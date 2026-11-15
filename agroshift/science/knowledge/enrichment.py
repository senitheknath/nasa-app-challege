"""On-demand full database enrichment from FAO EcoCrop, FAO Crop Calendar API, and FAOSTAT/GAEZ."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from agroshift.science.knowledge.knowledge_store import ROOT, migrate, run, seed_database, transaction

ECOCROP_CSV_URL = "https://raw.githubusercontent.com/OpenCLIM/ecocrop/main/EcoCrop_DB.csv"
ECOCROP_SOURCE_URL = "https://data.apps.fao.org/catalog/dataset/ecocrop"
FAO_CALENDAR_BASE = "https://api-cropcalendar.apps.fao.org/api/v1"


def _norm_sci_name(name: str | None) -> str:
    """Normalize scientific name to lowercase 'genus species' (stripping authority/subspecies)."""
    if not name:
        return ""
    tokens = re.findall(r"[a-zA-Z]+", name.lower())
    return " ".join(tokens[:2]) if len(tokens) >= 2 else (tokens[0] if tokens else "")


def _parse_float(val: Any) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _fmt_mmdd(obj: Any) -> str | None:
    if not isinstance(obj, dict):
        return None
    m, d = obj.get("month"), obj.get("day")
    if isinstance(m, int) and isinstance(d, int) and 1 <= m <= 12 and 1 <= d <= 31:
        return f"{m:02d}-{d:02d}"
    return None


def fetch_ecocrop_index(
    *,
    allow_network: bool = True,
    cache_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Load FAO EcoCrop traits keyed by normalized scientific name ('genus species')."""
    target = cache_path or (ROOT / "data" / "provider_samples" / "EcoCrop_DB.csv")
    if allow_network:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(ECOCROP_CSV_URL, headers={"User-Agent": "AgroShift/1.0"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                target.write_bytes(resp.read())
        except Exception:
            if not target.exists():
                return {}

    if not target.exists():
        return {}

    index: dict[str, dict[str, Any]] = {}
    with target.open(encoding="latin-1", newline="") as f:
        for row in csv.DictReader(f):
            sci = _norm_sci_name(row.get("ScientificName"))
            if not sci or sci in index:
                continue
            index[sci] = row
    return index


def fetch_fao_calendar_records(
    countries: tuple[str, ...] = ("LK", "KE"),
    *,
    allow_network: bool = True,
    cache_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Fetch crop calendar records from the live FAO Crop Calendar API (with local JSON cache fallback)."""
    c_dir = cache_dir or (ROOT / "data" / "provider_samples")
    c_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    for cc in countries:
        cc_up = cc.strip().upper()
        crops_cache = c_dir / f"fao_cal_crops_{cc_up}.json"
        cal_cache = c_dir / f"fao_cal_windows_{cc_up}.json"

        if allow_network:
            for url, path in (
                (f"{FAO_CALENDAR_BASE}/countries/{cc_up}/crops", crops_cache),
                (f"{FAO_CALENDAR_BASE}/cropCalendar?countries={cc_up}", cal_cache),
            ):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "AgroShift/1.0"})
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        path.write_bytes(resp.read())
                except Exception:
                    pass

        if not crops_cache.exists() or not cal_cache.exists():
            continue

        try:
            crop_meta = json.loads(crops_cache.read_text(encoding="utf-8"))
            cal_list = json.loads(cal_cache.read_text(encoding="utf-8"))
        except Exception:
            continue

        by_fao_crop_id = {
            str(item.get("crop_id")): item for item in crop_meta if isinstance(item, dict) and item.get("crop_id")
        }
        for entry in cal_list:
            if not isinstance(entry, dict):
                continue
            crop_obj = entry.get("crop") or {}
            fao_cid = str(crop_obj.get("id") or "")
            meta = by_fao_crop_id.get(fao_cid, {})
            aez_name = (entry.get("aez") or {}).get("name") or "national"
            for sess in entry.get("sessions") or []:
                if not isinstance(sess, dict):
                    continue
                p_start = _fmt_mmdd(sess.get("early_sowing"))
                p_end = _fmt_mmdd(sess.get("later_sowing"))
                h_start = _fmt_mmdd(sess.get("early_harvest"))
                h_end = _fmt_mmdd(sess.get("late_harvest"))
                if not (p_start or h_start):
                    continue
                records.append(
                    {
                        "country": cc_up,
                        "aez": aez_name,
                        "season": sess.get("additional_information") or "",
                        "fao_crop_id": fao_cid,
                        "scientific_name": meta.get("crop_scientific_name") or "",
                        "other_name": meta.get("other_name") or crop_obj.get("name") or "",
                        "planting_start": p_start,
                        "planting_end": p_end,
                        "harvest_start": h_start,
                        "harvest_end": h_end,
                    }
                )
    return records


def _ensure_sources_and_regions(conn: sqlite3.Connection, today: str, countries: tuple[str, ...]) -> None:
    sources = [
        (
            "fao_ecocrop",
            "FAO EcoCrop Crop Ecological Requirements Database",
            ECOCROP_SOURCE_URL,
            "CC BY 4.0",
            "2007-openclim",
        ),
        (
            "fao_crop_calendar_api",
            "FAO Crop Calendar Information System API",
            "https://api-cropcalendar.apps.fao.org/",
            "FAO Open Access",
            today,
        ),
        (
            "faostat_qcl",
            "FAOSTAT Crops and Livestock Products (QCL)",
            "https://www.fao.org/faostat/en/#data/QCL",
            "CC BY 4.0",
            "2026",
        ),
    ]
    for src in sources:
        run(
            conn,
            "INSERT INTO ag_source VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "title=excluded.title, license=COALESCE(excluded.license, ag_source.license), "
            "source_version=COALESCE(excluded.source_version, ag_source.source_version)",
            src,
        )
    run(conn, "INSERT INTO ag_region VALUES (?,?,?) ON CONFLICT DO NOTHING", ("global", "Global", None))
    for cc in countries:
        cc_up = cc.strip().upper()
        run(conn, "INSERT INTO ag_region VALUES (?,?,?) ON CONFLICT DO NOTHING", (cc_up.lower(), cc_up, cc_up))


ECOCROP_SYNONYMS: dict[str, str] = {
    "yam": "dioscorea alata",
    "almond": "prunus amygdalus",
    "plantain": "musa acuminata",
    "triticale": "triticum aestivum",
}


def _insert_ecocrop_traits(
    conn: sqlite3.Connection,
    eco_index: dict[str, dict[str, Any]],
    today: str,
) -> int:
    if not eco_index:
        return 0

    existing = {
        (r["crop_id"], r["trait"])
        for r in run(conn, "SELECT crop_id, trait FROM ag_evidence WHERE review_status='reviewed'").fetchall()
    }
    crops = run(
        conn,
        "SELECT DISTINCT crop_id, scientific_name FROM ag_crop_record WHERE scientific_name IS NOT NULL",
    ).fetchall()

    inserted = 0
    for c_row in crops:
        cid = c_row["crop_id"]
        sci = _norm_sci_name(c_row["scientific_name"])
        eco = eco_index.get(sci) or eco_index.get(ECOCROP_SYNONYMS.get(cid, ""))
        if not eco:
            continue

        candidates: list[tuple[str, float | None, float | None, str, str]] = [
            (
                "preferred_daily_mean_air_temperature",
                _parse_float(eco.get("TOPMN")),
                _parse_float(eco.get("TOPMX")),
                "degC",
                "FAO EcoCrop optimal temperature range (TOPMN-TOPMX).",
            ),
            (
                "preferred_soil_ph",
                _parse_float(eco.get("PHOPMN")),
                _parse_float(eco.get("PHOPMX")),
                "pH",
                "FAO EcoCrop optimal soil pH range (PHOPMN-PHOPMX).",
            ),
            (
                "indicative_cycle_duration",
                _parse_float(eco.get("GMIN")),
                _parse_float(eco.get("GMAX")),
                "days",
                "FAO EcoCrop crop cycle duration (GMIN-GMAX).",
            ),
        ]

        dra = (eco.get("DRA") or "").lower()
        if "well" in dra and "poor" not in dra:
            candidates.append(
                ("persistent_waterlogging_conflict", 1.0, 1.0, "boolean", f"FAO EcoCrop drainage={eco.get('DRA')}.")
            )
        elif "poor" in dra or "water" in dra:
            candidates.append(
                ("persistent_waterlogging_conflict", 0.0, 0.0, "boolean", f"FAO EcoCrop drainage={eco.get('DRA')}.")
            )

        for trait, lo, hi, units, note in candidates:
            if (cid, trait) in existing or lo is None or hi is None or lo > hi:
                continue
            eid = hashlib.sha256(f"ecocrop|{cid}|{trait}".encode()).hexdigest()[:24]
            run(
                conn,
                "INSERT INTO ag_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                (
                    eid,
                    "global",
                    cid,
                    trait,
                    lo,
                    hi,
                    None,
                    units,
                    "global",
                    None,
                    None,
                    "fao_ecocrop",
                    "2007-openclim",
                    today,
                    "ecocrop_database",
                    "reviewed",
                    note,
                    ECOCROP_SOURCE_URL,
                ),
            )
            existing.add((cid, trait))
            inserted += 1
    return inserted


def _insert_calendar_records(
    conn: sqlite3.Connection,
    cal_records: list[dict[str, Any]],
    today: str,
) -> int:
    if not cal_records:
        return 0

    crops = run(conn, "SELECT crop_id, name, scientific_name FROM ag_crop_record").fetchall()
    by_sci = {_norm_sci_name(r["scientific_name"]): r["crop_id"] for r in crops if r["scientific_name"]}
    by_name = {r["name"].strip().lower(): r["crop_id"] for r in crops if r["name"]}

    inserted = 0
    for rec in cal_records:
        cid = by_sci.get(_norm_sci_name(rec.get("scientific_name"))) or by_name.get(
            (rec.get("other_name") or "").strip().lower()
        )
        if not cid:
            continue

        reg_id = rec["country"].lower()
        sys_label = f"{rec['aez']} ({rec['season']})".strip(" ()")
        eid = hashlib.sha256(f"cal_ev|{cid}|{reg_id}|{sys_label}".encode()).hexdigest()[:24]
        run(
            conn,
            "INSERT INTO ag_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
            (
                eid,
                "global",
                cid,
                "growing_calendar_window",
                None,
                None,
                f"Plant {rec['planting_start']}..{rec['planting_end']} / Harvest {rec['harvest_start']}..{rec['harvest_end']}",
                None,
                reg_id,
                None,
                sys_label[:64],
                "fao_crop_calendar_api",
                today,
                today,
                "crop_calendar_api",
                "reviewed",
                f"FAO Crop Calendar AEZ: {rec['aez']}",
                "https://api-cropcalendar.apps.fao.org/",
            ),
        )
        cal_id = hashlib.sha256(
            f"cal|{cid}|{reg_id}|{sys_label}|{rec['planting_start']}|{rec['harvest_start']}".encode()
        ).hexdigest()[:24]
        run(
            conn,
            "INSERT INTO ag_growing_calendar VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
            (
                cal_id,
                cid,
                reg_id,
                None,
                sys_label[:64],
                rec["planting_start"],
                rec["planting_end"],
                rec["harvest_start"],
                rec["harvest_end"],
                eid,
            ),
        )
        inserted += 1
    return inserted


def _import_faostat_validation(conn: sqlite3.Connection, data_dir: Path, today: str) -> int:
    fpath = data_dir / "faostat_qcl_sample.json"
    if not fpath.exists():
        return 0
    try:
        payload = json.loads(fpath.read_text(encoding="utf-8"))
    except Exception:
        return 0
    rows = (payload.get("rows") or payload.get("records") or []) if isinstance(payload, dict) else (payload if isinstance(payload, list) else [])
    crop_rows = run(conn, "SELECT crop_id, name FROM ag_crop_record").fetchall()
    crop_ids = {r["crop_id"] for r in crop_rows}
    by_name = {r["name"].strip().lower(): r["crop_id"] for r in crop_rows if r["name"]}

    inserted = 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        raw_cid = str(item.get("crop_id") or "").strip()
        raw_crop = str(item.get("crop") or "").strip().lower()
        cid = raw_cid if raw_cid in crop_ids else by_name.get(raw_crop)
        if not cid:
            for nm, mapped_id in by_name.items():
                if nm in raw_crop or raw_crop in nm:
                    cid = mapped_id
                    break
        if not cid:
            continue
        cc = str(item.get("country_code") or item.get("country") or "GLB").upper()
        val = _parse_float(item.get("tonnes") or item.get("value") or item.get("production_tonnes"))
        vid = hashlib.sha256(f"faostat|{cc}|{cid}|{item.get('year')}".encode()).hexdigest()[:24]
        run(
            conn,
            "INSERT INTO ag_validation_observation VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
            (
                vid,
                "global",
                f"{cc}_national",
                cc,
                cid,
                "rainfed",
                "faostat_national_production",
                val,
                str(item.get("year") or "2022"),
                "faostat_qcl",
                today,
                str(item.get("crop") or item.get("item") or "FAOSTAT QCL national production"),
            ),
        )
        inserted += 1
    return inserted


def _import_gaez_validation(conn: sqlite3.Connection, data_dir: Path, today: str) -> int:
    mpath = data_dir / "gaez" / "manifest.json"
    if not mpath.exists():
        return 0
    try:
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
    except Exception:
        return 0

    run(
        conn,
        "INSERT INTO ag_source VALUES (?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
        (
            "fao_gaez_v5",
            "FAO / IIASA Global Agro-Ecological Zones (GAEZ v5)",
            "https://data.apps.fao.org/catalog/dataset/514c92d5-9e01-4c70-814a-80ea1ca9fe6a",
            "CC BY 4.0",
            "v5-2026",
        ),
    )
    crop_rows = run(conn, "SELECT crop_id, name FROM ag_crop_record").fetchall()
    crop_ids = {r["crop_id"] for r in crop_rows}
    by_name = {r["name"].strip().lower(): r["crop_id"] for r in crop_rows if r["name"]}
    gaez_aliases = {
        "wetland rice": "rice",
        "dryland rice": "rice",
        "white potato": "potato",
        "gram": "chickpea",
        "phaseolus bean": "bean",
        "pearl millet": "millet",
        "sugar cane": "sugarcane",
        "banana": "banana",
    }

    inserted = 0
    for fname, meta in manifest.items():
        if not isinstance(meta, dict):
            continue
        cname = str(meta.get("crop") or "").strip().lower()
        cid = gaez_aliases.get(cname) or by_name.get(cname)
        if not cid:
            for nm, mapped in by_name.items():
                if cname in nm or nm in cname:
                    cid = mapped
                    break
        if not cid or cid not in crop_ids:
            continue
        water = "irrigated" if meta.get("water") == "irrigated" else "rainfed"
        vid = hashlib.sha256(f"gaez|{fname}".encode()).hexdigest()[:24]
        run(
            conn,
            "INSERT INTO ag_validation_observation VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
            (
                vid,
                "global",
                "GAEZ_GLOBAL",
                "GLB",
                cid,
                water,
                "gaez_v5_suitability",
                1.0,
                fname.split(".")[4] if len(fname.split(".")) > 4 else "GAEZ",
                "fao_gaez_v5",
                today,
                f"GAEZ v5 suitability raster ({meta.get('crop')}, {water})",
            ),
        )
        inserted += 1
    return inserted


def update_full_database(
    db_path: Path | None = None,
    *,
    data_dir: Path | None = None,
    allow_network: bool = True,
    countries: tuple[str, ...] = ("LK", "KE"),
) -> dict[str, Any]:
    """Seed base packs and enrich the SQLite knowledge database from live EcoCrop, FAO Crop Calendar, FAOSTAT, and GAEZ."""
    target_db = db_path or (ROOT / "data" / "knowledge.sqlite")
    d_dir = data_dir or (ROOT / "data")
    today = date.today().isoformat()

    eco_index = fetch_ecocrop_index(allow_network=allow_network)
    cal_records = fetch_fao_calendar_records(countries=countries, allow_network=allow_network)

    conn = sqlite3.connect(str(target_db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        migrate(conn)
        seed_database(conn, d_dir)

        before_tiers = {
            r["support_level"]: r["n"]
            for r in run(conn, "SELECT support_level, COUNT(*) AS n FROM ag_catalogue GROUP BY support_level").fetchall()
        }

        with transaction(conn):
            _ensure_sources_and_regions(conn, today, countries)
            eco_added = _insert_ecocrop_traits(conn, eco_index, today)
            cal_added = _insert_calendar_records(conn, cal_records, today)
            val_added = _import_faostat_validation(conn, d_dir, today) + _import_gaez_validation(conn, d_dir, today)
            run(
                conn,
                "INSERT INTO ag_import_history VALUES (?,?,?,?,?,?,?)",
                (
                    hashlib.sha256(f"enrich|{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:24],
                    "global",
                    today,
                    hashlib.sha256(f"{eco_added}|{cal_added}|{val_added}".encode()).hexdigest(),
                    datetime.now(timezone.utc).isoformat(),
                    "imported",
                    f"ecocrop={eco_added}, calendar={cal_added}, validation={val_added}",
                ),
            )

        after_tiers = {
            r["support_level"]: r["n"]
            for r in run(conn, "SELECT support_level, COUNT(*) AS n FROM ag_catalogue GROUP BY support_level").fetchall()
        }
        return {
            "db_path": str(target_db),
            "allow_network": allow_network,
            "ecocrop_species_loaded": len(eco_index),
            "ecocrop_traits_added": eco_added,
            "calendar_rows_added": cal_added,
            "validation_rows_added": val_added,
            "tiers_before": before_tiers,
            "tiers_after": after_tiers,
        }
    finally:
        conn.close()
