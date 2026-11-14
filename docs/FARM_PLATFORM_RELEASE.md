# Farm platform release — 8 November 2026

This report covers the latest master brief, implemented in the existing repository at C:/Users/ASUS/OneDrive/Desktop/nasa. The current branch is codex/farm-platform. Recovery branch codex/before-farm-platform preserves commit cc630c1. Earlier global-data work remains intact.

## 1. Problems identified

The existing Streamlit/Python app already had verified global NASA archives, a 32-crop reference catalogue, scoped scientific screening and provider integrations. Remaining gaps were session-only single-farm navigation, private tables without an application identity adapter, whole-catalogue reads, manual context lookup, and uncertainty hidden mostly in details. The old start.sh also pointed at a different directory.

## 2. Problems resolved

The existing framework and scientific engines remain in use. Four destinations organize the app. Farmers can save multiple named farms and frozen assessment history, export/import validated profiles, and draw an optional boundary. Anonymous saves stay in the browser session. Configured OIDC users can use private PostgreSQL storage.

Location confirmation retrieves verified NASA history and attempts soil/calendar context. Exact archived soil values are reused; unsuccessful lookups stay unavailable. Published planting dates require selecting a crop and checking its named zone; they never fill the farmer's dates. Soil map values never replace measured pH.

Indexed multilingual prefix search replaces catalogue-wide reads. A 300 ms debounced search component requests at most ten name suggestions. The catalogue queries ten rows per page, and the previous-crop picker uses bounded queries. Crop screening fetches identities only for reviewed candidate traits.

Cards now identify missing factors. Details and reports preserve assessed factors, unknowns, A–D capabilities, source versions, the exact NASA provenance and separate environmental context. Field validation remains unavailable.

## 3. Files changed

Application: app.py; agroshift/finder_ui.py, results_ui.py, research_ui.py, finder_style.py, finder_report.py; new farm_ui.py, farm_records.py, private_store.py, farm_context.py and crop_search.py.

Database/science interface: agroshift/knowledge.py, knowledge_store.py, screening.py, decision.py; db/reference_reader.sql; new migrations 005_search_tokens.sql, 006_farm_history.postgres.sql and 007_search_collation.postgres.sql; new db/server_access.sql.

Operations: compose.database.yml; scripts/dev_database.py, run_local.py, test_local.py, run.sh, check_farmer_ui.cjs, check_farm_boundary.cjs; start.sh; Dockerfile; .dockerignore; .streamlit/secrets.example.toml; requirements-db.txt.

Tests: tests/test_app.py, test_corrections.py, test_knowledge_store.py, test_postgres_knowledge.py; new test_farm_workspace.py and test_private_store.py. README.md, HANDOFF.md and the database/demonstration guides explain the resulting application.

## 4. Database schema

Twenty base tables exist in PostgreSQL after migration:

- Reference identities: ag_crop, ag_crop_record, ag_crop_name, ag_name_token, ag_family.
- Reviewed evidence and applicability: ag_evidence, ag_source, ag_region, ag_regional_crop, ag_cultivar, ag_growing_calendar, ag_rotation_constraint.
- Releases/operations: ag_pack, ag_import_history, ag_schema_version, ag_nasa_cache, ag_provider_status.
- Private data: farm_profiles, farmer_accounts, saved_analyses.

New tables in this change are ag_name_token and farmer_accounts. Migration 006 adds optimistic revision numbers and update times to farm_profiles, plus deduplicating fingerprints and a history index to saved_analyses. Existing migrations were not rewritten. SQLite applies shared reference migrations and excludes PostgreSQL-only private tables.

Farm profiles include known measurements, crop history, selected windows and an optional single-ring WGS84 GeoJSON boundary. Geometry is validated for coordinates, closure, nonzero area, crossings, a maximum of 250 corners and containment of the selected field point. It is not a land survey or a basis for inferred hectares. Multipart fields, holes and antimeridian boundaries are not supported.

## 5–7. Crop counts

| Evidence | Count |
| --- | ---: |
| Distinct crop identities | 32 |
| Crops with some reviewed global environmental traits | 14 |
| Crops in the regional rotation pack | 5 |
| Crops with either kind of screening evidence | 17 |
| Catalogue-only crops | 15 |
| Reviewed global trait rows | 37 |

Two crops occur in both the global and regional groups. The exclusive catalogue labels are therefore 12 general, five regional and 15 catalogue-only. These counts describe available references, not full agronomic profiles or proof of suitability. The current release has 96 verified AGROVOC names across English, French and Spanish and cited botanical families.

## 8. Working source integrations

The dated provider registry is data/provider_registry.json. The full access/licensing audit is [DATA_PROVIDER_RESEARCH.md](DATA_PROVIDER_RESEARCH.md).

- NASA POWER: exact-coordinate, integrity-verified daily histories; 34 bundled locations covering 2001–2025. Missing or synthetic records cannot enter real screening.
- SoilGrids WCS: modeled mean pH at 0–5 cm, separate from field tests. This release reused the exact Anuradhapura archive (pH 5.8). A live attempt at the Nairobi weather coordinate returned no usable estimate.
- FAO Crop Calendar: live retrieval during this release returned 22 crop entries for Sri Lanka and 89 for Kenya. Zone-specific dates are available through the existing crop lookup; no national date is silently assigned to a field.
- AGROVOC terminology and GBIF botanical-family references: verified stored identities/citations.
- GAEZ v5: 12 verified global raster layers for six crops and two water scenarios, plus the existing national sample connector. These remain independent modeled context.
- FAOSTAT: the stored country production extract and source metadata remain available; national totals are never farm-yield predictions.
- Open-Meteo/GeoNames: bounded place search, with manual coordinates and map selection preserved.

## 9. Unavailable or conditional services

No verified authorized bulk ECOCROP trait download/API was established. The documented reviewed-file importer can ingest legitimately obtained records; no invented REST endpoint or numerical traits were added. FAO describes ECOCROP as discontinued around 2015 with its information incorporated into GAEZ. [FAO ECOCROP](https://www.fao.org/land-water/resources/tools/databases/ecocrop/en/)

SoilGrids REST availability remains restricted; WCS is used, and a point may still have no data. Soil texture, organic carbon, nitrogen and bulk density are not integrated. Crop Calendar data are not packaged for redistribution while its redistribution terms remain unresolved. Crop Ontology remains researched reference access, and CROPIX has no configured authenticated connection. A paid Open-Meteo account and optional Gemini credentials have not been exercised.

OIDC client credentials and a public hosting account are absent. The identity checks and real PostgreSQL isolation work, but a live external-provider sign-in and public HTTPS deployment remain unverified.

## 10. Locations tested

The scientific regression suite checks actual archived NASA provenance and conservative general screening for:

| Country | Location | Latitude | Longitude |
| --- | --- | ---: | ---: |
| Sri Lanka | Anuradhapura | 8.3114 | 80.4037 |
| India | Ludhiana / Punjab | 30.9010 | 75.8573 |
| Kenya | Nairobi | -1.2921 | 36.8219 |
| Brazil | Sinop / Mato Grosso | -12.5425 | -55.7211 |
| United States | Ames / Iowa | 42.0308 | -93.6319 |
| Australia | Wagga Wagga / Riverina | -35.1082 | 147.3598 |

These are software/data-provenance checks. They do not validate crop performance on farms.

## 11. UI changes

Dashboard shows the selected farm, location, data availability and latest screening, with Analyze my farm as the main action. My Farm manages names, fields, boundaries, imports, saved history and optional account access. Recommendations retains three crop cards per page and two/three-way comparison. Explore retains charts, rotation analysis, scenarios, maps in crop details, source lookups, reports and the separate educational lab.

White/neutral surfaces, navy text and restrained blue accents are preserved. Mobile navigation uses a two-by-two layout. Controls have labels and visible keyboard focus; the crop suggestions use native browser input/datalist behavior. Browser checks cover narrow phone, phone, tablet and desktop. This is not a formal WCAG certification or assistive-technology audit.

## Follow-up packaging correction, 9 November 2026

The UI redesign baseline found that the final cleanup after this release removed one terminal newline from migrations 005, 006 and 007 after they had been applied locally. The source SQL was logically identical, but stored checksums no longer matched; the SQLite fallback failed. The redesign repairs this with a fixed compatibility manifest for exactly those canonical/legacy digests. It preserves the applied SQL and database audit records and rejects other edits. The 111-test baseline passed again after the repair. See [the current release report](UI_REDESIGN_RELEASE.md).

## 12. Verification

Final regression command: python -m scripts.test_local --postgres — **111 passed in 44.73 seconds**, with one upstream Streamlit/pandas deprecation warning. Both real PostgreSQL tests ran; none skipped.

Browser verification passed at 320×740, 390×844, 768×1024 and 1366×900: keyboard access, navigation, three-card limit, no horizontal overflow, details, comparisons, live crop-name search, HTML/JSON/weather downloads, saved farms and history. A separate browser test drew an actual Leaflet polygon, saved and exported it, uploaded the farm file, reopened it and confirmed the boundary persisted. Stable panel/upload keys fixed a refresh race found during this check.

Local PostgreSQL 18.6 is healthy. Read-only runtime queries return the 32-crop release; English, Spanish, French and scientific-name prefix searches were exercised against the real database. The Docker image built successfully, passes its HTTP health check, runs as UID 1000, excludes secrets.toml and completes the 17-card example workflow with SQLite fallback. Baseline before these changes: 102 passed and one PostgreSQL test skipped. Development failures included obsolete navigation expectations and a calendar variable that shadowed a helper; both were corrected.

The regression suite covers synthetic-data exclusion, missing values, units, source applicability, water assumptions, scientific/report consistency, atomic imports, indexed search against a 1,000-crop fixture catalogue, private ownership, expired identity claims, boundary validation, optimistic save conflicts, history deduplication, multiple farms and session isolation.

The fixture catalogue tests scale only; its invented test identities are never part of the shipped agricultural reference data.

## 13. Remaining limits

Only the confirmed Sri Lankan lowland dry/intermediate pack supports regional two-window rotations. Global screening evaluates the available factors for the first selected window. Cultivar-specific heat/frost stress, soil reserves, pest pressure, daily water balance, field yields and economic outcomes remain unmodeled.

A map boundary does not improve NASA's source grid resolution. Soil pH is one modeled surface layer and may differ from measured soil. Missing inputs retain uncertainty and do not earn suitability credit. None of the scores or categories is a success probability. Capability D remains false.

Anonymous session data may disappear when the session ends; export farms/reports to retain them. Configured private persistence requires an authenticated account. The application database credential is a trusted-server credential and must never be distributed to browser clients or PostgREST users. App sessions reject expired identity tokens; live provider setup must still be verified before deployment.

## 14. Exact run and deployment commands

Fresh local setup, Python 3.14 and Docker Desktop:

    python -m venv .venv
    .venv\Scripts\activate
    python -m pip install -r requirements-dev.txt -r requirements-db.txt
    python -m scripts.dev_database up
    python -m scripts.run_local

On Linux/macOS, replace activation with source .venv/bin/activate. The app opens at http://localhost:8501. Local PostgreSQL binds only 127.0.0.1:56542. Random local credentials are generated under ignored .cache/. The database volume survives python -m scripts.dev_database down. Keep that credential file protected if retaining the volume.

Without PostgreSQL:

    python -m pip install -r requirements-dev.txt
    python -m streamlit run app.py --server.address=127.0.0.1

On this configured laptop:

    wsl -d Ubuntu-26.04 -- /home/asus/.venvs/agroshift-prep/bin/python -m scripts.dev_database up
    wsl -d Ubuntu-26.04 -- /home/asus/.venvs/agroshift-prep/bin/python -m scripts.run_local

START_AGROSHIFT.cmd and start.sh now launch this current checkout. Stop the existing app before starting another process on port 8501. Use --port 8512 for a second local instance. --cached-context disables new automatic soil/calendar requests while retaining matching archives; interactive place search and explicit source lookups still need internet.

Database status:

    python -m scripts.dev_database status

Local application container:

    docker build -t agroshift:farm-platform .
    docker run --rm -p 127.0.0.1:8501:8501 agroshift:farm-platform

For a hosted database, apply migrations and seed as the isolated import administrator, then grant db/reference_reader.sql to a restricted reference login. Set its connection in AGROSHIFT_DATABASE_URL. For private saves, also provision the restricted agroshift_app login, apply db/server_access.sql and set AGROSHIFT_PRIVATE_DATABASE_URL. Do not grant membership of that role to other user-facing roles.

Copy .streamlit/secrets.example.toml to the ignored secrets.toml and configure a real OIDC client. Set AGROSHIFT_OIDC_ISSUER to the exact issuer in the provider's discovery metadata. Supply secrets through the host's secret manager or a read-only runtime mount; .dockerignore excludes secrets.toml from the image. The existing Supabase JWT policy is an alternative identity adapter, not an interchangeable owner identifier for the new OIDC adapter.

Production requires a configured host with HTTPS, WebSocket support and protected PostgreSQL connections. Use the container health path /_stcore/health. External sign-in, backup/restore policy and actual hosting configuration must be verified for that deployment. No public URL has been created.

Tests:

    python -m scripts.test_local
    python -m scripts.test_local --postgres

Install requirements-db.txt and set AGROSHIFT_TEST_PG_ADMIN only on a disposable cluster to include both real PostgreSQL tests. They create and remove random test databases/roles. Browser verification uses playwright-core, CHROME_PATH, optional AGROSHIFT_URL, and node scripts/check_farmer_ui.cjs. Run node scripts/check_farm_boundary.cjs for drawing/import verification.

Streamlit verifies OIDC tokens; this app additionally checks issuer, subject and expiration before deriving a private owner ID. This extra expiration check follows the documented st.user behavior. [Streamlit user identity](https://docs.streamlit.io/develop/api-reference/user/st.user), [Streamlit login](https://docs.streamlit.io/develop/api-reference/user/st.login)
