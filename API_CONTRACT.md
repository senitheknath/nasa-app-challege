# AgroShift Backend API Contract (For UI / AI Integration)

**Base URL:** `http://127.0.0.1:8000` (CORS enabled for `*`)  
**Start Server:**
```bash
.venv/bin/python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

This document defines every endpoint in the modular AgroShift Starlette API (`api/routes/`), exact JSON request/response schemas, optional authentication for saving farms, and a direct field-mapping guide for the `UI` branch (`TerraforgeUserData` in `input.js` / `workflow.js`).

---

## 1. Quick Mapping Guide for `UI` Branch (`TerraforgeUserData`)

If you are wiring `origin/UI` (`input.js`, `workflow.js`) to this backend:

| UI State (`TerraforgeUserData`) | Backend Endpoint | Mapping Notes |
| :--- | :--- | :--- |
| Map pin / polygon drawn (`parcel.center`, `parcel.coordinates`, `territory.code`) | `POST /api/earth-data/autofill` | Convert `[{lat, lng}, ...]` to GeoJSON Polygon `[[lng, lat], ...]`. Returns geodetic `area_ha`, SoilGrids `ph`, Copernicus DEM `drainage` & `slope_pct`. |
| Satellite layers & overpasses | `POST /api/earth-data/satellite` | Returns 3 NASA GIBS WMTS tile URLs (SMAP Soil Moisture, MODIS NDVI, GPM IMERG) + NASA CMR satellite overpasses. |
| Climate chart & suggested season | `POST /api/earth-data/climate` | Returns 25-yr NASA POWER summary, 12-month climatology, and `suggested_window`. |
| Rotation cycle planning (`rotationPlan.seasons`) | `POST /api/agronomy/rotations` | Convert `startDate` (`"2026-10-01"`) $\to$ `{start_month: 10, start_day: 1}`, `harvestDate` $\to$ `{end_month, end_day}`. Returns ranked rotations (`0–100` score) + exact Gantt timelines! |
| Crop screening & sowing matrix | `POST /api/agronomy/screen` | Screens all 107 crops for the farm's climate, soil, and windows. |
| Optional user login & saved farms | `POST /api/auth/register`, `POST /api/farms` | Login is **optional**. All agronomy/earth-data endpoints work anonymously with inline `farm` JSON, or with `farm_id` when `Authorization: Bearer <token>` is sent. |

---

## 2. Earth Data Endpoints (`api/routes/earth_data.py`)

### `POST /api/earth-data/autofill`
Derives geodetic area, SoilGrids pH, and Copernicus DEM slope/drainage from coordinates or a drawn GeoJSON polygon.

**Request:**
```json
{
  "country": "LK",
  "latitude": 8.3114,
  "longitude": 80.4037,
  "boundary": {
    "type": "Polygon",
    "coordinates": [[[80.400, 8.310], [80.405, 8.310], [80.405, 8.315], [80.400, 8.315], [80.400, 8.310]]]
  },
  "offline": false,
  "refresh": false
}
```

**Response (`200 OK`):**
```json
{
  "location": { "country": "LK", "latitude": 8.3114, "longitude": 80.4037 },
  "autofill": {
    "area_ha": { "value": 30.59, "acres": 75.59, "unit": "hectares", "source": "Geodetic area calculated from drawn field boundary" },
    "ph": { "value": 5.8, "source": "ISRIC SoilGrids 2.0 (modelled mean pH in water, 0–5 cm depth)" },
    "drainage": { "value": "well_drained", "slope_pct": 1.2, "elevation_m": 95, "source": "Copernicus DEM 90 m" },
    "climate": { "seasonal_rainfall_mm": 1180.5, "temperature_c": 27.8, "root_zone_wetness": 0.42 }
  }
}
```

### `POST /api/earth-data/satellite`
Returns NASA GIBS WMTS raster tile endpoints and NASA CMR satellite overpass schedules.

**Request:**
```json
{
  "latitude": 8.3114,
  "longitude": 80.4037,
  "boundary": null,
  "offline": false
}
```

**Response (`200 OK`):**
```json
{
  "location": { "latitude": 8.3114, "longitude": 80.4037 },
  "layers": [
    { "id": "smap_soil_moisture", "name": "SMAP Soil Moisture (9 km)", "wmts_url": "https://gibs.earthdata.nasa.gov/wmts/..." },
    { "id": "modis_ndvi", "name": "MODIS Vegetation Index (NDVI)", "wmts_url": "https://gibs.earthdata.nasa.gov/wmts/..." },
    { "id": "gpm_imerg", "name": "GPM IMERG Rain Rate", "wmts_url": "https://gibs.earthdata.nasa.gov/wmts/..." }
  ],
  "overpass_schedule": {
    "acquisitions_count": 2,
    "acquisitions": [
      { "label": "Harmonized Landsat Sentinel-2 (30 m)", "granule_id": "HLS.L30...", "cloud_cover_pct": 5.0, "status": "available" }
    ]
  }
}
```

### `POST /api/earth-data/climate`
Returns NASA POWER 25-year daily climate summary, 12-month climatology, and auto-suggested growing window.

**Request:**
```json
{
  "country": "LK",
  "latitude": 8.3114,
  "longitude": 80.4037,
  "offline": false,
  "refresh": false
}
```

**Response (`200 OK`):**
```json
{
  "location": { "country": "LK", "latitude": 8.3114, "longitude": 80.4037, "countries_at": ["LK"] },
  "provenance": { "source": "NASA POWER...", "verified": true },
  "summary": {
    "annual_rainfall_mm": 1350.2,
    "mean_temp_c": 27.9,
    "climatology": [
      { "month": 1, "label": "Jan", "rainfall_mm": 85.4, "temperature_c": 25.8, "t_min": 21.5, "t_max": 30.1 }
    ]
  },
  "suggested_window": { "start_month": 9, "end_month": 2, "months": 6, "basis": "Longest rain-supported period..." }
}
```

### `GET /api/earth-data/places?q=anuradhapura&country=LK`
Global place name search and country map bounding view.

---

## 3. Agronomy & Crop Rotation Endpoints (`api/routes/agronomy.py`)

> **Shared `farm` object:** All `/api/agronomy/*` endpoints accept either an inline `farm` object (anonymous) OR `"farm_id": <int>` (when `Authorization: Bearer <token>` is provided).

### `POST /api/agronomy/rotations`
Generates ranked multi-season crop rotation plans (`0–100` score + rating tier) with exact physical DAG timelines, 4 FAO-56 phenological growth stages, turnaround buffers, and delay slack.

**Request:**
```json
{
  "farm": {
    "country": "LK",
    "latitude": 8.3114,
    "longitude": 80.4037,
    "ph": 5.8,
    "drainage": "well_drained",
    "irrigation": "rainfed",
    "previous": "unknown",
    "windows": [
      { "start_month": 10, "start_day": 1, "end_month": 1, "end_day": 20 },
      { "start_month": 3, "start_day": 1, "end_month": 6, "end_day": 30 }
    ]
  },
  "max_sequences": 16
}
```

**Response (`200 OK`):**
```json
{
  "status": "success",
  "total": 16,
  "rotations": [
    {
      "id": "potato_then_sesame",
      "name": "Potato → Sesame",
      "rank": 1,
      "score": 87.0,
      "rating": "Excellent",
      "overall_status": "complementary",
      "components": {
        "climate_suitability": 40.0,
        "transition_synergy": 27.0,
        "timeline_efficiency": 20.0
      },
      "summary": "Complementary botanical rotation",
      "season_1": { "window": "01 Oct – 20 Jan (next year)", "crop_id": "potato", "crop_name": "Potato", "family": "Solanaceae", "status": "possible" },
      "season_2": { "window": "01 Mar – 30 Jun", "crop_id": "sesame", "crop_name": "Sesame", "family": "Pedaliaceae", "status": "possible" },
      "transition": {
        "status": "complementary",
        "benefits": ["Botanical family break between Solanaceae and Pedaliaceae..."],
        "cautions": [],
        "blockers": []
      },
      "timeline": {
        "turnaround_summary": {
          "buffer_days": 7,
          "status": "optimal",
          "advisory": "7-day turnaround allows ideal field drying, plowing, and seedbed prep."
        },
        "slots": [
          {
            "crop_id": "potato",
            "crop_name": "Potato",
            "sowing_date": "2024-10-01",
            "harvest_nominal_date": "2025-02-03",
            "growth_cycle_days": { "min": 106, "nominal": 125, "max": 144 },
            "delay_slack_days": 0,
            "stages": [
              { "stage": "initial", "description": "Emergence & Root Establishment", "start_date": "2024-10-01", "end_date": "2024-10-23", "duration_days": 22 },
              { "stage": "development", "description": "Rapid Vegetative Canopy Growth", "start_date": "2024-10-23", "end_date": "2024-11-27", "duration_days": 35 },
              { "stage": "mid_season", "description": "Flowering & Peak Water Demand (Kc max)", "start_date": "2024-11-27", "end_date": "2025-01-08", "duration_days": 42 },
              { "stage": "late_season", "description": "Grain Fill & Ripening", "start_date": "2025-01-08", "end_date": "2025-02-03", "duration_days": 26 }
            ]
          }
        ]
      }
    }
  ]
}
```

### `POST /api/agronomy/screen`
Screens all 107 crops for a given `farm` and optional `weights` (`temperature`, `water`, `soil`, `diversification`).
- **Request:** `{ "farm": { ... }, "weights": { "temperature": 1.0, "water": 1.0, "soil": 1.0, "diversification": 1.0 }, "include_sowing_matrix": true }`
- **Response:** `{ "farm": {...}, "capabilities": [...], "weather_risk": {...}, "sowing_matrix": [...], "cards": [...] }`

### `POST /api/agronomy/crops/{crop_id}/details`
Deep scientific evidence for a single crop (water balance, FAO stage water demand, GAEZ rainfed/irrigated suitability, pest context).
- **Request:** `{ "farm": { ... }, "boundary": null, "offline": false }`

### `POST /api/agronomy/report?format=json|html`
Generates a full downloadable JSON or HTML agronomic report.

---

## 4. Optional Authentication & Saved Farms (`api/routes/identity.py`)

Users do **not** need an account to run earth-data or rotation endpoints. Accounts are strictly optional for persisting farms across sessions.

| Method & Path | Auth Required | Body / Notes |
| :--- | :--- | :--- |
| `POST /api/auth/register` | No | `{ "email": "...", "password": "...", "display_name": "..." }` $\to$ returns `{ "token": "...", "user": {...} }` |
| `POST /api/auth/login` | No | `{ "email": "...", "password": "..." }` $\to$ returns `{ "token": "...", "user": {...} }` |
| `GET /api/auth/me` | `Bearer <token>` | Returns `{ "user": {...} }` |
| `GET /api/farms` | `Bearer <token>` | Lists all saved farms for the user |
| `POST /api/farms` | `Bearer <token>` | `{ "name": "Field A", "farm": { ... }, "boundary": { ... } }` $\to$ saves and returns `{ "farm": { "id": 1, ... } }` |
| `GET /api/farms/{farm_id}` | `Bearer <token>` | Fetch single saved farm |
| `PUT /api/farms/{farm_id}` | `Bearer <token>` | Update saved farm |
| `DELETE /api/farms/{farm_id}` | `Bearer <token>` | Delete saved farm |

---

## 5. Knowledge Atlas & System/Cache (`api/routes/knowledge.py`, `api/routes/system.py`)

- `GET /api/knowledge/crops?q=&category=&limit=50&offset=0` — Search/paginate the 107-crop atlas.
- `GET /api/knowledge/categories` — List all 14 reviewed crop categories.
- `GET /api/knowledge/status` — Knowledge DB version & crop count.
- `GET /api/health` — Service health check.
- `GET /api/system/presets` — Countries, weather stations, location presets, season templates, GAEZ scale.
- `GET /api/cache/status` — Inspect SQLite GeoCache (`geo_cache.db`), memory climate cache, and knowledge DB.
- `POST /api/cache/clear` — Clear caches: `{ "scope": "all" | "climate" | "knowledge" | "geocache", "data_type": "soil" }`.
- `POST /api/cache/update` — Seed/override a spatial cell in `geo_cache.db`: `{ "data_type": "soil", "latitude": 8.3114, "longitude": 80.4037, "payload": {"ph": 5.8}, "source": "manual" }`.
