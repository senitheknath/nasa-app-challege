# AgroShift AI — UI/UX redesign release

9 November 2026. Source: this repository, branch `codex/ui-redesign`. Recovery branch `codex/before-ui-redesign` preserves `10a2e80`. This is an implemented Streamlit application, verified locally; it is not a public deployment.

## 1. UI audit and research

The previous app had a useful short farmer workflow and sound separation of research tools, but its vertical three-card results, comparison widget lifecycle, sparse returning dashboard, farm selector and limited catalogue presentation made everyday tasks harder. Browser checks existed, but did not cover the requested five sizes or automated accessibility scanning.

The redesign uses original layout, typography and components. We reviewed official public pages and documentation, not authenticated PayPal/Stripe dashboards, and did not conduct a farmer usability study. The following are design decisions informed by those sources, rather than claims that those products use this exact implementation:

| Reference | Decision applied |
| --- | --- |
| [GOV.UK question pages](https://design-system.service.gov.uk/patterns/question-pages/) | Three short steps; explicit optional measurements; plain questions and a review before assessment. |
| [GSMA AgriTech UX guide](https://www.gsma.com/solutions-and-impact/connectivity-for-good/mobile-for-development/gsma_resources/agritech-ux-design-guidebook/) | Mobile-first task flow, fewer mandatory inputs, visible unknowns, and maps loaded on demand. Local user testing remains necessary. |
| [Stripe Dashboard basics](https://docs.stripe.com/dashboard/basics) and [PayPal invoicing](https://www.paypal.com/us/business/accept-payments/invoice) | Restrained visual hierarchy, consistent navigation, recognizable actions and concise task-oriented screens. No branding or proprietary layouts copied. |
| [OneSoil](https://onesoil.ai/en) | Farm-centered context, field overview and resumable work. No satellite monitoring capability was invented. |
| [EOSDA Crop Monitoring](https://eos.com/products/crop-monitoring/) | Keep field management, maps and environmental exploration organized in separate contexts. |
| [WCAG contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) and [target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) | Contrast checks, visible focus, labelled controls and 44 px primary buttons. The WCAG 2.2 AA minimum target criterion is 24 CSS px with exceptions; 44 px is our larger design target. |

Framework decisions:

- [Native Streamlit themes](https://docs.streamlit.io/develop/api-reference/configuration/config.toml) supply typography, input borders, buttons and semantic colors.
- [Widget lifecycle](https://docs.streamlit.io/develop/concepts/architecture/widget-behavior): stable keys plus supported session persistence keep inputs and selections across views. Domain state remains distinct from disposable widgets.
- [Forms](https://docs.streamlit.io/develop/concepts/architecture/forms): place search uses an explicit submit. The entire wizard is deliberately not an unsubmitted form because clicking the global navigation could discard pending values.
- [Fragments](https://docs.streamlit.io/develop/concepts/architecture/fragments): catalogue search/filter/pagination rerun in a fragment, while queries remain bounded.
- [Native navigation](https://docs.streamlit.io/develop/concepts/multipage-apps/overview) was evaluated. The established router was retained because its nested wizard/detail transitions already fit the application and preserving its state contract avoided a larger migration. Native buttons and keyed containers form the four-destination header.

The initial regression run uncovered 26 failures caused by the previous release's terminal-newline cleanup of applied migrations. After the precise compatibility repair described below, the unchanged baseline passed all 111 tests.

## 2. Design system

White and #F7F9FC surfaces, #14263D navy text, #64748B supporting text, #2563EB primary blue, #1D4ED8 hover/focus, #E2E8F0 content borders and restrained green/amber/red status surfaces. Tokens live in `agroshift/finder_style.py`; native equivalents live in `.streamlit/config.toml`.

The requested palette was adjusted where checks exposed problems. Input/button boundaries use #7C8BA0 for sufficient component contrast. Active navigation hover text uses the darker blue. Native success messages use #126653 on #ECFDF5. Native caption opacity is corrected within the app shell.

Inter is served locally from `static/InterVariable.woff2`, with the SIL Open Font License included. There is no runtime remote-font dependency. Hero 44 px desktop / 34 px mobile; page titles 30 px; section titles 22 px; card titles 18 px; body 16 px; supporting text 13–14 px. Layout uses a centered 1280 px limit, restrained borders, 10 px controls and 14 px cards.

Most styling uses our own component classes or explicit Streamlit container keys. The limited framework adapters are documented in `finder_style.py`: main gutters, header height, caption opacity and the immediate wrapper relationship inside keyed card grids. No generated emotion class names are hardcoded. Streamlit upgrades should rerun the browser tests.

## 3. Files modified and added

| Area | Files |
| --- | --- |
| Entry and theme | `app.py`, `.streamlit/config.toml`, `agroshift/finder_style.py` |
| Farmer workflow | `agroshift/finder_ui.py`, `agroshift/farm_ui.py`, `agroshift/results_ui.py` |
| Explore/search | `agroshift/research_ui.py`, `agroshift/crop_search.py`, `agroshift/knowledge.py` |
| New shared components/state | `agroshift/ui_components.py`, `agroshift/ui_state.py` |
| Exact migration compatibility | `agroshift/knowledge_store.py`, new `db/migration_compatibility.json` |
| Font and image packaging | `static/InterVariable.woff2`, `static/Inter-LICENSE.txt`, `Dockerfile` |
| Verification | `tests/test_ui_redesign.py`, updated `tests/test_app.py`, `tests/test_farm_workspace.py`, `tests/test_corrections.py`, `scripts/check_redesign.cjs`, `scripts/check_farmer_ui.cjs`, `scripts/check_farm_boundary.cjs` |
| Documentation | `README.md`, `HANDOFF.md`, this report, correction note in `docs/FARM_PLATFORM_RELEASE.md` |

No agricultural reference data or migration SQL files were changed. The scientific engine, NASA provider contracts, reporting calculations and private storage implementation were preserved.

## 4. Components created

Shared page headings, captions, context summaries, textual status badges, three-factor finding lists, unknown-value summaries, step indicator, empty state, report downloads and responsive header. `ui_state.py` captures drafts independently of the rendered page and clears inputs when a different farm is started or opened.

A factor marked “checked” only means the engine actually assessed it. It is not automatically shown as within range. Overall categories and constraints come directly from the engine.

## 5. Screens redesigned

First-visit home, returning dashboard, farm list/editor, all three setup steps, crop results, crop details, comparison, catalogue and Explore. Existing climate charts, scenarios, sources, reports, boundary tools and educational lab remain accessible. Explore adds direct Soil information and Maps topics without adding top-level destinations.

## 6. Navigation improvements

Four stable destinations: Dashboard, My Farm, Recommendations and Explore. Desktop uses a horizontal header; narrow screens use a compact two-row navigation. The active destination is visible; selected-farm context appears when space permits. Details/comparison retain the Recommendations context.

Ordinary top-level navigation reuses the loaded dataset and screened cards. Tests replace the weather loader and screening function with failure mocks to prove these functions are not called during draft or result navigation. Explicitly opening another farm, changing weather years or changing scientific priorities still performs the relevant calculation.

## 7. Farm workflow

Search by name is the first location method. Saved archives, coordinates and an optional map remain available. A selected point requires explicit confirmation; optional map preview does not block onboarding.

The Field step supports a name, drainage and irrigation availability. Soil pH, area and water quantities remain optional. Changing from rain-only to irrigated clears the net quantity to unknown; it never invents a water amount. Modelled soil pH is labelled separately from measured pH.

The Season step preserves previous crops, selected months and regional options. A compact review shows location, supplied conditions and unknowns before Find crop options. Drafts survive leaving and resuming setup.

My Farm uses cards with location/season/update information and bounded pages of four. Saving, reopening, exporting/importing, boundary drawing and assessment history are preserved. Anonymous storage is explicitly session-only. Account controls require both private database settings and the required OIDC configuration fields; live external login was not exercised.

## 8. Recommendations and evidence

Results use four cards per page: two columns at wider viewports, one on mobile. Status filtering respects returned categories; an optional alphabetical sort adds no suitability ranking. Cards show temperature, soil and water findings, a visible constraint when present, unknowns, View details and Compare.

Selections are explicit, limited to three, and survive details and ordinary navigation. Comparison uses aligned desktop cards and stacked mobile cards. Details separate why the crop appears, checked factors, unknowns and important constraints. Reference ranges, scope, cultivar qualifications, source links and recorded retrieval dates are available in Scientific evidence; absent legacy dates are disclosed.

HTML reports can be downloaded directly on the results page; JSON and weather CSV are under More download formats. The existing report schema and complete provenance remain intact.

Catalogue search retains indexed prefixes, multilingual names and synonyms. Filters use actual database groups. Search results and suggestions are limited to 10 records per request/page; per-crop evidence queries do not fetch the entire traits table. Catalogue-only entries clearly say that screening thresholds are unavailable.

## 9. Responsive verification

Actual Chrome browser checks exercised the farmer workflow at all requested sizes:

| CSS viewport | Layout and workflow |
| --- | --- |
| 320 × 740 | Single-column cards, readable navigation, no unintended horizontal overflow |
| 390 × 844 | Complete mobile workflow; HTML and JSON downloads; unknown values preserved |
| 768 × 1024 | Two-column cards; usable forms, comparison and catalogue |
| 1024 × 768 | Horizontal header and two-column results |
| 1440 × 900 | Centered desktop layout, farm context and two-column results |

At every size the script checks home, location, field, season, results, comparison, expanded scientific details, retained selections, farm saving/history, dashboard, catalogue search, climate and soil views. The reviewer inspected actual screenshots and corrected double padding in cards, inherited definition-list indentation, a truncated navigation label and contrast issues.

A separate real Leaflet test drew a polygon, saved/exported it, uploaded the JSON and confirmed the boundary after reopening. An isolated local QA harness injected one NASA failure, displayed the error without substitute crop cards, and successfully retried the selected location. That failure was deliberately injected; it is not evidence of a live NASA outage.

## 10. Accessibility checks

The five-size suite scanned 65 actual page states with axe-core against WCAG 2 A/AA, 2.1 AA and 2.2 AA rule tags: **zero detected violations in the final run**. Automated “incomplete” results are retained in the JSON log; they are not represented as passes.

Keyboard Tab/Enter reaches and activates Analyze my farm. The main action is at least 44 CSS px high. Inputs have visible labels, focus styles are retained, text accompanies every result status, and reduced motion is supported.

Measured design-token contrast:

| Pair | Ratio |
| --- | --- |
| Supporting text #64748B on white | 4.76:1 |
| Supporting text #64748B on #F7F9FC | 4.51:1 |
| Primary blue #2563EB and white | 5.17:1 |
| Input boundary #7C8BA0 on #F7F9FC | 3.29:1 |
| Input boundary #7C8BA0 on white | 3.47:1 |

This is not a WCAG certification. Screen-reader testing, touch-device testing, all third-party map internals, all chart interactions and usability studies with farmers remain outstanding. Screenshots and static ratios alone cannot establish full accessibility.

## 11. Scientific and functional regressions

`python -m scripts.test_local --postgres` executes **117 passing tests**, including both real PostgreSQL tests with no skips. One upstream Streamlit/pandas deprecation warning remains.

An exact pre/post JSON comparison confirmed identical scientific cards for six representative countries (LK, IN, KE, BR, US, AU: 14 options each) and the confirmed Sri Lankan example (17 options). This covers status, constraints, assessed/unknown factors, details and sources—not merely the count. It is software regression evidence, not agricultural field validation.

The suite also checks synthetic-data exclusion, unknown water/soil values, geographic scope, report consistency, ownership isolation, farm revisions/history, boundary validation, a 1,000-crop fixture catalogue, bounded/category search and draft/comparison lifecycle.

The migration repair permits only the three known canonical/legacy checksum pairs for migrations 005, 006 and 007, corresponding to one removed terminal newline. It does not modify SQL, rerun applied migrations or rewrite audit rows. A new regression confirms that the exact legacy variant is accepted and an unrelated edit still fails.

The Docker image builds, runs as UID 1000, excludes secrets.toml, serves the local font and passes its HTTP health check. A browser smoke check exercises its SQLite-backed example assessment.

## 12. Actual screenshots and artifacts

Files are generated locally under `artifacts/` and excluded from Git:

- `ui-redesign-baseline/`: screenshots of the previous implementation.
- `ui-redesign/`: actual home, forms, crop cards, comparison, details, farm workspace, dashboard, catalogue, climate and soil captures at all five sizes; HTML/JSON reports; accessibility.json.
- `ui-redesign-boundary/`: actual boundary roundtrip screenshot and exported test farm.
- `agroshift-ui-verification.zip`: collected screenshots and machine-readable verification.
- `agroshift-ai-ui-redesign.zip`: clean source export.
- `agroshift-ai-ui-redesign.bundle`: Git history transfer.
- `agroshift-ui-release-manifest.json`: revision and archive hashes.

These use explicitly entered QA profiles or the labelled fictional example. They contain no account credentials, personal farm database or local database passwords.

## 13. Remaining limitations

The UI is English; crop-name search supports the catalogue's recorded multilingual aliases. Translation of the whole interface is not implemented. This redesign does not expand the agricultural evidence release: 32 catalogue identities, 14 crops with some global traits, five regional rotation crops, 17 distinct crops with some screening support.

Only confirmed Sri Lankan lowland dry/intermediate fields have regional two-season screening. General references are not verified farm-level recommendations. Independent field validation, pest/cultivar coverage, yield or profitability predictions remain absent.

Maps/providers may require network access. The offline archive covers exact bundled points, not every world location. Soil estimates remain coarse model outputs. Anonymous session data can disappear when a session ends. Real OIDC sign-in and public HTTPS deployment require external configuration and remain unverified.

The final source archive is an explicit transfer for Gemini or another agent; there is no automatic synchronization with another workspace or dependence on a particular Gemini model.

## 14. Exact run commands

On the configured Windows laptop, double-click `START_AGROSHIFT.cmd`, then open [the local app](http://localhost:8501).

Equivalent PowerShell command from the project folder:

```powershell
wsl -d Ubuntu-26.04 -- /home/asus/.venvs/agroshift-prep/bin/python -m scripts.run_local
```

Use `--cached-context` to avoid automatic live soil/calendar calls while exploring the bundled location archives.

Fresh Python 3.14 environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt -r requirements-db.txt
python -m scripts.dev_database up
python -m scripts.run_local
```

Without Docker/PostgreSQL, use the automatic SQLite reference fallback:

```powershell
python -m streamlit run app.py --server.address=127.0.0.1
```

Verification on the configured laptop:

```powershell
wsl -d Ubuntu-26.04 -- /home/asus/.venvs/agroshift-prep/bin/python -m scripts.test_local --postgres
$env:NODE_PATH="$env:LOCALAPPDATA\agroshift-ui-check\node_modules"
$env:CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
$env:AGROSHIFT_URL="http://localhost:8501"
node scripts/check_redesign.cjs
node scripts/check_farm_boundary.cjs
```

For another machine, install test-only tooling outside the repository:

```powershell
npm install --prefix "$env:LOCALAPPDATA\agroshift-ui-check" playwright-core axe-core --no-save --no-package-lock
```

Container:

```powershell
docker build -t agroshift:ui-redesign .
docker run --rm -p 127.0.0.1:8501:8501 agroshift:ui-redesign
```

Stop another app using port 8501 before running that container, or map a different local port.
