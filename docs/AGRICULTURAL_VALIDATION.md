# Agricultural Validation, 5-Variant Ablation Study, and Process-Based Prototype

**Date:** 2026-11-09  
**Scope:** Section 19 (`Agricultural Validation`), Section 20 (`Ablation Study`), Section 21 (`Process-Based Crop Modeling Prototype`)  
**Reproducible Artifacts:** `agroshift/validation.py`, `scripts/run_validation_ablation.py`, `data/validation_ablation_results.json`, `agroshift/aquacrop_prototype.py`

---

## 1. Multi-Method Agricultural Validation (`agroshift/validation.py`)

> [!IMPORTANT]
> AgroShift AI does not fabricate synthetic "ground-truth" crop success labels and never claims independent on-farm agronomic trial validation where none has been performed (`capabilities["D"]["available"] == False`). All validation metrics below compare AgroShift AI's screening outputs against independent published agro-ecological benchmarks (FAO/IIASA GAEZ v5 and historical temporal holdouts across 34 real NASA POWER station archives).

### 1.1 Temporal Holdout Validation (`2001–2015` vs. `2016–2025`)
Evaluated across all **34 verified global reference stations** (`data/global_nasa_stations_summary.csv`, `884` station–crop pairs):
- **Overall Screening Status Agreement Rate (`2001–2015` vs. `2016–2025`):** **`84.50%`** (`747 / 884` station–crop evaluations retained identical categorical screening status across decades).
- **Observed Decadal Warming Delta ($\overline{T}_{2016\text{–}2025} - \overline{T}_{2001\text{–}2015}$):** **`+0.330 °C`** across the 34 global agricultural stations.
- **Interpretation:** The 15.5% of status transitions between 2001–2015 and 2016–2025 occur at thermal boundary stations where decadal warming (+0.3°C to +0.6°C) shifts cool-season crops (`wheat`, `barley`, `oats`, `dry_pea`) across their upper published temperature threshold or shifts warm-season crops into compatibility at temperate stations.

### 1.2 Missing-Data & Degraded-Coverage Stress Testing (`evaluate_missing_data_stress`)
Tested at `nairobi_kenya` (`-1.2921, 36.8219`):
- **Full-Input Possible Crops:** `12`
- **Minimal-Input (`ph=None`, `drainage="unknown"`, `rain_fraction=None`) Unknown Crops:** `4`
- **Degraded Weather Coverage ($<10$ complete daily temperature seasons) Possible Crops:** **`0`** (`26` crops fall back to `unknown` / `check`).
- **False Optimistic Promotions When Inputs Are Removed:** **`0`** (`conservative_fallback_verified = True`).

---

## 2. Five-Variant Scientific Ablation Study (`run_ablation_study`)

Evaluated across all **34 global stations** (`884` station–crop evaluations, `680` GAEZ-mapped station–crop pairs):

| Model Variant | Mean Assessed Factors / Crop | Insufficient Evidence (`unknown`) Rate | Worth Investigating Rate | Conditional Compatibility Rate | Unflagged Promotion on GAEZ Class 7–8 (`Very Marginal` / `Not Suitable`) | Directional Agreement with GAEZ v5 Suitability |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline (Climate only)** | `1.69` | `15.4%` | `40.4%` | `12.6%` | `14.9%` | `57.1%` |
| **Variant A (+Soil context)** | `2.31` | `7.7%` | `38.6%` | `12.6%` | `14.9%` | `64.5%` |
| **Variant B (+GAEZ v5 cross-check)** | `2.35` | `15.4%` | `29.0%` | `24.0%` | **`0.0%`** | `72.0%` |
| **Variant C (+Crop calendars)** | `2.69` | `15.4%` | `40.4%` | `12.6%` | `14.9%` | `57.1%` |
| **Variant D (Combined 6-layer evidence)** | **`3.96`** | **`7.7%`** | `28.5%` | `24.4%` | **`0.0%`** | **`79.4%`** |

### Key Ablation Findings
1. **Adding Soil Context (`Variant A`):** Cuts the `Insufficient evidence` (`unknown`) rate in half (from **`15.4%` to `7.7%`**) and improves directional agreement with GAEZ v5 by **`+7.4` percentage points** (`57.1% → 64.5%`) by identifying soil pH constraints on acid- or alkaline-sensitive crops.
2. **Adding GAEZ v5 Cross-Check (`Variant B`):** Eliminates unflagged promotions on GAEZ Class 7–8 (`Very marginal` / `Not suitable`) land (from **`14.9%` down to `0.0%`**) by reclassifying divergent cases to `Conditional compatibility` (`Layer D`), increasing GAEZ directional agreement by **`+14.9` percentage points** (`57.1% → 72.0%`) without double-counting correlated reanalysis inputs.
3. **Adding Crop Calendars (`Variant C`):** Increases mean assessed evidence dimensions per crop (`1.69 → 2.69`) and enables stage-resolved reproductive hazard reporting (`agroshift/extremes.py`) without overriding farmer planting dates.
4. **Full Combined 6-Layer Evidence (`Variant D`):** Achieves the highest evidence density (**`3.96` factors/crop**), lowest `unknown` rate (**`7.7%`**), **`0.0%`** unflagged promotions on GAEZ Class 7–8 land, and **`79.4%`** directional agreement with FAO/IIASA GAEZ v5 (+22.3 percentage points over Baseline).

---

## 3. Isolated Process-Based Crop Modeling Prototype (`agroshift/aquacrop_prototype.py`)

- Implements the **FAO Irrigation and Drainage Paper 66 / AquaCrop** water-driven daily canopy cover ($CC(t)$), root-zone water stress ($K_{s,\text{exp}}, K_{s,\text{sto}}$), crop transpiration ($Tr(t)$), soil evaporation ($E(t)$), and normalized water productivity ($B = WP^* \sum \frac{Tr(t)}{ET_0(t)}$) equations for 10 reference crops (`maize`, `sorghum`, `pearl_millet`, `wheat`, `rice`, `soybean`, `groundnut`, `potato`, `sunflower`, `cotton`).
- **Strict Isolation Safeguards:**
  - Never called by `agroshift/screening.py:find_options`.
  - Every return payload carries `"simulation": True`, `"data_category": "hypothetical_simulation"`, `"calibrated_to_farm": False`, `"used_in_primary_screening": False`, and a full dictionary of `unmeasured_assumed_parameters`.
