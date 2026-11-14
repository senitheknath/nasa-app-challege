# Database Architecture, Security, Authentication, and Deployment

**Date:** 2026-11-09  
**Scope:** Section 12 (`Knowledge Database`), Section 13 (`Persistence & Security`), Section 14 (`Deployment`), Section 25 (`Security and Privacy`)

---

## 1. Dual-Database Architecture & Least-Privilege Isolation

### 1.1 Reference Knowledge Store (`agroshift/knowledge_store.py`, `agroshift/knowledge.py`)
- **Primary Shared Backend:** PostgreSQL (`AGROSHIFT_DATABASE_URL`) in schema `agroshift`, accessed by the Streamlit runtime in `READ ONLY` repeatable-read transactions (`default_transaction_read_only=on`, `statement_timeout=15000`).
- **Automatic Offline Fallback:** Local SQLite snapshot (`~/.cache/agroshift/knowledge.sqlite3` or `:memory:`) seeded deterministically from versioned JSON/CSV manifests (`data/crops.json`, `data/global_catalogue.json`, `data/global_nasa_stations_summary.csv`, `data/provider_registry.json`).
- **Least-Privilege Reader Role (`db/reference_reader.sql`):** Grants `USAGE` on schema `agroshift` and `SELECT` on reference views/tables (`ag_catalogue_cited`, `ag_global_trait_named`, `ag_growth_stage_reviewed`, `ag_pest_context_reviewed`, `ag_cultivar_trait_reviewed`, `ag_name_token`, `ag_crop_name`, `ag_pack`, `ag_soil_observation`, `ag_validation_observation`, `ag_refresh_policy`) to `agroshift_reader`, with `REVOKE CREATE ON SCHEMA agroshift FROM PUBLIC`.

### 1.2 Migration History (`db/migrations/001`–`008`)
- `001_reference.sql` – `007_search_collation.postgres.sql`: Preserved with immutable SHA-256 checksums (`ag_schema_version` & `db/migration_compatibility.json`).
- `008_scientific_expansion.sql`: Adds `ag_cultivar_trait`, `ag_growth_stage`, `ag_soil_observation`, `ag_pest_context`, `ag_validation_observation`, `ag_refresh_policy`, and reviewed citation views (`ag_growth_stage_reviewed`, `ag_pest_context_reviewed`, `ag_cultivar_trait_reviewed`).

---

## 2. Private Multi-User Farm Workspace (`agroshift/private_store.py`, `db/server_access.sql`)

- **Strict Schema Isolation:** Private user records reside in schema `agroshift_private` (`AGROSHIFT_PRIVATE_DATABASE_URL`), completely separate from `agroshift_reader`.
- **OIDC Authentication & Ownership (`agroshift/farm_ui.py`):**
  - Verifies `st.user` OIDC claims (`iss` issuer + `sub` subject) only when `AGROSHIFT_AUTH_CONFIGURED=1`.
  - Binds database transactions to the authenticated `(issuer, subject)` via `set_config('agroshift.user_issuer', ...)` and `set_config('agroshift.user_subject', ...)`.
  - Enforces PostgreSQL Row-Level Security (`FORCE ROW LEVEL SECURITY` on `app_users`, `saved_farms`, `saved_boundaries`, `saved_assessments`, `saved_Comparisons`) and `SECURITY DEFINER` RPCs (`save_farm_record`, `list_saved_farms`, `load_saved_farm`, `delete_saved_farm`) so a user can never read, modify, or enumerate another farmer's records.
- **Portable Anonymous Mode:** Farmers who do not sign in can export and re-import validated, self-contained farm JSON files (`agroshift/farm_records.py`) without server-side tracking.

---

## 3. Security & Privacy Hardening

1. **Zero Credential Leakage:** Database fallback and provider error handlers log only exception class names (`type(exc).__name__`) and never expose connection strings, tokens, or stack traces in UI messages (`tests/test_knowledge_store.py`, `tests/test_private_store.py`).
2. **Path Traversal & Payload Bounds:**
   - Station manifest paths are verified via `path.is_relative_to(root.resolve())`.
   - Remote provider responses are capped at `MAX_BYTES = 1_000_000` (`agroshift/provider_http.py`), and offline bulk refresh downloads enforce explicit byte limits (`scripts/refresh_provider_data.py`).
3. **GeoJSON Polygon Validation (`boundary_polygon`):** Enforces WGS84 coordinates, single exterior ring, $\le 250$ vertices, non-self-intersection, positive area, and point-in-polygon enclosure of the farm coordinate before storage or GAEZ sampling.
