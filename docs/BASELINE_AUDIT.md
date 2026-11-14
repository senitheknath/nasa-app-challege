# AgroShift AI — Phase 0 Baseline System Audit

**Audit Date:** 9 November 2026  
**Repository:** `/home/asus/.gemini/antigravity/worktrees/nasa/agroshift_scientific_engineering_upgrade`  
**Active Branch:** `agroshift_scientific_engineering_upgrade`  

---

## 1. Git Repository & Branch State

### 1.1 Branch Topology Discovery
When the worktree `agroshift_scientific_engineering_upgrade` was initialized, it pointed to `main` (`92024df`, *"Integrate 34-hub NASA archives, scientific audit engine, and 71-test suite with PayPal+WhatsApp UI"*). Inspection of all repository refs revealed that the authoritative release branch in the repository is `codex/ui-redesign` (`6358a2f`), a strict 8-commit linear fast-forward descendant of `main` (`92024df`):

1. `92024df` (`main`, `codex/before-global-upgrade`) — Integrate 34-hub NASA archives, scientific audit engine, and 71-test suite
2. `f074b97` — Add portable crop knowledge store with audited imports and private record isolation
3. `6eeaa1c` — Screen global crops with reviewed evidence and multilingual identities
4. `0ad469b` — Retain GBIF species citations for botanical families
5. `e92fa61` — Document crop evidence and distinguish mixed seasons in farmer results
6. `a5061b6` — Add verified global GAEZ, soil, vocabulary, calendar and national evidence
7. `cc630c1` (`codex/global-crop-finder`) — Make Crop Finder the primary farmer workflow with focused results and separate research
8. `10a2e80` (`codex/farm-platform`) — Add farm workspace, private persistence and indexed crop discovery
9. `6358a2f` (`codex/ui-redesign`) — Redesign the farmer workspace with persistent drafts and accessible crop cards

### 1.2 Recovery Checkpoints
- Pre-global-upgrade checkpoint: `92024df` (`main`, `codex/before-global-upgrade`)
- Pre-scientific-engineering-upgrade checkpoint: `6358a2f` (`codex/ui-redesign`)
- Working tree status prior to modifications: clean (`git status --short` empty).
- Fast-forwarded `agroshift_scientific_engineering_upgrade` cleanly to `6358a2f` via `git merge --ff-only codex/ui-redesign`.

---

## 2. Baseline Architecture & Module Inventory

| Module / Path | Baseline Responsibility |
|---|---|
| `app.py` | Main Streamlit entry point and 4-destination router (`Dashboard`, `My Farm`, `Recommendations`, `Explore`). |
| `agroshift/power.py` | NASA POWER Daily API client (`T2M`, `T2M_MIN`, `T2M_MAX`, `PRECTOTCORR`, `RH2M`, `ALLSKY_SFC_SW_DWN`), SHA-256 integrity verification, exact-request disk cache, and 34-station offline archive fallback. |
| `agroshift/climate.py` | Coverage-aware monthly/annual aggregation, recurring `Window` extraction, Climdex `< 1 mm` dry-spell detection, Hargreaves reference $ET_0$, Tetens VPD, $\text{GDD}_{10}$, and descriptive z-score anomaly classification. |
| `agroshift/decision.py` | `Farm` dataclass and validation, Level 1 vs. Level 2 capability guard, Sri Lankan 2-season rotation feasibility and interval-valued MCDA engine (`assess`), and priority sensitivity analysis (`priority_sensitivity`). |
| `agroshift/screening.py` | Global first-season crop screening (`find_options`), combining Sri Lankan regional cards (when `pilot_scope` is confirmed) with general global crop cards from reviewed traits in the knowledge store. |
| `agroshift/knowledge_store.py` | Dual-backend (SQLite and PostgreSQL) schema migration runner (`db/migrations/001`–`007`), atomic release importer (`lk`, `global`, `nasa_manifest`, `providers`), SHA-256 release verification, and conflict detection (`ag_conflicts`). |
| `agroshift/knowledge.py` | Read-only query interface with PostgreSQL-to-SQLite fallback, prefix token search (`ag_name_token`), and in-process LRU caching. |
| `agroshift/providers.py` & `provider_http.py` | External provider adapters: FAO AGROVOC (`terminology`), FAO Crop Calendar (`calendar_crops`, `crop_calendars`), ISRIC SoilGrids 2.0 WCS (`soil_context`, 0–5 cm mean pH only), FAO/IIASA GAEZ v5 5-arc-minute GeoTIFF reader (`gaez_point`) and country CSV summary (`gaez_context`), and FAOSTAT QCL archive reader (`national_production`). |
| `agroshift/farm_context.py` | Asynchronous location enrichment (`location_context`) fetching SoilGrids pH and FAO Crop Calendar crop list in background threads, plus capability tier reporting (`A`–`D`). |
| `agroshift/farm_records.py` & `private_store.py` | Validated `agroshift.farm.v1` profile serialization, 250-vertex non-self-intersecting WGS84 polygon boundary validation, OIDC claim verification, and RLS-enforced PostgreSQL persistence. |
| `agroshift/finder_ui.py`, `results_ui.py`, `research_ui.py`, `farm_ui.py`, `ui_components.py`, `ui_state.py` | Minimalist farmer workflow UI, comparison cards, research tools, and session state persistence. |
| `agroshift/ml_engine.py`, `educational_traits.py`, `global_atlas.py`, `education_ui.py` | Isolated synthetic educational dataset and historical rainfall hindcast backtester in the Learning Lab. Strictly fenced off from farm recommendations. |

---

## 3. Baseline Catalogue, Evidence & Archive Counts

- **Crop Identities (`ag_catalogue_cited`):** 32 crops total:
  - **Regional rotation support (`support_level = 'regional'`):** 5 crops (`rice`, `mung_bean`, `cowpea`, `maize`, `groundnut`) in `data/crops.json` (`2026-11-08.1`).
  - **General global trait screening (`support_level = 'general'`):** 14 crops (`barley`, `cabbage`, `cassava`, `groundnut`, `maize`, `oats`, `onion`, `potato`, `sorghum`, `soybean`, `sunflower`, `sweet_potato`, `tomato`, `wheat`), of which 2 (`maize`, `groundnut`) overlap with the Sri Lankan regional pack.
  - **Catalogue-only (`support_level = 'catalogue'`):** 15 crops (`banana`, `beans`, `chickpea`, `coffee`, `cotton`, `coconut`, `finger_millet`, `lentil`, `oil_palm`, `pea`, `pearl_millet`, `pigeon_pea`, `rapeseed`, `sugarcane`, `tea`, `yam` — 15 non-overlapping).
- **Reviewed Global Evidence Rows (`data/global_catalogue.json`, `2026-11-08.global.2`):**
  - 37 numeric/boolean trait rows across 5 traits (`preferred_daily_mean_air_temperature`, `preferred_soil_ph`, `persistent_waterlogging_conflict`, `seasonal_crop_et`, `indicative_cycle_duration`).
  - 32 botanical family classification rows (`GBIF Backbone Taxonomy`).
- **Regional Evidence Rows (`data/crops.json`, `2026-11-08.1`):**
  - 23 reviewed regional trait rows across 5 Sri Lankan crops.
- **Bundled NASA POWER Archives:**
  - 34 verified 25-year (`20010101`–`20251231`) daily agroclimatology archives (`data/demo_power.json` + 33 `.json.gz` files in `data/stations/`).
- **Bundled GAEZ v5 Rasters (`data/gaez/`):**
  - 12 verified 5-arc-minute GeoTIFF rasters (6 crops: `MZE`, `WHE`, `GRD`, `SOY`, `SRG`, `WPO` × 2 low-input water regimes: `LRLM` rainfed, `LILM` irrigated).

---

## 4. Baseline Test Execution Results

1. **On commit `92024df` (`main`):**
   - Command: `/home/asus/.venvs/agroshift-prep/bin/python -m pytest`
   - Result: **71 passed, 1 warning in 30.99s**
2. **On commit `6358a2f` (`codex/ui-redesign`):**
   - Command: `/home/asus/.venvs/agroshift-prep/bin/python -m pytest`
   - Result: **115 passed, 2 skipped, 1 warning in 41.25s** (the 2 skipped tests are opt-in PostgreSQL tests requiring `AGROSHIFT_TEST_PG_ADMIN`).

---

## 5. Identified Scientific & Engineering Gaps Against Upgrade Specification

1. **Climate Data & Evapotranspiration (Sections 4, 10, 11):**
   - `agroshift/power.py` only permits 6 parameters (`T2M`, `T2M_MIN`, `T2M_MAX`, `PRECTOTCORR`, `RH2M`, `ALLSKY_SFC_SW_DWN`); wind speed (`WS2M`, `WS10M`), surface pressure (`PS`), dew point (`T2MDEW`), and root/surface wetness (`GWETTOP`, `GWETROOT`) are rejected if requested.
   - `agroshift/power.py` caches only by exact coordinate string rather than normalizing to the underlying native NASA POWER grid cell (`0.5° × 0.625°` meteorology / `1.0° × 1.0°` solar) while preserving exact requested farm coordinates.
   - `agroshift/climate.py` computes Hargreaves $ET_0$, but does not implement FAO-56 Penman–Monteith $ET_0$ when wind speed, radiation, humidity, and surface pressure are available, nor stage-specific $ET_c = K_c \times ET_0$ or a daily root-zone water balance.
   - Crop-specific extreme temperature (heat/frost), GDD, and dry-spell risk diagnostics are not connected to crop-specific biological tolerance evidence.
2. **Soil Data & Source Precedence (Section 5):**
   - `agroshift/providers.py` (`soil_context`) only queries `phh2o_0-5cm_mean`. It does not retrieve clay, sand, silt, soil organic carbon (`soc`), total nitrogen (`nitrogen`), bulk density (`bdod`), cation exchange capacity (`cec`), coarse fragments (`cfvo`), or volumetric water content (`wv0010`, `wv0033`, `wv1500`), nor multiple depth intervals (`0-5cm`, `5-15cm`, `15-30cm`, `30-60cm`) or uncertainty quantiles (`Q0.05`, `Q0.95`).
   - Explicit measured-vs-estimated soil comparison object (preserving both, displaying disagreement, and enforcing field measurement precedence) and regional USDA SDA / ISRIC WoSIS lookups are not yet implemented.
3. **GAEZ v5 & Polygon Extraction (Section 6):**
   - `gaez_point` only queries single-point pixels across 6 crops (`MZE`, `WHE`, `GRD`, `SOY`, `SRG`, `WPO`). More crops in the catalogue (e.g., Rice, Barley, Pearl millet, Chickpea, Cowpea, Cassava, Sweet potato, Sunflower, Rapeseed, Cotton, Sugarcane, Banana, Bean) have official GAEZ v5 `RES05-SIX` layers.
   - Polygon-aware cell sampling for farms with a validated `boundary` polygon (reporting all intersected grid cells and class distribution while stating native ~10 km resolution) is not yet implemented.
4. **Agricultural Knowledge Database & Crop Catalogue (Sections 7, 8, 12):**
   - Catalogue has 32 crops. Needs expansion to 100+ legitimate, sourced crop identities (FAO WCA / AGROVOC / GBIF) with strict separation of support tiers (`catalogue`, `general`, `regional`, `validated`) and expanded reviewed FAO traits (FAO Paper 56 Table 11/12/17 $K_c$, rooting depth, depletion fraction $p$, salinity tolerance $EC_e$; FAO Paper 33 / 66 / Training Manual 3).
   - Database schema needs additive migration (`008_...`) to support richer soil profile observations, cultivar traits, pest reference context, provider cache metadata, and independent validation records without modifying migrations `001`–`007`.
5. **Regional Crop Calendars, Global Rotation Engine & Evidence Combination (Sections 9, 13, 16, 17):**
   - FAO Crop Calendar records are displayed as raw tables in an expander, without automated comparison against the farmer's selected planting/harvest window to flag potential zone calendar conflicts.
   - Multi-season rotation planning (`decision.assess`) only runs for the 5-crop Sri Lankan lowland pack; a general constraint-based rotation planner for crops with reviewed cycle duration, botanical family, water/soil traits, and perennial/annual growth habit is needed while preserving the Sri Lankan regional pack.
   - Multi-layer evidence combination (Layers A–F: Data eligibility, Hard constraints, Environmental screening, Correlated model context without double counting, Farmer constraints, Final classification) needs explicit structured representation.
6. **Agricultural Validation & Ablation Pipeline (Section 20):**
   - No reproducible agricultural evaluation and ablation benchmark (`Baseline` vs. `Variant A: +Soil`, `Variant B: +GAEZ`, `Variant C: +Calendars`, `Variant D: Combined Evidence`) currently exists.
