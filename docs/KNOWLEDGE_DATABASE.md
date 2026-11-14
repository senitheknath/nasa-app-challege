# Agricultural knowledge database

The app reads versioned crop names, translations, global evidence and source citations from SQLite by default. SQLite builds itself from the checked-in release on first use. Subsequent queries use an in-process cache. Set `AGROSHIFT_KNOWLEDGE_PATH` to use a separately managed SQLite release. Every process opens its own connections. A configured but unreachable PostgreSQL instance falls back to the packaged references and exposes the change through `knowledge_status()`. The Explore view displays this status. The local run helper uses PostgreSQL automatically when its generated configuration exists. No farmer records are collected by the reference cache.

## Local use

From the repository root in the project's Python environment:

```bash
python -m scripts.knowledge_db seed --sqlite .cache/agroshift.sqlite3
python -m scripts.knowledge_db status --sqlite .cache/agroshift.sqlite3
python -m scripts.knowledge_db conflicts --sqlite .cache/agroshift.sqlite3
export AGROSHIFT_KNOWLEDGE_PATH="$PWD/.cache/agroshift.sqlite3"
```

Run `seed` to refresh bundled releases in a managed SQLite file. For a read-only filesystem, the automatic bundled release can operate in memory. An SQLite file can be restored by rerunning the seed or by using SQLite's backup command. Use a fresh path for a trial import.

## PostgreSQL or Supabase

1. Create an isolated PostgreSQL database. Keep the import administrator's connection string in `AGROSHIFT_IMPORT_DATABASE_URL` in the migration environment. Supply TLS parameters appropriate for the host, including server certificate verification. Keep this credential out of the application's configuration.
2. Install the optional driver using `python -m pip install -r requirements-db.txt`. Run `python -m scripts.knowledge_db seed --postgres`. It creates the `agroshift` schema, applies numbered migrations and imports reviewed data. `migrate --postgres` applies migrations without importing.
3. Provision a separate login named `agroshift_reader` with a secret supplied by the host. Give the login only the grants in `db/reference_reader.sql`. It requires no table ownership, administrative role, schema creation or RLS bypass. Export that login's DSN as `AGROSHIFT_DATABASE_URL` in the app environment and install the driver there. Run `python -c "from agroshift.knowledge import knowledge_status; print(knowledge_status())"` to confirm the selected backend.
4. On a Supabase project using authenticated user sessions, administrators can apply `db/supabase_authenticated.sql`. This adapter uses the JWT identity furnished by Supabase to enforce ownership. The standalone migration enables and forces row security with default denial for both private tables. The Streamlit server adapter in private_store.py now supports configured OIDC accounts on ordinary PostgreSQL. Anonymous farms remain in browser-session storage.

The read login can query the reference views, crop names and release versions. Private farm profiles and saved analyses share a composite farm/owner foreign key. An analysis can refer only to a farm of the same owner. Per-user access uses separate authenticated sessions. Do not expose migration, superuser, Supabase service-role or reader passwords in client code. [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) and [Supabase policies](https://supabase.com/docs/guides/database/postgres/row-level-security).

## Import and review

`seed` reads the regional pack, global catalogue, and archive manifest. It also ingests the dated provider registry when supplied. The NASA table contains metadata and object paths. The source envelopes stay in the file archive. The manifest's digest identifies each upstream payload. NASA's existing reader still verifies it before use. Provider rows record a dated probe result.

For a legally obtained ECOCROP export or another reviewed source, normalize only records covered by the applicable terms into the format in `data/global_catalogue.json`. Confirm permission to store and redistribute the intended fields, retain provider attribution and record the version. Compose a complete new global release that includes the entries being retained. Use `python -m scripts.knowledge_db import-global --file RELEASE.json --sqlite TRIAL.sqlite3` or the `--postgres` backend. The importer takes a local file. Upstream downloads, access credentials, rate limits and release licensing remain the responsibility of the applicable provider connector or authorized data curator. It does not fetch a speculative ECOCROP endpoint.

- Each release includes a version, retrieval date, source registry, crop identities and aliases, and traits. Source entries carry a stable ID, document URL, title, version and licensing information when known. Distinguish the catalogue release revision from an upstream dataset version. The audit preserves release versions and retrieval dates independently.
- A numeric trait requires both finite endpoints, original units, a source, an evidence type, explicit geography, and a review status. Scope can additionally identify a cultivar and farming system. Unknown values stay absent. The imported Sri Lankan pack retains a null retrieval date where its upstream metadata did not record one.
- Imports serialize by release and commit atomically. Unchanged checksums skip work. A changed release replaces its own rows and retires removed evidence while retaining other packs. Reusing a published version for changed content fails. The checksum uses LF-normalized file bytes for portability across Git checkouts. The history records accepted and rejected imports without storing connection strings. Keep original release files in versioned storage for replay.
- Distinct, currently reviewed values for the same crop, trait and applicability remain in the evidence table. The conflict view flags both, and the global screening view withholds them pending review. Identical published values can retain more than one citation. Catalogue status is the highest level available anywhere. The location-specific engine separately decides which evidence applies.
- Botanical families, names, cultivars, source definitions, regional support, trait and soil evidence use foreign keys. The calendar and rotation-constraint tables are ready for sourced packs. The existing Sri Lankan engine retains its audited local rules. The database contains only reviewed records supplied by the release.

## Backup and verification

Use the host's protected credential store or PostgreSQL service files. For example, `pg_dump --format=custom --schema=agroshift --file=reference.dump "$PGDATABASE"` creates a backup. Restore into a separate empty database with `pg_restore --exit-on-error --no-owner --dbname="$RESTORE_DATABASE" reference.dump`. Give the restoration administrator the required grants. For databases with private records, restrict and encrypt backups according to your hosting policy. Keep source files and climate objects in the backup plan.

The November 8 development checks imported the same 32 crops, 37 reviewed global ranges and 34 NASA archive records into SQLite and PostgreSQL 18.6. A custom-format PostgreSQL backup restored into an empty database with identical crop, translation, reference and version query output. Six database tests checked rollback, repeat imports, conflicting references, unknowns, translated search, fallback and private access. A real PostgreSQL test verified reader privileges and isolation for two owners against the SQL policy, using a local test function to supply their identities. Hosted Supabase identity delivery requires a live environment and was not exercised.

To repeat the live policy test, install `requirements-db.txt` and `requirements-dev.txt`. Set `AGROSHIFT_TEST_PG_ADMIN` only to a disposable local PostgreSQL cluster with database and role creation privileges. Run `python -m pytest tests/test_knowledge_store.py tests/test_postgres_knowledge.py`. It creates and removes a random test database and roles. With no test connection configured, the PostgreSQL test is skipped and the SQLite tests run.


## Farm-platform additions

Run python -m scripts.dev_database up to provision local PostgreSQL 18.6, seed the existing release and apply both access-grant files. Python -m scripts.run_local selects its restricted reference reader. Generated administrator/reader/app passwords live under ignored .cache/ and must be kept with the local volume. The Compose image is pinned by digest, with port 56542 bound only to localhost.

Migration 005 adds full-name/word tokens and indexed prefix searches. Migration 006 adds farmer_accounts, farm revision checks, timestamps and a deduplicating history index. Migration 007 gives PostgreSQL prefix ranges an explicit C collation independent of the database locale. Migration 008 (`008_scientific_expansion.sql`) adds cultivar traits (`ag_cultivar_trait`), FAO-56 stage-specific growth coefficients (`ag_growth_stage`), benchmark soil profile observations (`ag_soil_observation`), reviewed environmental pest/disease context (`ag_pest_context`), validation observation records (`ag_validation_observation`), and dataset refresh policies (`ag_refresh_policy`), expanding the global seed (`2026-11-09.global.3`) to 107 crops, 295 reviewed traits, 96 growth-stage records, and 18 pest context records. No previously committed migration was edited. Farm history queries return ten rows per page; the catalogue also returns ten rows per page.

For private OIDC storage, install requirements-db.txt, configure .streamlit/secrets.toml from the example, and set AGROSHIFT_OIDC_ISSUER and AGROSHIFT_PRIVATE_DATABASE_URL. Use the restricted agroshift_app login with db/server_access.sql. The server derives an owner UUID from the verified issuer and subject, checks token expiration, and sets ownership only inside each transaction. Session data is cleared if the authenticated owner changes. No private query is globally cached.

This role is trusted application infrastructure: never grant membership to browser/PostgREST roles. Its RLS policy is restricted to that role. The existing Supabase auth.uid policy remains separate. A user granted only the Supabase policy cannot choose an owner by setting the server adapter's session variable.

Farm profile edits use optimistic revision checks. Saved reports preserve their own inputs, NASA provenance, reference versions and source context. Duplicate saves of the same assessment are idempotent. The runtime rejects superuser or BYPASSRLS connections for private storage.

Anonymous farms and history exist only in the Streamlit session; profile exports/imports provide a portable copy. Boundary imports are validated and never used to invent a field area or improve source-grid resolution.

The current verification record, live-login limits and deployment commands are in [FARM_PLATFORM_RELEASE.md](FARM_PLATFORM_RELEASE.md). To exercise the local real-PostgreSQL suite without printing credentials, run python -m scripts.test_local --postgres.
