# FAO/IIASA GAEZ v5, FAO Crop Calendar, and Geospatial Terrain Integration

**Date:** 2026-11-09  
**Scope:** Section 6 (`FAO/IIASA GAEZ v5`), Section 7 (`FAO Crop Calendar` & `FAOSTAT`), Section 10 (`Geospatial & Terrain Modeling`)

---

## 1. FAO/IIASA GAEZ v5 Integration (`agroshift/providers.py`, `data/gaez/`)

### 1.1 Official Dataset & Verification
- **Mapset:** `GAEZ-V5.RES05-SIX.HP0120.AGERA5.HIST.{CROP}.{WATER}.tif` (5-arc-minute resolution, `4320 × 2160` WGS84 `EPSG:4326` palette GeoTIFFs, 2001–2020 historical AgERA5 climate, low input level).
- **Suitability Classes (`GAEZ_CLASSES`):** `0: No data`, `1: Very high`, `2: High`, `3: Good`, `4: Medium`, `5: Moderate`, `6: Marginal`, `7: Very marginal`, `8: Not suitable`, `9: Water`.
- **Expanded Coverage (24 Crops × 2 Water Regimes = 48 Verified Rasters):**
  - Cereals: `Maize (MZE)`, `Wheat (WHE)`, `Wetland rice (RCW)`, `Dryland rice (RCD)`, `Sorghum (SRG)`, `Pearl millet (PML)`
  - Legumes: `Soybean (SOY)`, `Groundnut (GRD)`, `Gram / Mung bean (GRM)`, `Cowpea (COW)`, `Chickpea (CHK)`, `Pigeonpea (PIG)`, `Phaseolus bean (PHB)`
  - Roots & Tubers: `White potato (WPO)`, `Sweet potato (SPO)`, `Cassava (CSV)`
  - Oilseeds, Fibre & Sugar: `Sunflower (SFL)`, `Sesame (SES)`, `Cotton (COT)`, `Sugarcane (SUC)`
  - Horticulture & Perennials: `Banana (BAN)`, `Tomato (TOM)`, `Onion (ONI)`, `Cabbage (CAB)`
- **Integrity:** All 48 rasters are verified against the official GAEZ v5 `_readme_res05.xlsx` file inventory and SLD color map legend (`SIX/sld`), with SHA-256 checksums pinned in `data/gaez/manifest.json`.

### 1.2 Point and Polygon Sampling (`gaez_point`, `gaez_polygon`)
- `gaez_point(latitude, longitude, crop, water)` extracts the exact 5-arc-minute cell class via GeoTIFF affine tags (`33550` pixel scale, `33922` tiepoints, `34735` EPSG:4326 GeoKey).
- `gaez_polygon(boundary, crop, water)` validates a farmer's GeoJSON `Polygon` or `Feature`, samples the centroid, exterior ring vertices, and interior 5-arc-minute grid lattice points, and reports whether the polygon spans multiple GAEZ suitability classes alongside an explicit ~10 km resolution disclosure.
- **Scientific Safeguards:**
  - GAEZ v5 suitability classes are categorical agro-ecological classifications and are **never** converted into harvest probabilities or farm yield predictions.
  - Because GAEZ v5 historical layers use `AgERA5` reanalysis while NASA POWER uses `MERRA-2`, `agroshift/evidence_combination.py` (`Layer D`) uses GAEZ v5 strictly as a cross-check (`aligned`, `divergent_caution`, `divergent_local_constraint`) and never double-counts correlated reanalysis signals.

---

## 2. FAO Crop Calendar & FAOSTAT (`agroshift/providers.py`)

### 2.1 FAO Crop Calendar Window Matching (`match_crop_calendar`)
- Retrieves country-specific crops (`calendar_crops`) and agro-ecological zone sowing/harvesting windows (`crop_calendars`) from `https://api-cropcalendar.apps.fao.org/api/v1/countries`.
- `match_crop_calendar(window, calendar_rows, crop_name)` compares the farmer's selected `Window(start_month, start_day, end_month, end_day)` against each agro-ecological zone's `early_sowing`–`later_sowing` and `early_harvest`–`late_harvest` spans:
  - Identifies `matched_zones` and `conflicting_zones`.
  - Sets `sowing_date_confirmed = True` when the farmer's window aligns with a published zone calendar, enabling stage-resolved risk evaluation in `agroshift/extremes.py`.
  - **Never** overwrites the farmer's chosen planting or harvesting dates (`farmer_window_preserved = True`).

### 2.2 FAOSTAT QCL National Context (`national_production`)
- Uses the hash-verified extract (`data/faostat_qcl_sample.json`) from the official FAOSTAT Crops and Livestock Products (`QCL`) bulk distribution (`Production_Crops_Livestock_E_All_Data_(Normalized).zip`).
- Preserves official FAO observation flags (`A`: Official figure, `E`: Estimated value, `I`: Imputed value) and never uses national production tonnage to rank suitability for an individual farm.

---

## 3. Geospatial & Terrain Context (`terrain_context`)

- `terrain_context(latitude, longitude)` queries Copernicus DEM GLO-90 (`90 m` horizontal resolution) at the central coordinate and 4 cardinal offsets ($\pm 0.00081^\circ \approx 90\text{ m}$ N/S/E/W) to compute elevation ($\text{m}$) and regional terrain slope ($\text{\%}$), classifying terrain into `flat_to_gentle (<2%)`, `moderate (2-8%)`, or `steep (>=8%)`.
- Explicitly discloses that a 90 m DEM does not resolve field-level terracing, bunded paddy leveling, or micro-drainage features.
