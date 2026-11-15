# AgroShift AI

Find crops to investigate using your field location, known conditions and growing season. **Dashboard**, **My Farm**, **Recommendations** and **Explore** keep the farmer workflow short while retaining the scientific tools.

## Run

On the configured laptop, double-click **START_AGROSHIFT.cmd** and open [AgroShift](http://localhost:8501). Choose **Analyze my farm** or **Try an example farm**. The example uses genuine archived NASA weather and explicitly fictional field inputs.

Fresh setup with Python 3.14:

    python -m venv .venv
    .venv\Scripts\activate
    python -m pip install -r requirements-dev.txt -r requirements-db.txt
    python -m scripts.dev_database up
    python -m scripts.run_local

Docker Desktop is needed for the PostgreSQL command. Linux/macOS activation: source .venv/bin/activate. Without Docker or PostgreSQL, use python -m streamlit run app.py --server.address=127.0.0.1; the bundled SQLite reference database starts automatically.

The laptop's Python environment is /home/asus/.venvs/agroshift-prep in WSL Ubuntu-26.04. Source is /mnt/c/Users/ASUS/OneDrive/Desktop/nasa. Both launch scripts use the current checkout.

## Farmer workflow

1. Choose a country, then search for a place or use a saved location, coordinates or map point.
2. Enter known water and drainage conditions. Leave unknown measurements blank.
3. Choose growing months and previous crops.
4. Review up to four crop cards per page, select two or three to compare, and open details.
5. Download a report directly from results. Save a named farm and assessment in My Farm, or export a farm profile.

My Farm supports multiple fields, optional drawn boundaries and saved history. Anonymous saves belong to the browser session; export a copy to retain them. Configured OIDC accounts can use private PostgreSQL storage. Live external sign-in needs provider credentials and has not been verified in this environment.

Soil and calendar references are checked after selecting a location. Map estimates never become measured farm inputs. Explore contains climate charts, regional rotations, scenarios, source details, crop search, downloads and the separate educational lab.

## Evidence coverage

| Capability | Available evidence |
| --- | --- |
| Crop catalogue | 107 crop identities across 25 botanical families with cited names, AGROVOC labels and GBIF taxonomy |
| General screening | 107 crops with 295 reviewed global traits (`temp_opt_c`, `soil_ph`, `water_mm`, `duration_days`, `waterlogging_tolerance`) |
| Stage-specific water & extremes | 96 FAO-56 four-stage $K_c$ and duration records across 24 major crops |
| Regional rotations & global rotations | Five crops in confirmed Sri Lankan lowland dry/intermediate fields + global constraint-based two-season succession engine |
| Pest & disease context | 18 reviewed environmental pest/disease pressure indicators across 15 crops (no pesticide prescriptions) |
| Offline climate | 34 exact-location NASA POWER archives, 2001–2025, plus grid-cell caching (`0.5°×0.625°` MERRA-2, `1.0°×1.0°` CERES) |
| FAO land context | 48 GAEZ v5 layers across 24 crops and two water scenarios (`Rain-fed`, `Irrigated`) with polygon intersection |
| Soil & terrain sources | SoilGrids 2.0 WCS (12 properties, 6 depths, `Q0.05`/`Q0.95`), USDA SDA SSURGO (US), ISRIC WoSIS WFS, Copernicus DEM 90 m |
| Independent field validation | Temporal holdout (`84.5%` agreement), missing-data robustness (`0` false promotions), 5-variant ablation; prospective farm yield validation not available |

Capability A is environmental history, B is general crop screening, C is regional rotation screening and D is field validation. Detailed assessments expose what is available for the selected field. Missing requirements remain unknown. No harvest quantity, success probability or worldwide agronomic validation is claimed.

## Database and imports

The local setup uses PostgreSQL 18.6 with separate administrator, reference-reader and private-application roles. Credentials are generated under ignored .cache/. The database binds to localhost and persists in a Docker volume.

    python -m scripts.dev_database status
    python -m scripts.dev_database down

A separately managed reference database can be populated through:

    python -m scripts.knowledge_db seed
    python -m scripts.knowledge_db status
    python -m scripts.knowledge_db conflicts

External PostgreSQL uses AGROSHIFT_DATABASE_URL for the restricted reader. Private saves additionally use AGROSHIFT_PRIVATE_DATABASE_URL and configured OIDC. The import administrator is separate. [Database and identity setup](docs/KNOWLEDGE_DATABASE.md)

Reference ingestion validates units, provenance, scope, versions and conflicts. It does not invent an ECOCROP API or fill unknown traits. Maintainer refreshes use scripts/refresh_provider_data.py. [Provider research and licensing](docs/DATA_PROVIDER_RESEARCH.md)

## Tests and deployment

    python -m scripts.test_local
    python -m scripts.test_local --postgres
    docker build -t agroshift:ui-redesign .
    docker run --rm -p 127.0.0.1:8501:8501 agroshift:ui-redesign

The --postgres test command requires the local database and optional dependencies. It creates and removes disposable test databases/roles. Browser checks use scripts/check_redesign.cjs (also available through check_farmer_ui.cjs) and scripts/check_farm_boundary.cjs. Install playwright-core and axe-core in a separate tooling folder and set NODE_PATH, CHROME_PATH and optional AGROSHIFT_URL. The redesign check exercises five viewport sizes and writes actual screenshots and an accessibility log under artifacts/ui-redesign/.

The image runs as an unprivileged user and excludes secrets.toml. Production hosting needs HTTPS, WebSocket support, protected database connections and verified OIDC setup. No public hosting account or URL is configured.

## Documentation

- [Baseline system audit](docs/BASELINE_AUDIT.md)
- [Climate and satellite data research](docs/CLIMATE_AND_SATELLITE_RESEARCH.md)
- [Soil data research and reconciliation](docs/SOIL_DATA_RESEARCH.md)
- [GAEZ v5 and FAO Crop Calendar integration](docs/GAEZ_AND_CALENDAR_INTEGRATION.md)
- [Water balance and agro-climatic extremes modeling](docs/WATER_AND_EXTREMES_MODELING.md)
- [Global rotation and pest/disease modeling](docs/ROTATION_AND_PEST_MODELING.md)
- [6-Layer evidence combination and automation](docs/EVIDENCE_COMBINATION_AND_AUTOMATION.md)
- [Agricultural validation and 5-variant ablation study](docs/AGRICULTURAL_VALIDATION.md)
- [Deployment, refresh governance and security](docs/DEPLOYMENT_AND_SECURITY.md)
- [UI redesign, research and verification report](docs/UI_REDESIGN_RELEASE.md)
- [Farm platform architecture and prior release](docs/FARM_PLATFORM_RELEASE.md)
- [Global scientific method](docs/GLOBAL_SCREENING.md)
- [Database and private storage](docs/KNOWLEDGE_DATABASE.md)
- [Provider access and licensing](docs/DATA_PROVIDER_RESEARCH.md)
- [Original scientific audit](docs/SCIENTIFIC_AUDIT.md)
- [Demonstration guide](DEMONSTRATION_AND_SUBMISSION.md)
- [Gemini or other agent handoff](HANDOFF.md)

Inter is bundled locally under the SIL Open Font License in static/Inter-LICENSE.txt. Code is MIT licensed. Each dataset retains its own source terms and attribution. Country boundaries use Natural Earth public-domain geometry and can be approximate near borders and small islands.
