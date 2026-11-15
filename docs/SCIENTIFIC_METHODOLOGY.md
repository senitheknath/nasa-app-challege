# CRESCO Agro-Grid: Scientific Methodology, Formulas & Agronomic Rules

This document summarizes the Earth-observation datasets, agronomic theories, mathematical scoring formulas, and transition rules implemented in **CRESCO Agro-Grid** (`agroshift_dev`).

---

## 1. Earth Observation & Field Context Inputs

When a user draws a field polygon on the map, `derive_field_autofill` (`agroshift/earth_data/autofill.py`) populates the field context without manual guesswork while keeping every field transparently attributed and overridable:

| Layer | Data Source | Derived Parameters |
| :--- | :--- | :--- |
| **Field Geometry** | Geodetic polygon calculation | `area_ha` (hectares) and `acres` |
| **Climate & Moisture** | **NASA POWER** (25-year daily agroclimatology archive) | Daily mean temperature (`T2M`), corrected precipitation (`PRECTOTCORR`), root-zone wetness, topsoil wetness |
| **Soil Profile** | **SoilGrids** | Soil pH, texture class, drainage class, 4-horizon soil profile |
| **Terrain** | **Copernicus DEM** | 5×5 terrain elevation mesh, field slope (`slope_pct`) |
| **Crop Suitability** | **FAO GAEZ** | Rainfed and irrigated suitability indices (`gaez_point`, `gaez_polygon`) |
| **3D Field Slab Fusion** | Satellite overpasses + progressive inverse-variance fusion | Canopy/atmosphere state and uncertainty-weighted soil wetness (`engine_3d.py`) |

---

## 2. Single-Crop Regional Screening (`find_options` in `agroshift/science/decision/screening.py`)

Before building rotations, all **107 crops** are screened against the farmer's exact location and first sowing window (`w1`) using reviewed global traits and verified NASA POWER history (`MIN_SEASONS` full years required):

1. **Thermal Fit (`preferred_daily_mean_air_temperature`)**
   - Computes median seasonal temperature across all valid full historical years (`typical_day`) and the median fraction of days inside `[low, high]` °C.
   - `possible` if `low <= typical_day <= high`, else `outside`.
2. **Soil pH Compatibility (`preferred_soil_ph`)**
   - Checks `low <= farm.ph <= high`. If outside, status becomes `outside` with a pH caution.
3. **Drainage & Waterlogging (`persistent_waterlogging_conflict`)**
   - If `farm.drainage == "waterlogged"` and the crop has a waterlogging conflict (`1`), status becomes `blocked`.
4. **Cycle Duration Fit (`indicative_cycle_duration`)**
   - Compares window length `L = (end - start).days + 1` against `[low, high]` days. If `L < low`, status is downgraded from `possible` to `check`.
5. **Seasonal Water Supply Adequacy (`seasonal_crop_et`)**
   - Estimates usable seasonal water supply:
     $$\text{Estimated Supply (mm)} = R_{\text{median}} \times f_{\text{rain}} + I_{\text{net}}$$
     where $R_{\text{median}}$ is median seasonal rainfall, $f_{\text{rain}}$ is usable rain fraction, and $I_{\text{net}}$ is net irrigation (`0` when `rainfed`).
   - If $\text{Estimated Supply} < \text{ET}_{\text{low}}$, status is downgraded to `check`.

**Status Priority Order:** `possible` (0) → `check` (1) → `outside` (2) → `unknown` (3) → `blocked` (4).

---

## 3. Agronomic Transition Rules (`DEFAULT_RULES` in `agroshift/rotation/rules.py`)

Every consecutive crop pair `(Crop 1 → Crop 2)` is evaluated by **8 composable agronomic rules**, each emitting `blocker`, `caution`, or `benefit` findings:

| Rule | Theory / Mechanism | Trigger & Finding |
| :--- | :--- | :--- |
| **`rule_lifecycle`** | Annual vs. perennial land occupation | `blocker` if Crop 1 is perennial; `caution` if Crop 2 is perennial |
| **`rule_window_turnaround`** | Calendar & land-prep turnaround | `blocker` if `window_overlap_days(w1, w2) > 0` |
| **`rule_family_succession`** | Botanical family alternation & nitrogen fixation | `caution` if `family(C1) == family(C2)` (or `family(prev) == family(C1)`); `benefit` (`legume_diversification`) if distinct families and includes `Fabaceae`; `benefit` (`family_break`) otherwise |
| **`rule_rooting_depth`** | Vertical root-zone stratification | `benefit` (`rooting_depth_alternation`) if $|\bar{d}_1 - \bar{d}_2| \ge \text{min\_rooting\_delta\_m}$, where $\bar{d} = \frac{1}{2}(d_{\min} + d_{\max})$ |
| **`rule_drainage_transition`** | Paddy-to-upland soil structure shock | `caution` (`drainage_transition`) when transitioning from flooded/rice to waterlogging-sensitive upland crop |
| **`rule_pathogen_carryover`** | Host-specific pest & disease continuity | `caution` (`pest_pathogen_overlap`) if `pests(C1) ∩ pests(C2)` is non-empty |
| **`rule_nutrient_balance`** | Macronutrient extraction & biological N₂ fixation | `benefit` (`nutrient_replenishment`) if heavy feeder is followed by nitrogen-fixer; `caution` (`consecutive_heavy_feeders`) if two heavy feeders follow each other |
| **`rule_water_deficit_carryover`** | Cumulative root-zone moisture depletion | `caution` if `irrigation == "rainfed"` and both crops have $K_{c,\max} \ge 1.15$ |

**Overall Transition Status:**
- `blocked`: any `blocker` finding
- `caution`: `same_family_s1_s2` finding
- `conditional`: any other `caution` finding
- `complementary`: no blockers or cautions

---

## 4. Multi-Criteria Agronomic Scoring (`rate_rotation_sequence` in `agroshift/rotation/engine.py`)

Each rotation sequence receives a **0–100 Agronomic Score** composed of 3 weighted pillars:

$$\text{Score} = \text{Climate Suitability (0–40)} + \text{Transition Synergy (0–35)} + \text{Timeline Efficiency (0–25)}$$

1. **Climate Suitability (`climate_pts`, 0–40)**
   - Sum of Season 1 and Season 2 screening card points:
     - `possible` = `20.0` pts
     - `check` = `12.0` pts
     - `outside` = `5.0` pts
     - `blocked` / `unknown` = `0.0` pts

2. **Transition Synergy (`trans_pts`, 0–35)**
   - If `transition.status == "blocked"`, `trans_pts = 0.0`.
   - Otherwise starts at `15.0` and adjusts per finding:
     - `+6.0` per `benefit`
     - `-7.0` per `caution`
     - `-15.0` per `blocker`
   - Clamped to `[0.0, 35.0]`.

3. **Timeline Efficiency (`time_pts`, 0–25)**
   - Base score by turnaround buffer status:
     - `optimal`: `20.0` · `acceptable`: `16.0` · `excessive_fallow`: `10.0` · `tight`: `6.0` · `collision`: `0.0` (fallback `14.0`)
   - Adjustments:
     - `slack_bonus = 2.5 × (number of slots with delay_slack_days > 0)`
     - `span_penalty = min(6.0, max(0.0, (span_total - 20) × 0.06))`
     - `coll_penalty = min(6.0, collision_probability_pct × 0.1)`
   - Clamped to `[0.0, 25.0]`.

**Rating Tiers:**
- **Optimal**: `score >= 88.0`
- **Good**: `72.0 <= score < 88.0`
- **Moderate**: `50.0 <= score < 72.0`
- **Restricted**: `score < 50.0`

---

## 5. 5-Factor Operational Easiness Matrix (`compute_easiness_matrix`)

Each rotation is also scored across **5 physical operational hardness factors** (`f₁..f₅ ∈ [0.0, 10.0]`, where **lower = easier**):

1. **`turnaround_expiry_pressure` ($f_1$)**: Penalizes tight/negative turnaround buffers (`buffer_days < 0` → `6.0`, `< 7` → `4.5`, `< 14` → `2.5`, `14–35` → `0.5`, `> 35` → `1.5`), zero/low delay slack (`+2.0` if `<= 0`, `+1.0` if `< 7`), and collision probability (`+3.0 × collision_pct / 100`).
2. **`earthwork_drainage_flip` ($f_2$)**: Base `1.0`; `+6.0` for paddy-to-upland drainage flip; `+0.5` to `+3.0` for field slope (`>= 4%`, `>= 8%`, `>= 15%`); `+2.0` for poor drainage with waterlogging-sensitive Crop 2.
3. **`water_irrigation_dependency` ($f_3$)**: Base `1.0`; adds `+2.5` if mean $K_{c,\max} \ge 1.15$ (`+1.5` if $\ge 1.0$). Under `rainfed`, adds `+2.5` for `water_deficit_carryover` and up to `+4.0` from seasonal rainfall deficit ratio $\max\left(0, \frac{\text{water\_need} - \text{rainfall}}{\text{water\_need}}\right) \times 6.0$.
4. **`soil_nutrient_intervention` ($f_4$)**: Base `3.0`; `-2.0` if either crop is a nitrogen fixer; `+4.0` if both are heavy feeders (`+1.5` if one); `+2.5` if soil $\text{pH} < 5.5$ or $> 8.0$ (`+1.0` if $< 5.8$ or $> 7.6$).
5. **`pest_pathogen_vigilance` ($f_5$)**: Base `1.5`; `+min(5.0, 2.5 + n_shared)` for shared pests; `+3.5` if same botanical family; `-1.0` if distinct families with `0` shared pests.

$$\text{Hardness Score} = \frac{f_1 + f_2 + f_3 + f_4 + f_5}{5}, \qquad \text{Easiness Score} = 10.0 - \text{Hardness Score}$$

**Ease-Adjusted Score:**
$$\text{ease\_adjusted\_score} = 0.65 \times \text{Score} + 3.5 \times \text{Easiness Score}$$

---

## 6. Goal-Based Filter Scores (`_compute_filter_scores`)

To let farmers re-rank rotations by priority (`Best Match`, `Water Saving`, `Soil & Nitrogen`, `Pest Break`, `Easy Cycle`), each rotation computes 5 normalized `0–100` scores:

| Filter ID | Formula |
| :--- | :--- |
| **`default`** | $\text{Score}$ |
| **`water`** | $\text{clamp}_{0..100}\big((10 - f_{\text{water}}) \times 6.5 + \text{climate\_pts} \times 0.85\big)$ |
| **`soil`** | $\text{clamp}_{0..100}\big((10 - f_{\text{soil}}) \times 6.5 + \text{trans\_pts} \times 1.0\big)$ |
| **`pest`** | $\text{clamp}_{0..100}\big((10 - f_{\text{pest}}) \times 6.5 + \text{trans\_pts} \times 1.0\big)$ |
| **`ease`** | $\text{clamp}_{0..100}(\text{ease\_adjusted\_score})$ |

---

## 7. Multi-Crop Chaining (3–4 Crops) & FAO-56 Growth Stages

* **Why 3–4 Crops:** A 2-crop cycle repeats host families too soon to break soil-borne pest/disease carryover. Extending sequences to **3–4 crops** introduces 2–3 distinct botanical families, root depths, and nitrogen fixers within a reliable 12–18 month climate/turnaround window.
* **Slot Chaining (`_extend_timeline_with_followup_crops`):**
  - Follow-up crops are selected preferring non-repeats, non-perennials, viable regional status (`possible` / `check`), and botanical family alternation (`family != prev_family`).
  - Each follow-up slot begins after a **14-day field preparation & turnaround buffer** following the prior slot's nominal harvest date.
  - Each slot builds **4 FAO-56 phenological stages** (`Initial`, `Develop`, `Mid-Season`, `Late`) scaled to the crop's cycle duration.

---

## 8. Custom Crop Scorer & 1-Tap Smart Swap (`_build_custom_sequence`)

When a farmer enters 2–4 crops they already have (`custom_crop_ids`):
1. Evaluates all valid orderings (locking Slot 1 if an active `Current crop` is pinned) and selects the **highest-scoring sequence** (`is_custom = True`).
2. Inserts it into the regional list and computes **`custom_comparison`** (`gap_pts = custom_score - top_regional_score` + primary bottleneck reason).
3. Tests replacing the weakest non-pinned crop with top viable regional candidates; if a replacement improves the score by $\ge 2.0\text{ pts}$, surfaces a **1-tap `smart_swap`** recommendation.
