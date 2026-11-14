"""Versioned imports for PostgreSQL and the offline reference database."""
from __future__ import annotations

from contextlib import contextmanager
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sqlite3
import unicodedata
from urllib.parse import urlsplit
import uuid

_curr = Path(__file__).resolve()
while _curr != _curr.parent:
    if (_curr / "data").is_dir() and (_curr / "agroshift").is_dir():
        ROOT = _curr
        break
    _curr = _curr.parent
else:
    ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "db/migrations"
REGION = "lk_lowland_dry_intermediate"
UNITS = {"temperature_c": "°C", "water_mm": "mm/season", "ph_preferred": "pH", "duration_days": "days"}


def search_key(value):
    normalized = unicodedata.normalize("NFKD", value.casefold())
    # Keep vowel marks in scripts where stripping them changes the word.
    return "".join(c for c in normalized if not (unicodedata.combining(c) and "COMBINING" in unicodedata.name(c, ""))).strip()


def sqlite_connect(path):
    connection = sqlite3.connect(path, timeout=15, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def postgres_connect(url, *, readonly=False):
    import psycopg
    from psycopg.rows import dict_row
    options = "-c search_path=agroshift,pg_catalog -c statement_timeout=15000"
    if readonly:
        options += " -c default_transaction_read_only=on"
    return psycopg.connect(url, row_factory=dict_row, autocommit=True, connect_timeout=3, options=options)


def is_postgres(conn):
    return not isinstance(conn, sqlite3.Connection)


def run(conn, sql, args=()):
    return conn.execute(sql.replace("?", "%s") if is_postgres(conn) else sql, args)


@contextmanager
def transaction(conn, *, lock=False):
    # Import and migration processes serialize. Readers see the last committed release.
    conn.execute("BEGIN" if is_postgres(conn) else "BEGIN IMMEDIATE")
    try:
        if lock and is_postgres(conn):
            conn.execute("SELECT pg_advisory_xact_lock(72189031)")
        yield
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def digest(data):
    return hashlib.sha256(data).hexdigest()


def migrate(conn):
    alias_path = ROOT / "db/migration_compatibility.json"
    aliases = json.loads(alias_path.read_text()) if alias_path.exists() else {}
    with transaction(conn, lock=True):
        if is_postgres(conn):
            conn.execute("CREATE SCHEMA IF NOT EXISTS agroshift")
            conn.execute("REVOKE CREATE ON SCHEMA agroshift FROM PUBLIC")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ag_schema_version (name TEXT PRIMARY KEY,digest TEXT NOT NULL)"
        )
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if ".postgres." in path.name and not is_postgres(conn):
                continue
            sql = path.read_text(encoding="utf-8")
            checksum = digest(sql.encode())
            row = run(
                conn, "SELECT digest FROM ag_schema_version WHERE name=?", (path.name,)
            ).fetchone()
            if row:
                alias = aliases.get(path.name, {})
                known_packaging_difference = (
                    checksum == alias.get("canonical")
                    and row["digest"] == alias.get("legacy")
                    and digest(
                        (
                            sql + "\n" * alias.get("trailing_newlines_removed", 0)
                        ).encode()
                    )
                    == row["digest"]
                )
                if row["digest"] != checksum and not known_packaging_difference:
                    raise ValueError(
                        f"Migration {path.name} changed after application."
                    )
                continue
            # Migrations use only top-level statements. Native applications share the same DDL.
            for statement in re.sub(r"--[^\n]*", "", sql).split(";"):
                if statement.strip():
                    conn.execute(statement)
            if path.name == "005_search_tokens.sql":
                for row in conn.execute(
                    "SELECT pack_id,crop_id,search_key FROM ag_crop_name"
                ).fetchall():
                    put_tokens(conn, row["pack_id"], row["crop_id"], row["search_key"])
            run(
                conn,
                "INSERT INTO ag_schema_version VALUES (?,?)",
                (path.name, checksum),
            )


def required_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid {label}.")
    return value.strip()


def source_url(value):
    value = required_text(value, "source URL")
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("A source needs an absolute HTTP(S) reference.")
    return value


def iso_date(value):
    if value is not None:
        date.fromisoformat(value)
    return value


def put_source(conn, item):
    key, url = required_text(item["id"], "source ID"), source_url(item["url"])
    previous = run(conn, "SELECT url FROM ag_source WHERE id=?", (key,)).fetchone()
    if previous and previous["url"] != url:
        raise ValueError(f"Source {key} changed URL. Use a distinct source ID.")
    run(conn, """INSERT INTO ag_source VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,license=COALESCE(excluded.license,ag_source.license),
            source_version=COALESCE(excluded.source_version,ag_source.source_version)""",
        (key, required_text(item["title"], "source title"), url, item.get("license"), item.get("version")))


def put_tokens(conn, pack, crop_id, name):
    normalized = search_key(name)
    for token in {normalized, *re.findall(r"[^\W_]+", normalized)}:
        run(conn, "INSERT INTO ag_name_token VALUES (?,?,?) ON CONFLICT DO NOTHING",
            (pack, crop_id, token))


def put_crop(conn, crop, pack):
    key = required_text(crop["id"], "crop ID")
    name = required_text(crop["name"], "crop name")
    family = crop.get("family")
    if family:
        run(conn, "INSERT INTO ag_family VALUES (?) ON CONFLICT DO NOTHING", (family,))
    run(conn, "INSERT INTO ag_crop VALUES (?) ON CONFLICT DO NOTHING", (key,))
    run(conn, "INSERT INTO ag_crop_record VALUES (?,?,?,?,?,?,?,?)", (
        pack,key,name,crop.get("scientific_name"),crop.get("group"),family,crop.get("life_cycle"),crop.get("concept_uri")))
    names = list(crop.get("names", [])) + [{"language":"en", "name":name}]
    if crop.get("scientific_name"):
        names.append({"language":"la","name":crop["scientific_name"]})
    for alias in names:
        word = required_text(alias["name"], "crop name")
        run(conn, "INSERT INTO ag_crop_name VALUES (?,?,?,?,?,?) ON CONFLICT DO NOTHING",
            (pack,key,required_text(alias["language"], "language"),word,search_key(word),alias.get("source_id")))
        put_tokens(conn, pack, key, word)


def put_trait(conn, item, pack, version, retrieved):
    crop_id = item["crop_id"]
    # Block a global release from introducing a crop without a catalogue record of its own.
    if not run(conn, "SELECT 1 FROM ag_crop_record WHERE pack_id=? AND crop_id=?", (pack,crop_id)).fetchone():
        raise ValueError(f"Unknown crop in {pack}: {crop_id}")
    src = run(conn, "SELECT * FROM ag_source WHERE id=?", (item["source_id"],)).fetchone()
    if not src:
        raise ValueError("Unknown scientific source.")
    scope = required_text(item["region_id"], "geographic scope")
    if pack == "global" and scope != "global":
        raise ValueError("Global seed traits require explicit global scope.")
    if item.get("cultivar"):
        cultivar_id = f"{crop_id}:{item['cultivar']}"
        run(conn, "INSERT INTO ag_cultivar VALUES (?,?,?) ON CONFLICT DO NOTHING", (cultivar_id,crop_id,item["cultivar"]))
    else:
        cultivar_id = None
    lo, hi = item.get("min"), item.get("max")
    text_value = item.get("value_text")
    if text_value is None:
        if any(type(n) not in (float,int) or not math.isfinite(n) for n in (lo,hi)) or lo > hi:
            raise ValueError("A numerical trait requires finite ordered endpoints.")
        required_text(item.get("unit"), "original trait unit")
    trait = required_text(item["trait"], "trait name")
    evidence = required_text(item["evidence_type"], "evidence type")
    review = item["review_status"]
    record = (pack,crop_id,trait,lo,hi,text_value,item.get("unit"),scope,cultivar_id,item.get("system"),
              src["id"],item.get("version") or src["source_version"] or version,
              iso_date(item.get("retrieved_on") or retrieved),evidence,review,item.get("note"),
              source_url(item.get("source_url") or src["url"]))
    identity = digest(json.dumps(record, ensure_ascii=False).encode())
    run(conn,"INSERT INTO ag_evidence VALUES (" + ",".join("?" for _ in range(18)) + ") ON CONFLICT DO NOTHING", (identity,*record))
    if cultivar_id is not None:
        run(
            conn,
            "INSERT INTO ag_cultivar_trait VALUES (" + ",".join("?" for _ in range(16)) + ") ON CONFLICT DO NOTHING",
            (
                identity,
                pack,
                cultivar_id,
                crop_id,
                trait,
                lo,
                hi,
                text_value,
                item.get("unit"),
                scope,
                src["id"],
                item.get("version") or src["source_version"] or version,
                iso_date(item.get("retrieved_on") or retrieved),
                review,
                item.get("note"),
                source_url(item.get("source_url") or src["url"]),
            ),
        )


def put_growth_stage(conn, item, pack, version, retrieved):
    crop_id = required_text(item["crop_id"], "crop ID")
    if not run(conn, "SELECT 1 FROM ag_crop_record WHERE pack_id=? AND crop_id=?", (pack, crop_id)).fetchone():
        raise ValueError(f"Unknown crop in {pack}: {crop_id}")
    src = run(conn, "SELECT * FROM ag_source WHERE id=?", (item["source_id"],)).fetchone()
    if not src:
        raise ValueError("Unknown scientific source for growth stage.")
    stage_code = required_text(item["stage_code"], "stage code")
    stage_order = int(item["stage_order"])
    df_min = float(item["duration_fraction_min"])
    df_max = float(item["duration_fraction_max"])
    kc_min = float(item["kc_min"])
    kc_max = float(item["kc_max"])
    p_val = float(item["depletion_fraction_p"]) if item.get("depletion_fraction_p") is not None else None
    t_min = float(item["critical_tmin_c"]) if item.get("critical_tmin_c") is not None else None
    t_max = float(item["critical_tmax_c"]) if item.get("critical_tmax_c") is not None else None
    ky_val = float(item["ky_yield_response"]) if item.get("ky_yield_response") is not None else None
    wl_sens = 1 if item.get("waterlogging_sensitive") else 0
    review = required_text(item.get("review_status", "reviewed"), "review status")
    s_url = source_url(item.get("source_url") or src["url"])
    s_ver = item.get("version") or src["source_version"] or version
    ret_on = iso_date(item.get("retrieved_on") or retrieved)
    record = (
        pack,
        crop_id,
        stage_code,
        stage_order,
        df_min,
        df_max,
        kc_min,
        kc_max,
        p_val,
        t_min,
        t_max,
        ky_val,
        wl_sens,
        src["id"],
        s_ver,
        ret_on,
        review,
        item.get("note"),
        s_url,
    )
    identity = digest(json.dumps(record, ensure_ascii=False).encode())
    run(
        conn,
        "INSERT INTO ag_growth_stage VALUES (" + ",".join("?" for _ in range(20)) + ") ON CONFLICT DO NOTHING",
        (identity, *record),
    )


def put_pest_context(conn, item, pack, version, retrieved):
    crop_id = required_text(item["crop_id"], "crop ID")
    if not run(conn, "SELECT 1 FROM ag_crop_record WHERE pack_id=? AND crop_id=?", (pack, crop_id)).fetchone():
        raise ValueError(f"Unknown crop in {pack}: {crop_id}")
    src = run(conn, "SELECT * FROM ag_source WHERE id=?", (item["source_id"],)).fetchone()
    if not src:
        raise ValueError("Unknown scientific source for pest context.")
    scope = required_text(item.get("region_id", "global"), "region ID")
    record = (
        pack,
        crop_id,
        required_text(item["agent_name"], "pest/disease agent name"),
        item.get("scientific_name"),
        required_text(item["category"], "pest category"),
        required_text(item["favorable_condition"], "favorable condition"),
        required_text(item["susceptible_stage"], "susceptible stage"),
        required_text(item["cultural_notes"], "cultural notes"),
        scope,
        src["id"],
        item.get("version") or src["source_version"] or version,
        iso_date(item.get("retrieved_on") or retrieved),
        required_text(item.get("review_status", "reviewed"), "review status"),
        source_url(item.get("source_url") or src["url"]),
    )
    identity = digest(json.dumps(record, ensure_ascii=False).encode())
    run(
        conn,
        "INSERT INTO ag_pest_context VALUES (" + ",".join("?" for _ in range(15)) + ") ON CONFLICT DO NOTHING",
        (identity, *record),
    )


def put_soil_observation(conn, item, pack, retrieved):
    src = run(conn, "SELECT * FROM ag_source WHERE id=?", (item["source_id"],)).fetchone()
    if not src:
        raise ValueError("Unknown scientific source for soil observation.")
    record = (
        pack,
        src["id"],
        required_text(item["dataset_code"], "dataset code"),
        required_text(item["profile_code"], "profile code"),
        item.get("country_code"),
        float(item["latitude"]),
        float(item["longitude"]),
        float(item["upper_depth_cm"]),
        float(item["lower_depth_cm"]),
        required_text(item["property"], "soil property"),
        float(item["raw_value"]) if item.get("raw_value") is not None else None,
        item.get("raw_unit"),
        float(item["normalized_value"]) if item.get("normalized_value") is not None else None,
        required_text(item["normalized_unit"], "normalized unit"),
        float(item["uncertainty_low"]) if item.get("uncertainty_low") is not None else None,
        float(item["uncertainty_high"]) if item.get("uncertainty_high") is not None else None,
        required_text(item["observation_kind"], "observation kind"),
        iso_date(item.get("observed_date")),
        iso_date(item.get("retrieved_on") or retrieved),
    )
    identity = digest(json.dumps(record, ensure_ascii=False).encode())
    run(
        conn,
        "INSERT INTO ag_soil_observation VALUES (" + ",".join("?" for _ in range(20)) + ") ON CONFLICT DO NOTHING",
        (identity, *record),
    )


def put_validation_observation(conn, item, pack, retrieved):
    crop_id = required_text(item["crop_id"], "crop ID")
    src = run(conn, "SELECT * FROM ag_source WHERE id=?", (item["source_id"],)).fetchone()
    if not src:
        raise ValueError("Unknown scientific source for validation observation.")
    record = (
        pack,
        required_text(item["station_key"], "station key"),
        required_text(item["country_code"], "country code"),
        crop_id,
        required_text(item["water_regime"], "water regime"),
        required_text(item["reference_type"], "reference type"),
        float(item["reference_value"]) if item.get("reference_value") is not None else None,
        required_text(item["reference_code"], "reference code"),
        src["id"],
        iso_date(item.get("retrieved_on") or retrieved),
        item.get("note"),
    )
    identity = digest(json.dumps(record, ensure_ascii=False).encode())
    run(
        conn,
        "INSERT INTO ag_validation_observation VALUES (" + ",".join("?" for _ in range(12)) + ") ON CONFLICT DO NOTHING",
        (identity, *record),
    )


def put_refresh_policy(conn, item, pack, retrieved):
    src = run(conn, "SELECT * FROM ag_source WHERE id=?", (item["source_id"],)).fetchone()
    if not src:
        raise ValueError("Unknown scientific source for refresh policy.")
    run(
        conn,
        "INSERT INTO ag_refresh_policy VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(dataset_id) DO UPDATE SET "
        "refresh_cadence_days=excluded.refresh_cadence_days,fallback_policy=excluded.fallback_policy,updated_on=excluded.updated_on",
        (
            required_text(item["dataset_id"], "dataset ID"),
            pack,
            required_text(item["provider_name"], "provider name"),
            int(item["refresh_cadence_days"]),
            required_text(item["expected_format"], "expected format"),
            item.get("expected_crs"),
            item.get("expected_dimensions"),
            1 if item.get("require_sha256", True) else 0,
            1 if item.get("allow_live_farmer_path", False) else 0,
            required_text(item["fallback_policy"], "fallback policy"),
            src["id"],
            iso_date(item.get("updated_on") or retrieved),
        ),
    )


def clear_crop_pack(conn, pack):
    for table in (
        "ag_cultivar_trait",
        "ag_growth_stage",
        "ag_pest_context",
        "ag_soil_observation",
        "ag_validation_observation",
        "ag_refresh_policy",
        "ag_regional_crop",
        "ag_evidence",
        "ag_name_token",
        "ag_crop_name",
        "ag_crop_record",
    ):
        run(conn, f"DELETE FROM {table} WHERE pack_id=?", (pack,))


def global_pack(conn, doc):
    if not doc.get("crops"):
        raise ValueError("An empty catalogue cannot replace the active release.")
    iso_date(doc["retrieved_on"])
    for source in doc["sources"]:
        put_source(conn, source)
    for crop in doc["crops"]:
        put_crop(conn,crop,"global")
        if crop.get("family_source_id"):
            put_trait(conn,{
                "crop_id":crop["id"], "trait":"family", "value_text":required_text(crop["family"],"family"),
                "region_id":"global", "source_id":crop["family_source_id"], "source_url":crop["family_reference"],
                "evidence_type":"taxonomic classification", "review_status":"reviewed",
            },"global",doc["version"],doc["retrieved_on"])
    for trait in doc["traits"]:
        put_trait(conn,trait,"global",doc["version"],doc["retrieved_on"])
    for stage in doc.get("growth_stages", []):
        put_growth_stage(conn, stage, "global", doc["version"], doc["retrieved_on"])
    for pest in doc.get("pest_context", []):
        put_pest_context(conn, pest, "global", doc["version"], doc["retrieved_on"])
    for soil_obs in doc.get("soil_observations", []):
        put_soil_observation(conn, soil_obs, "global", doc["retrieved_on"])
    for val_obs in doc.get("validation_observations", []):
        put_validation_observation(conn, val_obs, "global", doc["retrieved_on"])
    for policy in doc.get("refresh_policies", []):
        put_refresh_policy(conn, policy, "global", doc["retrieved_on"])


def regional_pack(conn, doc):
    run(conn,"INSERT INTO ag_region VALUES (?,?,?) ON CONFLICT DO NOTHING",(REGION,doc["region"],"LK"))
    for key, source in doc["sources"].items():
        put_source(conn, dict(source, id=key))
    for key,crop in doc["crops"].items():
        put_crop(conn, dict(crop,id=key),"lk")
        run(conn,"INSERT INTO ag_regional_crop VALUES (?,?,?)",("lk",key,REGION))
        for name, evidence in crop["trait_evidence"].items():
            value = crop[name]
            if value is None:
                continue
            if not evidence["source"]:
                raise ValueError("Regional value lacks a source.")
            item = dict(crop_id=key,trait=name,unit=UNITS.get(name),region_id=REGION,source_id=evidence["source"],
                        evidence_type=evidence["status"],review_status="reviewed")
            if name == "duration_days":
                item["note"] = crop.get("duration_note")
                if key == "mung_bean":
                    item["cultivar"] = "MI 6"
            if isinstance(value,list):
                item["min"],item["max"] = value
            else:
                item["value_text"] = str(value).lower() if isinstance(value,bool) else value
            # The audited legacy pack records its revision, but no separate retrieval date.
            put_trait(conn,item,"lk",doc["version"],None)


def station_pack(conn, raw):
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if not rows:
        raise ValueError("No station records.")
    conn.execute("DELETE FROM ag_nasa_cache")
    for row in rows:
        if not re.fullmatch("[a-f0-9]{64}", row["sha256"]) or row["data_kind"] != "VERIFIED_CACHE":
            raise ValueError("Invalid NASA archive metadata.")
        lat, lon = float(row["latitude"]), float(row["longitude"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Invalid station coordinates.")
        run(conn, "INSERT INTO ag_nasa_cache VALUES (?,?,?,?,?,?,?,?,?)",
            (row["hub_key"],lat,lon,row["start"],row["end"],row["evidence"],row["sha256"],row["retrieved_at_utc"],row["data_kind"]))


def log_run(conn, pack, version, checksum, status, detail):
    run(conn, "INSERT INTO ag_import_history VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()),pack,version,checksum,datetime.now(timezone.utc).isoformat(),status,detail))


def provider_pack(conn, raw):
    records = json.loads(raw)
    if not isinstance(records,list) or not records:
        raise ValueError("A provider registry must contain at least one dated status.")
    conn.execute("DELETE FROM ag_provider_status")
    for row in records:
        run(conn, "INSERT INTO ag_provider_status VALUES (?,?,?,?)",
            (required_text(row["id"],"provider ID"),iso_date(required_text(row["checked"],"check date")),
             required_text(row["status"],"status"),required_text(row["detail"],"probe result")))


def import_file(conn, pack, path):
    if pack not in {"lk","global","nasa_manifest","providers"}:
        raise ValueError("Unsupported pack.")
    raw = Path(path).read_bytes()
    checksum = digest(raw.replace(b"\r\n", b"\n"))
    version = None
    try:
        with transaction(conn, lock=True):
            current = run(conn,"SELECT digest FROM ag_pack WHERE id=?",(pack,)).fetchone()
            if current and current["digest"] == checksum:
                return "unchanged"
            manifest = pack in {"nasa_manifest","providers"}
            doc = {} if manifest else json.loads(raw)
            version = checksum[:16] if manifest else required_text(doc["version"], "version")
            known = run(conn,"SELECT digest FROM ag_import_history WHERE pack_id=? AND version=? AND status='imported'",(pack,version)).fetchone()
            if known and known["digest"] != checksum:
                raise ValueError("The released version changed content. Supply a new version.")
            run(conn,"INSERT INTO ag_pack VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET version=excluded.version,digest=excluded.digest",(pack,version,checksum))
            run(conn,"INSERT INTO ag_region VALUES ('global','Worldwide',NULL) ON CONFLICT DO NOTHING")
            if manifest:
                (station_pack if pack == "nasa_manifest" else provider_pack)(conn,raw)
            else:
                clear_crop_pack(conn,pack)
                (global_pack if pack == "global" else regional_pack)(conn,doc)
            conflicts = conn.execute("SELECT count(*) AS n FROM ag_conflicts").fetchone()["n"]
            log_run(conn,pack,version,checksum,"imported",f"{conflicts} conflicting evidence rows pending review")
        return "imported"
    except Exception as exc:
        # No failed release is visible. Log only the failure class, never connection credentials.
        with transaction(conn):
            log_run(conn,pack,version,checksum,"failed",type(exc).__name__)
        raise


def release_files(data_dir=ROOT / "data"):
    files = (("lk", data_dir/"crops.json"), ("global", data_dir/"global_catalogue.json"),
            ("nasa_manifest", data_dir/"global_nasa_stations_summary.csv"))
    registry = data_dir / "provider_registry.json"
    return files + ((("providers", registry),) if registry.is_file() else ())


def seed_database(conn, data_dir=ROOT / "data"):
    return {pack: import_file(conn, pack, path) for pack,path in release_files(data_dir)}
