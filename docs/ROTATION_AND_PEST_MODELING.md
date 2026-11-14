# Crop Rotation Planning and Pest, Disease, and Weed Context Modeling

**Date:** 2026-11-09  
**Scope:** Section 15 (`Crop Rotation and Multi-Season Planning`) & Section 16 (`Pest, Disease, and Weed Context`)

---

## 1. Two-Tier Crop Rotation Architecture

### 1.1 Confirmed Sri Lankan Pilot Rotation Engine (`agroshift/decision.py` — Preserved)
- Applies strictly when `pilot_scope(latitude, longitude, country, pilot_confirmed)` is `True` and two seasonal windows (`Yala then Maha` or `Maha then Yala`) are selected.
- Uses reviewed Sri Lanka Department of Agriculture references (`data/crops.json`) with interval-bounded suitability across `temperature`, `water`, `soil`, and `rotation` criteria, enforcing cultivar-specific safeguards (e.g., `mung_bean` 55–60 day harvest timing applies specifically to cultivar `MI 6`).

### 1.2 International Constraint-Based Rotation Planner (`agroshift/rotation_engine.py`)
`plan_global_rotations(farm, dataset)` and `evaluate_transition(first_crop, second_crop, ...)` evaluate two-season international crop sequences using 5 explicit agronomic constraints:
1. **Life-Cycle Constraint (`annual` vs. `perennial`):**
   - Blocks scheduling a perennial crop (`sugarcane`, `banana`, `coffee_arabica`, `tea`, `alfalfa`, `cassava` multi-year) in Season 1 followed by an annual crop in Season 2 within the same annual cycle.
2. **Seasonal Window Turnaround & Overlap Check (`_window_overlap_days`):**
   - Blocks sequences where Season 1 harvest dates and Season 2 planting dates overlap.
3. **Botanical Family Succession (`ag_family`):**
   - Flags consecutive same-family sequences (`Poaceae → Poaceae`, `Solanaceae → Solanaceae`, `Fabaceae → Fabaceae`, `Brassicaceae → Brassicaceae`, `Asteraceae → Asteraceae`, `Cucurbitaceae → Cucurbitaceae`) as `"Same-family succession caution"` due to shared soil-borne pathogen, nematode, and pest carryover.
   - Identifies complementary cereal–legume (`Poaceae ↔ Fabaceae`) and root–legume transitions that diversify crop families.
4. **Rooting-Depth Alternation (`max_rooting_depth_m`):**
   - Highlights sequences that alternate deep-rooted crops (e.g., sorghum, sunflower, cotton, maize) with shallow-to-medium rooted legumes or vegetables (FAO-56 Table 22).
5. **Flooded Paddy to Upland Drainage Transition:**
   - Flags transitions from bunded rice (`rice`) to waterlogging-sensitive upland legumes/oilseeds with a requirement for field drainage and seedbed aeration between seasons.
- **Scientific Safeguard:** Numerical nitrogen fixation ($\text{kg N/ha}$) or disease-suppression percentages are **never** fabricated without site-specific trial measurements.

---

## 2. Educational Pest, Disease, and Weed Context (`agroshift/pests.py`, `ag_pest_context`)

- `evaluate_crop_pest_context(crop_id, frame, window)` queries reviewed records in `ag_pest_context_reviewed` (`18` major crop–pathogen/pest/weed relationships across `maize`, `wheat`, `rice`, `soybean`, `groundnut`, `common_bean`, `potato`, `tomato`, `sorghum`, `chickpea`, `cotton`, `cassava`, `sunflower`).
- Evaluates historical seasonal weather conduciveness indicators from `dataset.frame` (`warm_season_fraction`, `high_humidity_season_fraction`, `extended_dry_days_season_fraction`) to contextualize susceptible growth stages.
- **Strict Safety Boundaries:**
  - `outbreak_probability_predicted = False`: Weather conduciveness never predicts an outbreak probability.
  - `chemical_prescription_included = False`: Never prescribes chemical pesticides or dosage rates; provides cultural/rotational management context and directs farmers to local extension services.
