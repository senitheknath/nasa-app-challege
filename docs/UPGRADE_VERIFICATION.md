# Global Crop Finder verification

Verified 8 November 2026, Asia/Colombo. Recovery branch **codex/before-global-upgrade** retains starting commit **92024df**. Work is integrated on **codex/global-crop-finder**. Database, provider and scientific changes originated in isolated worktrees. The original 71-test baseline passed before changes.

## Executed checks

**103 tests passed, zero failed, zero skipped in 38.45 seconds.** The full run included the actual PostgreSQL policy test. One upstream Streamlit/pandas deprecation warning came from a chart in the educational laboratory.

| Area | Executed evidence |
| --- | --- |
| Farmer workflow | Home → location → conditions → season → crop cards → details → comparison → downloads through Streamlit AppTest |
| International scope | Real archived NASA history for Sri Lanka, India, Kenya, Brazil, the United States and Australia. Kenya completes the guided farmer workflow with one explicitly selected season |
| Unknown values | Empty field size, pH, irrigation amount and rainfall-use fraction remain unknown. Changing rain-only to regular irrigation keeps the amount blank |
| State correctness | New farms clear previous inputs and observations. Failed retrieval cannot reuse a different location. Returning to the season step preserves month and crop-history choices |
| Regional constraints | Original drainage, cultivar, duration, rotation, sensitivity, scenario, provenance and report consistency regressions retained. Global cards cannot override a regional exclusion |
| Catalogue | 32 crop identities, 96 AGROVOC English/French/Spanish labels, 32 botanical-family citations and 37 reviewed global trait records |
| Database | SQLite migrations, repeat import, malformed import rollback, conflicting references, source tracking, translated search and PostgreSQL outage fallback |
| Actual PostgreSQL 18.6 | Fresh schema, reader permissions and RLS with two owner identities. Cross-owner reads, updates and analysis-to-farm links rejected. A local identity fixture exercised the Supabase policy contract |
| Database recovery | Custom-format pg_dump restored into an empty database. Counts matched at 32 crops, 37 global traits and 34 NASA cache records |
| Source failures | Exact-query archive matching, invalid digests, service timeouts, missing soil pixels, malformed calendars, cross-country geocoder results, request deduplication and rate-limit cooldowns |
| Reports | Farmer HTML and JSON contain the same cards as the screen. Regional report intervals match the shared assessment. Unknowns and fictional example inputs remain labelled |
| Observations | The offline collector rechecked all 34 bundled NASA histories. Each has 9,131 dates and its original request, retrieval timestamp and digest |
| Container | Docker build succeeded with pinned application dependencies. The non-root container initialized the reference database, passed pip check and became healthy |
| Real browser | Chrome via Playwright at 320×740, 390×844, 768×1024 and 1366×900. Keyboard activation, visible navigation, card limits, details, comparison and actual HTML downloads passed. No horizontal overflow in results/comparison |
| Downloaded files | JSON and CSV retrieved from the running container. JSON matched the fictional profile and verified-cache provenance. CSV contained 9,131 daily rows |

The responsive test exercises keyboard activation of the primary action and the main workflow. Full WCAG 2.2 AA conformance and screen-reader certification were not evaluated.

## Live provider checks

The source research and retained raw assets distinguish live verification from archived and unavailable data. [Provider research](DATA_PROVIDER_RESEARCH.md)

- AGROVOC returned the maize concept live. The catalogue retains previously verified multilingual concept labels.
- Open-Meteo returned ten Nairobi place matches through the documented geocoder.
- FAO Crop Calendar returned 89 Kenyan crop choices. Selecting the returned Sri Lankan cowpea ID produced four actual zone-season records.
- SoilGrids WCS returned modelled pH 5.8 at the Anuradhapura point. The exact Nairobi weather point returned no usable soil pixel. Its field pH stays unknown. The separate archived point at −1.28333, 36.81667 has its own 6.1 estimate and is never substituted for another point.
- Twelve downloaded GAEZ v5 rasters were validated against their geometry, digest and class legend. Rainfed and irrigated low-input layers produce distinct model classes.
- The FAOSTAT published bulk extract retains 87 country/crop/year production values. Tests checked the archived Kenya figure and its official-data flag.

ECOCROP bulk redistribution permission, CROPIX and additional Crop Ontology service access remain limited as documented in the source register. The release includes a reviewed-data import path. No bulk ECOCROP extract is claimed.

## Architecture decisions

The existing Streamlit/Python application was retained. A lightweight router and smaller UI modules replace the competing wallet, chat and wizard entry points. Crop Finder shows the primary farmer task. Research loads the heavier plots, laboratory and reference tables on demand.

The application reads the central reference schema through knowledge.py. PostgreSQL is optional and SQLite supplies a persistent offline reference store. Farmer profiles are held in browser sessions with downloadable reports. Database tables and RLS policies for private records are present, while login and cloud-save UI require a hosted identity integration.

General first-season crop screening is available for 14 crops with reviewed global traits. The five-crop Sri Lankan reference pack supports regional two-season comparisons. Fifteen catalogue entries currently have names and taxonomy only. Searchable countries and crop names do not establish field performance.

A single season can span 30–366 days for broad reference comparison. Two-season regional windows remain 30–240 days each and cannot overlap. Farmer dates remain explicit. Additional country directories identify published guidance without assigning unreviewed zone or cultivar thresholds.

## Release limits and reproduction

Public hosting credentials were unavailable. This release is locally runnable and Docker-deployable. HTTPS hosting, domain configuration and a live Supabase identity connection remain outstanding. Field-outcome validation and competition eligibility also remain outstanding.

Run the suite with Python 3.14 and requirements-dev.txt. For the live PostgreSQL test also install requirements-db.txt and supply AGROSHIFT_TEST_PG_ADMIN for a disposable local cluster with database/role creation privileges. Without that variable, the PostgreSQL test is skipped.

For browser checks install playwright-core, set CHROME_PATH to an installed Chrome executable, optionally set AGROSHIFT_URL and run scripts/check_farmer_ui.cjs with Node. The recorded run targeted the Docker application on port 8512. Captures and downloaded reports are under artifacts/browser in the working checkout. The [home preview](crop-finder-preview.png) and [mobile result preview](farmer-results-mobile.png) are also included in the release.

The release ZIP includes source, all migrations, seed data, provider samples, raw observations and these instructions. HANDOFF.md explains continuation with Gemini or another assistant.
