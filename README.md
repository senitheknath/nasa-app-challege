# AgroShift AI & CRESCO

**AgroShift AI** is a scientific crop-screening, rotation-planning, and live field-monitoring platform grounded in NASA Earth observation data, FAO-56 agro-meteorology, and ISRIC soil science. It pairs a **Starlette JSON API** and **107-crop knowledge atlas** with **CRESCO**, an **Expo React Native** mobile app featuring a **3D Field Slab**, **Live Monitor**, and **Cresco AI** (an agronomy assistant powered by Google Gemini `gemini-flash-lite-latest`).

- **Public Repository:** [https://github.com/senitheknath/nasa-app-challege](https://github.com/senitheknath/nasa-app-challege)
- **README:** [https://github.com/senitheknath/nasa-app-challege/blob/main/README.md](https://github.com/senitheknath/nasa-app-challege/blob/main/README.md)

---

## Repository Structure

| Directory | Description | Link |
| :--- | :--- | :--- |
| `agroshift/` | Core scientific engines, NASA/FAO/soil data connectors, 3D slab, rotation engine, and Cresco AI | [agroshift/](https://github.com/senitheknath/nasa-app-challege/tree/main/agroshift) |
| `api/` | Modular Starlette ASGI JSON API (`earth-data`, `agronomy`, `knowledge`, `identity`, `cresco`, `system`) | [api/](https://github.com/senitheknath/nasa-app-challege/tree/main/api) |
| `mobile/` | **CRESCO** Expo React Native mobile app (3D field slab, planner, live monitor, Cresco AI & obstacle-avoiding bubble) | [mobile/](https://github.com/senitheknath/nasa-app-challege/tree/main/mobile) |
| `frontend/` | Streamlit + Folium + Plotly web interface | [frontend/](https://github.com/senitheknath/nasa-app-challege/tree/main/frontend) |

---

## Verified Space-Agency & Agricultural Data Sources

Every external dataset in AgroShift AI is explicitly attributed and provenance-labeled (`measured`, `observed`, `modeled`, `estimated`, `reviewed`, or `unavailable`)—missing values are never coerced to zero or fabricated.

### NASA & Space-Agency Earth Observation
- **NASA POWER** ([power.larc.nasa.gov](https://power.larc.nasa.gov/)) — 25-year daily agroclimatology (`MERRA-2` `0.5°×0.625°` & `CERES` `1.0°×1.0°`) for rainfall (`PRECTOTCORR`), temperature (`T2M`, `T2M_MAX`, `T2M_MIN`), solar radiation (`ALLSKY_SFC_SW_DWN`), wind (`WS2M`/`WS10M`), and root/surface soil wetness (`GWETROOT`, `GWETTOP`).
- **NASA GIBS WMTS** ([earthdata.nasa.gov](https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs)) — Live global satellite map overlays:
  - **SMAP L3 Passive Enhanced Surface Soil Moisture (9 km)** (NASA NSIDC DAAC)
  - **MODIS Terra 8-Day NDVI (250 m)** (NASA LP DAAC)
  - **GPM IMERG Precipitation Rate (10 km / 0.1°)** (NASA GES DISC)
- **NASA CMR Granules API** ([cmr.earthdata.nasa.gov](https://cmr.earthdata.nasa.gov/)) — Real overpass & granule queries for **Harmonized Landsat (30 m)**, **ECOSTRESS (70 m)**, and **SMAP (`SPL3SMP_E`, 9 km)**.
- **Copernicus / ESA Earth Observation** ([dataspace.copernicus.eu](https://dataspace.copernicus.eu/)) — Multi-provider STAC & Open-Meteo Elevation queries for **Copernicus Sentinel-2 L2A (10 m)**, **Sentinel-1 C-Band SAR (10 m)**, **Sentinel-3 SLSTR Thermal (1 km)**, **Copernicus DEM GLO-30**, and **ERA5-Land** reanalysis.

### Soil, Terrain, Climate & Agronomic Reference Sources
- **ISRIC SoilGrids 2.0** ([isric.org/explore/soilgrids](https://www.isric.org/explore/soilgrids)) — WCS (`GetCoverage`) & WMS overlays for soil pH, clay, texture, and multi-depth soil profiles (250 m).
- **ISRIC WoSIS** ([isric.org/explore/wosis](https://www.isric.org/explore/wosis)) & **USDA SDA SSURGO** ([sdmdataaccess.sc.egov.usda.gov](https://sdmdataaccess.sc.egov.usda.gov/)) — Point soil profiles and regional soil survey evidence.
- **UCSB CHIRPS v3.0** ([chc.ucsb.edu/data/chirps](https://www.chc.ucsb.edu/data/chirps)) & **Open-Meteo** ([open-meteo.com](https://open-meteo.com/)) — Gridded precipitation, seasonal forecasts, elevation, and GeoNames place search.
- **FAO Data & Standards** — **FAO-56** Penman-Monteith & Hargreaves $ET_0$ and 4-stage $K_c$ water balance, **FAO EcoCrop** ([fao.org](https://www.fao.org/land-water/databases-and-software/ecocrop/en/)), **FAO GAEZ** ([gaez.fao.org](https://gaez.fao.org/)), **FAO Crop Calendar API**, **AGROVOC**, and **FAOSTAT**.

---

## Core Features

### 1. Starlette JSON API (`api/`)
Lightweight ASGI backend built with **Starlette** and **Uvicorn**, offloading Earth-data and scientific computations via `run_in_threadpool`:
- **System & Health:** `GET /api/health`, `GET /api/system/presets`, `GET /api/system/config`, `GET /api/cache/status`
- **Earth Data & 3D Monitor:** `POST /api/earth-data/autofill`, `POST /api/earth-data/satellite`, `POST /api/earth-data/climate`, `POST /api/earth-data/monitor-3d`, `POST /api/earth-data/monitor-3d/stream`, `GET /api/earth-data/layers`, `GET /api/earth-data/places`
- **Agronomy & Rotations:** `POST /api/agronomy/screen`, `POST /api/agronomy/crops/{crop_id}/details`, `POST /api/agronomy/rotations`, `POST /api/agronomy/report`
- **Knowledge Atlas:** `GET /api/knowledge/crops`, `GET /api/knowledge/categories`, `GET /api/knowledge/status`
- **Identity & Saved Farms:** `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me`, `GET/POST/PUT/DELETE /api/farms`
- **Cresco AI:** `POST /api/cresco/connect`, `GET /api/cresco/status`, `POST /api/cresco/chat`, `POST /api/cresco/clear`, `POST /api/cresco/disconnect`

### 2. 107-Crop Knowledge Atlas & FAO-56 Rotation Engine
- **SQLite Reference Database (`data/knowledge.sqlite`):** 107 crops across 34 botanical families, 100 growth-stage records, 18 environmental pest/disease context indicators, and reviewed global traits.
- **Water Balance & Screening:** Daily FAO-56 Penman-Monteith $ET_0$ (with Hargreaves fallback), 4-stage $K_c$ crop water demand, 6-layer evidence combination, and constraint-based multi-season rotation planning.

### 3. 3D Field Slab & Live Monitor (`agroshift/monitoring/`)
- Combines **Atmosphere**, **Canopy**, a **5×5 Copernicus DEM Terrain Mesh**, and a **4-Horizon Soil Profile** (`0–5 cm`, `5–15 cm`, `15–30 cm`, `30–100 cm`) with Saxton-Rawls hydraulics and 3-way soil wetness fusion.
- **Live Monitor (`live_monitor.py`):** Tracks `t > 0` biological progress, expanding weather-volatility uncertainty, and satellite NDVI canopy assimilation.

### 4. Cresco AI (`agroshift/cresco/`)
Powered by **Google Gemini (`gemini-flash-lite-latest`)** using user-supplied API keys from [Google AI Studio](https://aistudio.google.com/apikey):
- **Live Key Verification:** `/api/cresco/connect` performs a real authenticated Gemini API check, distinguishing invalid keys (`401/403`), unavailable models (`404`), quota limits (`429`), and upstream/network errors.
- **Isolated In-Memory Session Store:** Ephemeral TTL-backed `CrescoSessionStore` (`X-Cresco-Session` header / `cresco_session` HttpOnly cookie). API keys are never persisted to disk, SQLite, or logs, and are wiped on disconnect or expiration. Conversation history is scoped by `(session_id, farm_id)`.
- **Provenance-Labeled Context & Multilingual Support:** Dynamically selects relevant crops and field/rotation context with explicit provenance tags and supports **English**, **Sinhala (`සිංහල`)**, and **Tamil (`தமிழ்`)**.

### 5. CRESCO Mobile App (`mobile/`)
Built with **Expo (`~58.0`)**, **React Native (`0.88.1`)**, **Expo Router**, **TanStack Query**, **Zustand**, and **React Native Reanimated**:
- Field boundary & location setup with automatic Earth-data autofill.
- Interactive **3D Field Slab** (`Slab3DView`) and **Chlorophyll Terrain Map** (`ChlorophyllTerrainMap`).
- Crop screening carousel, multi-season rotation planner, and live monitor.
- Dedicated **Cresco AI** screen (`src/app/cresco.tsx`) plus a global **floating, draggable, obstacle-avoiding `CrescoBubble`** that automatically dodges buttons, text, and navigation chrome.

---

## Quick Start

### 1. Backend API (Python 3.12+)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

Run backend tests:
```bash
pytest
```

### 2. CRESCO Mobile App (`mobile/`)
```bash
cd mobile
npm install
npx expo start
```

Run mobile typecheck & tests:
```bash
cd mobile
npx tsc --noEmit
npx jest
```

### 3. Web Prototype (`frontend/`)
```bash
pip install -r requirements.txt
streamlit run frontend/app.py
```

---

## License

Code is released under the **MIT License** (see `LICENSE`). Integrated NASA, ESA/Copernicus, ISRIC, USDA, UCSB, Open-Meteo, and FAO datasets retain their respective source terms and attributions.
