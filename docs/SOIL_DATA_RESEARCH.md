# Soil Data Research, Pedological Interpretation, and Source Precedence

**Date:** 2026-11-09  
**Scope:** Section 3 & Section 5 (`ISRIC SoilGrids 2.0 WCS`, `Pedological Interpretation`, `Measured vs. Modelled Precedence`, `USDA NRCS SDA`, `ISRIC WoSIS`)

---

## 1. ISRIC SoilGrids 2.0 OGC WCS (`agroshift/soil.py`, `agroshift/providers.py`)

### 1.1 Access Method & Operational Status
- The legacy ISRIC REST API (`rest.isric.org`) has experienced prolonged service restrictions.
- ISRIC's OGC Web Coverage Service (`https://maps.isric.org/mapserv`, WCS `2.0.1`, `FORMAT=GEOTIFF_INT16`) is operational and verified across all 12 soil properties, 6 standard depth intervals (`0-5cm`, `5-15cm`, `15-30cm`, `30-60cm`, `60-100cm`, `100-200cm`), and 4 quantile layers (`mean`, `Q0.05`, `Q0.95`, `uncertainty`).

### 1.2 Official Unit Normalization Table (`SOILGRIDS_PROPERTIES`)
Every SoilGrids integer raster value is normalized via `normalize_soilgrids_value(prop, raw_value)` while preserving `raw_value`, `scale_divisor`, `normalized_value`, `original_unit`, `normalized_unit`, and `conversion_method`:

| Property Code | Description | Mapped Integer Unit | Scale Divisor | Conventional Unit | Valid Range |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `phh2o` | Soil pH in $\text{H}_2\text{O}$ | $\text{pH} \times 10$ | `10.0` | `pH (H2O)` | `2.5 – 11.0` |
| `clay` | Clay fraction ($<0.002\text{ mm}$) | $\text{g/kg}$ | `10.0` | `%` | `0.0 – 100.0` |
| `sand` | Sand fraction ($0.05\text{–}2\text{ mm}$) | $\text{g/kg}$ | `10.0` | `%` | `0.0 – 100.0` |
| `silt` | Silt fraction ($0.002\text{–}0.05\text{ mm}$) | $\text{g/kg}$ | `10.0` | `%` | `0.0 – 100.0` |
| `soc` | Soil organic carbon | $\text{dg/kg}$ | `10.0` | `g/kg` | `0.0 – 1000.0` |
| `nitrogen` | Total nitrogen | $\text{cg/kg}$ | `100.0` | `g/kg` | `0.0 – 100.0` |
| `bdod` | Fine-earth bulk density | $\text{cg/cm}^3$ | `100.0` | `g/cm³` | `0.1 – 2.65` |
| `cec` | Cation exchange capacity (pH 7) | $\text{mmol(c)/kg}$ | `10.0` | `cmol(+)/kg` | `0.0 – 200.0` |
| `cfvo` | Coarse fragments ($>2\text{ mm}$) | $\text{cm}^3/\text{dm}^3$ | `10.0` | `vol%` | `0.0 – 100.0` |
| `wv0010` | Water content at $-10\text{ kPa}$ | $0.1\text{ vol\%}$ | `10.0` | `vol%` | `0.0 – 100.0` |
| `wv0033` | Water content at $-33\text{ kPa}$ (FC) | $0.1\text{ vol\%}$ | `10.0` | `vol%` | `0.0 – 100.0` |
| `wv1500` | Water content at $-1500\text{ kPa}$ (PWP) | $0.1\text{ vol\%}$ | `10.0` | `vol%` | `0.0 – 100.0` |

---

## 2. Pedological Interpretation & Coupled Property Safeguards (`agroshift/soil.py`)

1. **Compositional Texture Closure (`classify_usda_texture`):**
   - Because SoilGrids quantile random forests predict `clay`, `sand`, and `silt` rasters independently, raw pixel sums can deviate slightly from 100%.
   - `classify_usda_texture` checks compositional closure ($|\text{clay} + \text{sand} + \text{silt} - 100\%| \le 5\%$), renormalizes onto the compositional simplex, and classifies the horizon into the 12 USDA Soil Texture Triangle classes.
2. **Available Water Capacity (`available_water_capacity_mm_m`):**
   - Computed from field capacity (`wv0033`) and permanent wilting point (`wv1500`) discounted by volumetric coarse fragments (`cfvo`):
     $$\text{AWC} = (\text{wv0033} - \text{wv1500}) \times 10 \times \left(1 - \frac{\text{cfvo}}{100}\right) \quad (\text{mm/m})$$
3. **Bulk Density Context:**
   - Evaluated against texture-dependent USDA NRCS root-limiting thresholds ($1.80\text{ g/cm}^3$ for sands, $1.65\text{ g/cm}^3$ for loams, $1.47\text{ g/cm}^3$ for clays) with explicit disclosure that regional grids cannot diagnose field-scale plough pans or mechanical compaction.
4. **Non-Equivalence of SOC / Total N to Fertilizer Prescriptions:**
   - `interpret_soil_horizon` explicitly warns that SoilGrids `soc` and `nitrogen` measure total organic pools, not plant-available mineral $\text{NH}_4^+/\text{NO}_3^-$, $\text{P}$, or $\text{K}$, and blocks fertilizer prescription generation.
5. **Salinity Non-Inference:**
   - `salinity_ece_ds_m` is strictly `None` unless a direct electrical conductivity measurement is provided.

---

## 3. Measured vs. Estimated Soil Precedence (`reconcile_soil_evidence`)

- **Strict Precedence Order:**
  1. `farmer_measurement` (laboratory or field soil test entered by the farmer) — `provisional_modelled_use = False`.
  2. `regional_survey` (USDA NRCS SSURGO map unit in the US) — `provisional_modelled_use = True`.
  3. `modelled_estimate` (ISRIC SoilGrids 2.0 ~250 m grid) — `provisional_modelled_use = True`.
  4. `unknown` when neither exists.
- **Disagreement Detection:** When both measured pH and modelled pH exist, `reconcile_soil_evidence` preserves both, computes $\Delta \text{pH} = \text{pH}_{\text{measured}} - \text{pH}_{\text{modelled}}$, checks whether $\text{pH}_{\text{measured}}$ falls outside the SoilGrids `[Q0.05, Q0.95]` 90% prediction interval, and flags `meaningful_disagreement = True` when $|\Delta \text{pH}| \ge 0.5$ or outside `[Q0.05, Q0.95]`.

---

## 4. Regional & Reference Soil Sources (`agroshift/providers.py`)

- **USDA NRCS Soil Data Access (`usda_sda_soil`):** Queries `https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest` via spatial WKT intersection (`SDA_Get_Mukey_from_intersection_with_WktWgs84`) for `country_code == "US"`, returning SSURGO map unit (`muname`), dominant component (`compname`), drainage class (`drainagecl`), and top-horizon physical/chemical properties.
- **ISRIC WoSIS WFS 2.0 (`wosis_profiles`):** Queries `https://maps.isric.org/mapserv?map=/map/wosis_latest.map` (`TYPENAMES=ms:wosis_latest_phaq`) to retrieve standardized reference soil profile observations within a bounding box, classified as `"reference_profile_observation"`.
