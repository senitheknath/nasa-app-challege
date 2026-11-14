# Comprehensive Research: Next-Generation Farmer-Friendly Improvements for AgroShift AI

**Date:** 2026-11-09  
**Scope:** End-to-end audit and scientific/UX research into how AgroShift AI can be elevated further across **automation**, **agronomic visualization**, **scientific screening coverage**, **soil & water intelligence**, **rotation planning**, and **field-ready UX**—while keeping the primary farmer journey effortless and jargon-free.

---

## 1. Executive Codebase vs. UI Gap Analysis

By auditing the 33 Python modules in [`agroshift/`](../agroshift/) against the four farmer-facing UI views ([`finder_ui.py`](../agroshift/finder_ui.py), [`results_ui.py`](../agroshift/results_ui.py), [`farm_ui.py`](../agroshift/farm_ui.py), [`research_ui.py`](../agroshift/research_ui.py)), we identified **seven high-value scientific engines already built and tested in the backend that are not yet fully surfaced to the farmer in the UI**:

| # | Existing Backend Capability | Current UI State | High-Impact User-Friendly Improvement |
| :--- | :--- | :--- | :--- |
| **G1** | **107 Crops in Knowledge Store** (`data/global_catalogue.json`) | `screening.py` (`find_options`) currently screens **29 crops** (`25` with general traits + `4` regional-only), while **78 catalogue crops** remain unscreened because they lack `preferred_daily_mean_air_temperature` / `preferred_soil_ph` / `seasonal_crop_et` rows. | Expand reviewed FAO / MSU CRIES / FAO Paper 56 & 66 screening intervals to **all 107 crops** and add **Botanical Category Filter Pills** (`All`, `Cereals`, `Pulses & Legumes`, `Vegetables`, `Roots & Tubers`, `Oilseeds`, `Fruits`) on the Results screen. |
| **G2** | **12-Month Sowing Window Optimizer** (can evaluate `_make_general_card` across all 12 starting months using loaded NASA history) | Farmer must guess a start/end month first; if a crop fails in their chosen month, they are not told *which month* would work best. | Add an **Automated 12-Month Planting Window Heatmap Matrix** on Results & Crop Details showing, for each crop, which sowing months (`Jan`–`Dec`) fit temperature and rainfall best at their exact location. |
| **G3** | **Global Rotation & Botanical Family Engine** (`agroshift/rotation_engine.py`: `plan_global_rotations`, `evaluate_transition`) | `Explore -> Rotation comparison` stops for non-Sri-Lankan farms (`"Two-season rotations need a confirmed Sri Lankan field"`), and Crop Details does not show rotation fit with `Last crop grown here`. | Surface **Automated Previous-Crop Succession Badges** directly on Crop Cards/Details (e.g., *"✓ Good follow-up after Wheat: Legume nitrogen benefit & different botanical family"* or *"⚠ Same family as Tomato (Solanaceae): shared pest/disease carryover risk"*), and unlock the **Global Two-Season Rotation Planner** for all 250+ countries. |
| **G4** | **Agro-Climatic Extremes & Frost/Heat/Drought Radar** (`agroshift/extremes.py`: `summarize_historical_extremes`) | Screen only shows median daily temperature; frost days ($T_{\min}<0^\circ\text{C}$), heat-shock days ($T_{\max}>35^\circ\text{C}$), longest dry spell ($\text{CDD}<1\text{ mm}$), and heavy rainstorms ($\ge 25\text{ mm}$) are hidden. | Add a visual **4-Badge Weather Risk Strip** (*Frost Risk*, *Heat Stress Days*, *Longest Dry Spell*, *Heavy Downpour Days*) on the Season & Crop Details screens using plain farmer language. |
| **G5** | **FAO-56 4-Stage Crop Water Balance & $K_c$ Curve** (`agroshift/water_balance.py` + `96` stages in `ag_growth_stage`) | Crop Details only shows a static text line (`"Indicative full-cycle crop water use is 500–800 mm"`). | Render an interactive **Stage-by-Stage Crop Water Demand vs. Rainfall Chart** (`Initial` → `Development` → `Mid-Season Peak` → `Late Season`) showing *when* during the season irrigation is needed most. |
| **G6** | **6-Depth Soil Profile, USDA Texture Triangle & pH Reconciliation** (`agroshift/soil.py` + `soil_profile_wcs` + `terrain_context`) | `Explore -> Soil information` only displays a single `st.metric("Modelled topsoil pH", 5.8)`. | Upgrade `Soil information` and the `Field` step into a visual **Digital Soil Health & Terrain Card** showing topsoil vs. subsoil pH, USDA texture class, water-holding capacity, elevation/slope, and a visual **Measured vs. Modelled Disagreement Alert**. |
| **G7** | **6-Layer Non-Compensatory Evidence Scorecard & AquaCrop Simulator** (`agroshift/evidence_combination.py` & `agroshift/aquacrop_prototype.py`) | Not rendered in the UI. | Add a visual **6-Layer Evidence Checklist (Layers A–F)** on Crop Details and a **"Crop Growth & Water Stress Simulator" (AquaCrop)** interactive visual tab in `Explore -> Learning lab`. |

---

## 2. Deep Research Across 6 Improvement Pillars

### Pillar 1 — "Zero-Guesswork" Farmer Automation (Human-in-the-Loop)

Farmers abandon decision tools when forced to type numbers they do not know or click through multiple screens to discover basic facts about their land.

1. **1-Click "Best Planting Window" Finder per Crop:**
   - **Problem:** A farmer in Kenya or Iowa might pick `June–September` and see that a crop is `"Outside reference range"`, without knowing that `March–June` or `October–January` is ideal for that crop on their land.
   - **Solution:** Automatically scan all 12 possible planting start months (using the crop's indicative duration and the loaded 25-year NASA dataset) and display a **12-Month Viability Ribbon (`J F M A M J J A S O N D`)** on each crop detail page—with a 1-click button *"Switch my season to [Best Window]"*.
2. **Smart Previous-Crop Rotation Auto-Highlighting:**
   - **Problem:** When a farmer selects `"Last crop grown here"` (e.g., *Rice*, *Maize*, *Tomato*), that input is currently only used in the 5-crop Sri Lankan engine.
   - **Solution:** Automatically run [`evaluate_transition`](../agroshift/rotation_engine.py) for every candidate crop against the farmer's previous crop. Display a clear pill on each card:
     - 🟢 **Legume Break / Family Break:** *"Different plant family from your previous crop; reduces pest carryover."*
     - 🟡 **Same Botanical Family Warning:** *"Shares the same family (e.g., Solanaceae / Poaceae) as your last crop—check disease build-up."*
3. **Automatic Elevation, Slope & Frost-Pocket Context:**
   - Pull elevation and slope automatically via [`terrain_context`](../agroshift/providers.py) and Open-Meteo Elevation API so highland vs. lowland tropical zones (e.g., Nuwara Eliya/Kandy vs. Anuradhapura, or Eldoret vs. Mombasa) are immediately contextualized for the farmer.
4. **Decadal Climate Shift Alert (`2001–2012` vs. `2013–2025`):**
   - Automatically compute from the loaded 25-year NASA archive whether the farmer's chosen season has warmed or become drier/more erratic over the last decade compared to the prior decade (e.g., *"+0.4 °C warmer and +3 more dry-spell days in 2013–2025 vs. 2001–2012"*).

---

### Pillar 2 — Agronomic Visual Analytics That Farmers Understand Instantly

Research on agricultural DSTs (Walter & Lieth 1967; FAO Soils Bulletin 73; FAO Paper 56 & 66; agroclimate.org) shows that visual metaphors outperform raw tables:

1. **The "Soil Moisture Bucket" & 4-Stage Water Bar (`Initial` / `Vegetative` / `Flowering & Grain Fill` / `Maturity`):**
   - Instead of abstract $K_c$ coefficients, show a 4-stage visual bar chart where each growth stage displays:
     - **Crop Thirst ($\text{ET}_c = K_c \times \text{ET}_0$ in mm)** vs. **Typical Rain in That Stage (mm)**.
     - Highlights the **Peak Water-Sensitive Stage** (Mid-season flowering/fruiting) so the farmer knows *which weeks* supplemental irrigation is critical.
2. **12-Month × Multi-Crop Sowing Heatmap Matrix:**
   - A single visual grid where **rows = top candidate crops** and **columns = 12 planting months (`Jan`–`Dec`)**, color-coded (plus icons for color-blind accessibility) by historical temperature + rainfall compatibility. This lets a farmer plan a whole year's cropping calendar at one glance.
3. **Weather Extremes Risk Gauges (Confidence & Frequency Framing):**
   - Instead of probabilities or abstract standard deviations, communicate risk using **historical frequency out of 25 years**:
     - *"Frost ($<0\,^\circ\text{C}$) occurred in **0 of 25** past seasons"* (Safe) vs. *"Occurred in **14 of 25** past seasons"* (High Risk).
     - *"Severe heat ($>35\,^\circ\text{C}$) averages **8 days** per season."*
     - *"Longest dry spell without rain averages **16 consecutive days** (worst year: 29 days)."*
4. **Visual Soil Profile & Texture Card:**
   - A vertical layered soil-horizon illustration (`0–5 cm`, `5–15 cm`, `15–30 cm`, `30–60 cm`, `60–100 cm`, `100–200 cm`) showing how pH, clay/sand/silt, and water-holding capacity change with root depth.

---

### Pillar 3 — Expanding Scientific Screening Coverage & Crop Filters

1. **Full 107-Crop Screening & Category Filtering:**
   - Currently, farmers browsing Results see up to 29 screened crops without a category filter, and have to paginate 4 cards at a time.
   - Adding **Instant Category Filter Chips / Dropdown** (`All Categories`, `Cereals & Grains`, `Pulses & Legumes`, `Vegetables`, `Roots & Tubers`, `Oilseeds`, `Fruits & Perennials`, `Spices & Fiber`), **Search by Crop Name on Results**, and **Status Filter** (`Worth considering`, `Check before planting`, `All`) turns Results into a fast, interactive workbench.
2. **Cultivar Maturity Tier Guidance (Short / Medium / Long Duration):**
   - When a farmer's growing window is 75–90 days (e.g., short rains), long-duration varieties fail while short-duration cultivars (e.g., 65–75 day mung bean or cowpea, 90-day early maize) can fit. Surfacing cultivar duration tiers from `ag_cultivar_trait` helps farmers ask their local seed supplier for the right maturity group.

---

### Pillar 4 — Open-Data & Real-Time Forecast Complements (Scientifically Segregated)

While NASA POWER (`2001–2025`) provides the authoritative 25-year historical baseline, farmers making near-term operational decisions also benefit from:

1. **14-Day Agricultural Weather & Soil-Moisture Outlook (Open-Meteo Free Non-Commercial API):**
   - Open-Meteo provides unauthenticated 14-day forecasts of daily precipitation, $T_{\min}/T_{\max}$, FAO Penman-Monteith $\text{ET}_0$, and volumetric soil moisture (`0–7 cm`, `7–28 cm`).
   - **Scientific Safeguard:** Must be strictly labeled `short_range_numerical_weather_forecast` in a dedicated *"Current 7–14 Day Field Outlook"* widget, never mixed into the 25-year historical crop screening engine.
2. **Offline Multi-Property Soil Snapshot for All 34 Demo Stations:**
   - Pre-caching SoilGrids multi-property profiles (`phh2o`, `clay`, `sand`, `silt`, `soc`, `bdod`, `cec`, `wv0033`, `wv1500`) for the 34 bundled stations guarantees instant, rich soil profile visuals even without internet connectivity.

---

### Pillar 5 — Field-Ready UX, Mobile Ergonomics & Printable Field Cards

1. **One-Page Printable "Pocket Field Summary" (HTML/Print CSS):**
   - Farmers often share recommendations with family members, extension officers, or seed cooperatives via WhatsApp or paper. Enhancing `finder_report.py` (`readable()`) with a clean `@media print` stylesheet, visual status badges, 12-month calendar strip, and QR/link provenance makes the downloaded HTML report look like a professional extension bulletin.
2. **Quick-Jump Comparison Bar (Sticky Selection Tray):**
   - When a farmer clicks `+ Compare` on 2 or 3 crop cards across different pages, showing the names of the selected crops right in the comparison action bar (with a 1-click `Clear` button) prevents them from forgetting which crops they picked on page 1 while browsing page 3.
3. **Guided Question Chips in "Ask About My Results":**
   - Instead of forcing farmers to type a question from scratch in the assistant, provide 1-click **Suggested Question Buttons** (*"Why were some crops marked 'Check before planting'?"*, *"What is the biggest weather risk in my season?"*, *"Which crops are best after my previous crop?"*, *"What field measurements should I test next?"*).

---

## 3. Prioritized Implementation Roadmap

| Priority Tier | Improvement Package | Effort | Farmer Value | Scientific Defensibility |
| :--- | :--- | :---: | :---: | :---: |
| **Tier 1 (Immediate High-Impact)** | **1. 12-Month Sowing Window Heatmap Matrix** (Crop × Month compatibility grid)<br>**2. Historical Weather Extremes Risk Strip** (Frost, Heat $>35\,^\circ\text{C}$, Dry Spell CDD, Heavy Rain out of 25 yrs + Decadal Warming Shift)<br>**3. Global Rotation & Previous-Crop Succession Badges** on Crop Cards & Explore (`plan_global_rotations` unlocked globally)<br>**4. 4-Stage FAO-56 Crop Water Balance Chart** & **6-Layer Evidence Scorecard** on Crop Details<br>**5. Results Category/Search Filter + 1-Click Assistant Question Chips** | Low–Medium (uses modules already in `agroshift/`) | Very High | 100% grounded in existing verified NASA POWER, FAO-56, and GBIF data |
| **Tier 2 (Data & Visual Depth)** | **6. Digital Soil Health & Depth Profile Card** (`agroshift/soil.py` + USDA texture + pH disagreement alert)<br>**7. Interactive AquaCrop Canopy & Water-Stress Simulator** in `Explore -> Learning lab`<br>**8. Expanded Screening Traits** across more of the 107 catalogue crops<br>**9. Print-Styled Extension Bulletin Report** (`finder_report.py`) | Medium | High | Uses existing `soil.py`, `aquacrop_prototype.py`, and peer-reviewed FAO tables |
| **Tier 3 (Optional Live Extensions)** | **10. Live 7–14 Day Field Weather & Soil Moisture Outlook** (Open-Meteo API, segregated from historical screening)<br>**11. Offline Multi-Property SoilGrids Cache** for all 34 stations | Medium | Medium–High | Strictly separated (`forecast` vs. `historical_archive`) |
