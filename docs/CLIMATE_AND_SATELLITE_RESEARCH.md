# Climate and Satellite Data Research and Implementation

**Date:** 2026-11-09  
**Scope:** Section 3 & Section 4 (`NASA POWER`, `CHIRPS v3.0`, `ECMWF ERA5-Land`, `NASA GPM IMERG V07`, `NASA SMAP L3/L4`)

---

## 1. NASA POWER Daily Agroclimatology (`agroshift/power.py`)

### 1.1 Provider Evaluation Table
| Attribute | Verified Specification |
| :--- | :--- |
| **Official Source** | NASA Langley Research Center (LaRC) POWER Project (`https://power.larc.nasa.gov/api/temporal/daily/point`) |
| **Underlying Models** | GMAO MERRA-2 assimilation (`T2M`, `T2M_MIN`, `T2M_MAX`, `T2MDEW`, `PRECTOTCORR`, `RH2M`, `WS2M`, `WS10M`, `PS`, `GWETTOP`, `GWETROOT`) and CERES SYN1deg / FLASHFlux (`ALLSKY_SFC_SW_DWN`) |
| **Spatial Resolution** | Meteorology: `0.5° latitude × 0.625° longitude` (~55 km × 69 km at equator); Solar: `1.0° × 1.0°` (~111 km) |
| **Temporal Coverage** | `1981-01-01` to near-real-time (2–5 day latency for preliminary, ~2–3 months for final CERES) |
| **Time Standard** | Local Solar Time (`LST`) verified in response header (`header.time_standard == "LST"`) |
| **Authentication & Limits** | Public unauthenticated REST API; rate-limited with `HTTP 429` (`Retry-After` honored in `PowerClient`) |
| **Data Category** | Category 2 — Satellite-derived and assimilation/reanalysis gridded estimates (`REAL` live / `VERIFIED_CACHE` archived) |

### 1.2 Expanded Parameter Set (`EXTENDED_PARAMETERS`)
- **Default 6-Parameter Core (`PARAMETERS`):** `T2M` (°C), `T2M_MIN` (°C), `T2M_MAX` (°C), `PRECTOTCORR` (mm/day), `RH2M` (%), `ALLSKY_SFC_SW_DWN` (MJ/m²/day). Preserved as default so all 34 bundled station archives (`data/stations/*.json.gz`) match exact request signatures.
- **Extended 12-Parameter Suite (`EXTENDED_PARAMETERS`):** Adds:
  - `WS2M` (`m/s`, $\ge 0$): 2-meter wind speed for FAO-56 Penman-Monteith aerodynamic conductance.
  - `WS10M` (`m/s`, $\ge 0$): 10-meter wind speed (converted to 2 m via FAO-56 Eq. 47 when `WS2M` is absent).
  - `PS` (`kPa`, $> 0$): Surface atmospheric pressure for psychrometric constant $\gamma$.
  - `T2MDEW` (`C`): 2-meter dew/frost point temperature for actual vapour pressure $e_a$ (FAO-56 Eq. 14).
  - `GWETTOP` (`1`, $[0, 1]$): Surface soil wetness fraction (0–5 cm) from MERRA-2 land model.
  - `GWETROOT` (`1`, $[0, 1]$): Root-zone soil wetness fraction (0–100 cm) from MERRA-2 land model.

### 1.3 Grid-Cell Normalization & Provenance (`power_grid_cell`, `grid_query_key`)
- `power_grid_cell(latitude, longitude)` computes the exact published `0.5° × 0.625°` MERRA-2 meteorology cell center/bounds and `1.0° × 1.0°` CERES solar cell center/bounds.
- `PowerClient.fetch(..., reuse_grid_cell=True)` supports opt-in grid-cell cache reuse under `.cache/power/grid/{grid_query_key}.json` while keeping exact-coordinate cache files at `.cache/power/{exact_key}.json`.
- Every unpacked `Dataset.provenance` stores `dataset_id`, `provider`, `requested_coordinates`, `cached_request_coordinates`, `returned_coordinates`, `grid_cell`, `grid_cell_reused`, `time_standard`, `date_range`, `parameters`, `units`, `retrieved_at_utc`, `product_version`, `sha256`, and `missing_data_indicators`.

---

## 2. UCSB CHC CHIRPS v3.0 (`agroshift/providers.py:chirps_context`)

| Attribute | Verified Specification |
| :--- | :--- |
| **Official Source** | UC Santa Barbara Climate Hazards Center (`https://data.chc.ucsb.edu/products/CHIRPS/v3.0/`) |
| **Coverage & Resolution** | Quasi-global land `60°S–60°N`, `180°W–180°E` at `0.05° × 0.05°` (~5.5 km) resolution, `1981–present` |
| **Scientific Limitation** | Does **not** cover high latitudes ($|\text{lat}| > 60^\circ$, e.g. northern Finland/Alaska/northern Canada). |
| **Implementation & Safeguards** | `chirps_context(latitude, longitude)` enforces `-60.0 <= latitude <= 60.0` (returning `status="unavailable"` north of 60°N or south of 60°S) and sets `averaged_with_nasa_power = False` so CHIRPS and NASA POWER MERRA-2 precipitation are never automatically averaged. |

---

## 3. ECMWF ERA5-Land (`agroshift/providers.py:era5_land_context`)

| Attribute | Verified Specification |
| :--- | :--- |
| **Official Source** | Copernicus Climate Data Store (`reanalysis-era5-land`) / Open-Meteo ERA5-Land Archive API (`models=era5_land`) |
| **Coverage & Resolution** | Global land (`90°S–90°N`), `0.1° × 0.1°` (~9 km), `1950–present` |
| **Parameters** | Daily 2 m temperature, total precipitation, shortwave radiation, 10 m wind speed, volumetric soil water layer 1 (`0–7 cm`). |
| **Scientific Limitation & Safeguards** | Reanalysis volumetric soil moisture is a land-surface model state (HTESSEL) on a ~9 km grid. `era5_land_context` explicitly tags `soil_moisture_classification = "reanalysis_model_estimate"` and never substitutes it for a field soil moisture sensor. |

---

## 4. NASA GPM IMERG V07 & NASA SMAP L3/L4

### 4.1 NASA GPM IMERG V07 (`GPM_3IMERGDF` V07)
- **Coverage & Resolution:** Global (`90°S–90°N` in V07; core satellite radar footprint `60°S–60°N`), `0.1° × 0.1°` (~10 km), June 2000–present, units `mm/day`.
- **Access & Authentication:** Hosted on NASA GES DISC OPeNDAP/HTTPS (`https://disc.gsfc.nasa.gov/`); requires a personal NASA Earthdata Login bearer token (`~/.netrc` / `EARTHDATA_TOKEN`).
- **Engineering Decision:** Documented in `data/provider_registry.json` (`nasa-gpm-imerg`); not required on the anonymous farmer request path because NASA POWER `PRECTOTCORR` already assimilates satellite-gauge precipitation back to 1981 without requiring farmer credentials.

### 4.2 NASA SMAP (`SPL3SMP_E` 9 km L3 & `SPL4SMGP` 9 km L4)
- **Distinction:**
  - **SMAP L3 (`SPL3SMP` / `SPL3SMP_E`):** Passive L-band radiometer observation-derived surface soil moisture only (`0–5 cm` top layer, `36 km` native footprint posted on `9 km` EASE-Grid 2.0), susceptible to dense vegetation canopy ($\text{VWC} > 5\text{ kg/m}^2$) and frozen ground flags.
  - **SMAP L4 (`SPL4SMGP`):** Model-assimilated surface (`0–5 cm`) and root-zone (`0–100 cm`) soil moisture generated by assimilating SMAP L-band brightness temperatures into the NASA Catchments Land Surface Model.
- **Scientific Safeguard:** Regional 9–36 km passive microwave footprints average across heterogeneous land covers, irrigation canals, and soils; they are never treated as exact measurements of an individual farm's root-zone soil water content.
