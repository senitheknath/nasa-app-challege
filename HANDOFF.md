# AgroShift continuation handoff

Updated 9 November 2026. Current branch: codex/ui-redesign. Recovery branch codex/before-ui-redesign preserves 10a2e80. The only authoritative working checkout for this release is C:/Users/ASUS/OneDrive/Desktop/nasa.

Read README.md, docs/UI_REDESIGN_RELEASE.md, docs/FARM_PLATFORM_RELEASE.md, docs/GLOBAL_SCREENING.md, docs/DATA_PROVIDER_RESEARCH.md and docs/KNOWLEDGE_DATABASE.md first. Use git status and git log -1 --oneline before editing.

## What is implemented

Streamlit/Python remains the framework. app.py routes four destinations to finder_ui.py, farm_ui.py, results_ui.py and research_ui.py. screening.find_options supplies the crop cards and report records, calling decision.assess for applicable Sri Lankan regional fields. No parallel AI recommendation engine was added. The redesign keeps the existing router, adds shared ui_components.py and ui_state.py, two-column/four-card results, persistent draft/comparison state, direct report downloads and a filtered catalogue fragment. Native theme configuration and local Inter fonts provide the visual foundation.

The database contains 32 identities; 14 crops have some global traits, five support regional rotations, two overlap, and 15 are catalogue-only. Genuine NASA archives cover 34 exact locations. Soil and GAEZ estimates stay separate from measured inputs. No field-success probabilities or yields are supplied.

Farm profiles, validated boundaries and history work in browser-session mode. Private PostgreSQL CRUD, ownership, optimistic revisions and immutable assessment history are implemented behind Streamlit OIDC. Real PostgreSQL tests verify isolation. Live identity-provider credentials are absent, so an actual external sign-in has not been tested.

Local PostgreSQL is reproducible with Docker, using generated credentials and separate restricted roles. Its secret files are under ignored .cache/ and are deliberately absent from release exports. Recreate credentials and a new database volume in another environment; do not assume the laptop's local credentials exist.

## Run and verify

Use Python 3.14. Install requirements-dev.txt and requirements-db.txt. Run python -m scripts.dev_database up, then python -m scripts.run_local. For a reference-only offline demo, python -m streamlit run app.py also works with SQLite.

Run python -m scripts.test_local --postgres after starting the local database. Without PostgreSQL, use python -m scripts.test_local; two PostgreSQL checks will skip. Browser checks are scripts/check_redesign.cjs and scripts/check_farm_boundary.cjs and need playwright-core, axe-core and CHROME_PATH. Set NODE_PATH to the external test-tool installation. See the release report for actual test outcomes.

The browser scripts do not certify WCAG compliance. Scientific tests verify software invariants and provenance, not crop performance in the field.

## Exchange with Gemini, Astra or another agent

No Git remote is configured. There is no automatic synchronization with another agent's environment.

Use artifacts/agroshift-ai-ui-redesign.zip or artifacts/agroshift-ai-ui-redesign.bundle as an explicit transfer. Actual browser screenshots and accessibility results are in artifacts/agroshift-ui-verification.zip. The source ZIP includes tracked code, data, migrations and documentation, but excludes credentials, local farm records, Docker volumes and Python environments. Import it as the existing project, create a new branch and preserve this release. The Git bundle can be cloned to retain history; run git bundle verify before importing it.

Bring changes back as a reviewable Git commit/patch or source archive. Compare against this branch, inspect migrations and sources, and run the regression suite before integrating. Never infer access to another machine or a shared filesystem.

No particular Gemini model/version or paid AI API is required. Optional assistant credentials only route explanations; they do not alter the scientific ranking.

## Remaining external work

Configure and verify a real OIDC provider and public HTTPS host if launching publicly. Add reviewed cultivar/zone references and additional legitimate crop traits through the import pipeline. Resolve provider redistribution terms before bundling calendar records. Independent agricultural field validation remains outstanding.

Migration files must stay byte-stable after application. db/migration_compatibility.json allows only three exact known legacy checksum variants caused by one removed terminal newline in the previous packaging step; it does not authorize arbitrary edits or rewrite database history.

Do not regenerate missing weather, silently supply farm measurements, change applied migration files, reuse the application database role in browser clients, or broaden Sri Lankan rotation rules to other countries.

## Continuation prompt

Continue the existing AgroShift AI release. Read HANDOFF.md and its linked scientific and verification documents. Keep Crop Finder minimal, preserve unknown values and source provenance, and review every new scientific trait and geographical scope. Inspect Git status, implement changes on an isolated branch, run tests and update the release report. Do not claim your environment is synchronized with another agent unless an explicit transfer has been completed.
