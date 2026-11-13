"""Reproducible agricultural validation, geographic/temporal holdouts, missing-data stress tests, and 5-variant ablation study."""
from __future__ import annotations

import csv
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from agroshift.science.climate.climate import Window
from agroshift.science.decision.decision import Farm
from agroshift.science.decision.evidence_combination import build_evidence_layers
from agroshift.science.climate.power import archived_history, request_parameters
from agroshift.earth_data.providers import GAEZ_CROP_ID_MAP, gaez_point, match_crop_calendar, soil_context
from agroshift.science.decision.screening import find_options

_curr = Path(__file__).resolve()
while _curr != _curr.parent:
    if (_curr / "data").is_dir() and (_curr / "agroshift").is_dir():
        ROOT = _curr
        break
    _curr = _curr.parent
else:
    ROOT = Path(__file__).resolve().parents[2]


def load_station_manifest() -> list[dict]:
    path = ROOT / "data" / "global_nasa_stations_summary.csv"
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def evaluate_temporal_holdout(station_limit: int | None = None) -> dict:
    """Compare screening classifications between 2001-2015 (early period) and 2016-2025 (recent holdout) across verified stations."""
    rows = load_station_manifest()
    if station_limit is not None:
        rows = rows[:station_limit]

    station_results = []
    total_comparisons = 0
    exact_status_matches = 0
    temp_deltas = []

    for row in rows:
        lat, lon = float(row["latitude"]), float(row["longitude"])
        country = row["country"]
        ds = archived_history(request_parameters(lat, lon, date(2001, 1, 1), date(2025, 12, 31)))
        if ds is None:
            continue

        early_frame = ds.frame.loc["2001-01-01":"2015-12-31"].copy()
        early_frame.attrs.update(ds.frame.attrs)
        recent_frame = ds.frame.loc["2016-01-01":"2025-12-31"].copy()
        recent_frame.attrs.update(ds.frame.attrs)

        early_ds = replace(ds, frame=early_frame)
        recent_ds = replace(ds, frame=recent_frame)

        window = Window(5, 1, 9, 30) if lat >= 0 else Window(11, 1, 3, 31)
        farm = Farm(country=country, latitude=lat, longitude=lon, windows=(window,), ph=6.2, drainage="well_drained")

        cards_early = {c["id"]: c for c in find_options(farm, early_ds)}
        cards_recent = {c["id"]: c for c in find_options(farm, recent_ds)}

        common_ids = sorted(set(cards_early) & set(cards_recent))
        matches = sum(1 for cid in common_ids if cards_early[cid]["status"] == cards_recent[cid]["status"])
        total_comparisons += len(common_ids)
        exact_status_matches += matches

        dt = float(recent_frame["T2M"].mean() - early_frame["T2M"].mean())
        temp_deltas.append(dt)
        station_results.append(
            {
                "hub_key": row["hub_key"],
                "country": country,
                "crops_compared": len(common_ids),
                "status_agreement_rate": round(matches / max(len(common_ids), 1), 3),
                "warming_delta_c_2016_2025_vs_2001_2015": round(dt, 3),
            }
        )

    return {
        "stations_evaluated": len(station_results),
        "total_crop_station_pairs": total_comparisons,
        "overall_temporal_status_agreement_rate": round(exact_status_matches / max(total_comparisons, 1), 4),
        "mean_warming_delta_c": round(float(np.mean(temp_deltas)), 3) if temp_deltas else None,
        "station_breakdown": station_results,
    }


def evaluate_missing_data_stress(hub_key: str = "nairobi_kenya") -> dict:
    """Verify conservative behaviour under missing farmer inputs and degraded weather coverage."""
    rows = load_station_manifest()
    row = next((r for r in rows if r["hub_key"] == hub_key), rows[0])
    lat, lon = float(row["latitude"]), float(row["longitude"])
    ds = archived_history(request_parameters(lat, lon, date(2001, 1, 1), date(2025, 12, 31)))

    full_farm = Farm(
        country=row["country"],
        latitude=lat,
        longitude=lon,
        windows=(Window(3, 1, 7, 31),),
        ph=6.2,
        drainage="well_drained",
        irrigation="reliable",
        irrigation_mm=250.0,
        rain_fraction=0.7,
    )
    minimal_farm = Farm(
        country=row["country"],
        latitude=lat,
        longitude=lon,
        windows=(Window(3, 1, 7, 31),),
        ph=None,
        drainage="unknown",
        irrigation="rainfed",
        irrigation_mm=0.0,
        rain_fraction=None,
    )

    full_cards = {c["id"]: c for c in find_options(full_farm, ds)}
    min_cards = {c["id"]: c for c in find_options(minimal_farm, ds)}

    # Degrade weather coverage so fewer than 10 seasons have full daily T2M
    degraded_frame = ds.frame.copy()
    for yr in range(2005, 2026):
        degraded_frame.loc[f"{yr}-05-15", "T2M"] = np.nan
    degraded_ds = replace(ds, frame=degraded_frame)
    deg_cards = {c["id"]: c for c in find_options(minimal_farm, degraded_ds)}

    false_promotions = [
        cid
        for cid in full_cards
        if full_cards[cid]["status"] in {"outside", "blocked"} and min_cards[cid]["status"] == "possible"
    ]
    degraded_possible = [cid for cid, c in deg_cards.items() if c["status"] == "possible"]

    return {
        "station": row["hub_key"],
        "full_input_possible_count": sum(1 for c in full_cards.values() if c["status"] == "possible"),
        "minimal_input_unknown_count": sum(1 for c in min_cards.values() if c["status"] == "unknown"),
        "degraded_weather_unknown_count": sum(1 for c in deg_cards.values() if c["status"] == "unknown"),
        "degraded_weather_possible_count": len(degraded_possible),
        "false_optimistic_promotions_on_missing_data": len(false_promotions),
        "conservative_fallback_verified": len(false_promotions) == 0 and len(degraded_possible) == 0,
    }


def run_ablation_study(station_limit: int | None = None) -> dict:
    """Compare Baseline, Variant A (+Soil), Variant B (+GAEZ), Variant C (+Calendars), and Variant D (Combined Evidence)."""
    rows = load_station_manifest()
    if station_limit is not None:
        rows = rows[:station_limit]

    variants = {
        "Baseline (Climate only)": {"use_soil": False, "use_gaez": False, "use_calendar": False},
        "Variant A (+Soil context)": {"use_soil": True, "use_gaez": False, "use_calendar": False},
        "Variant B (+GAEZ v5 cross-check)": {"use_soil": False, "use_gaez": True, "use_calendar": False},
        "Variant C (+Crop calendars)": {"use_soil": False, "use_gaez": False, "use_calendar": True},
        "Variant D (Combined 6-layer evidence)": {"use_soil": True, "use_gaez": True, "use_calendar": True},
    }

    metrics = {
        name: {
            "total_evaluations": 0,
            "worth_investigating_count": 0,
            "conditional_count": 0,
            "constraints_or_blocked_count": 0,
            "insufficient_evidence_count": 0,
            "unflagged_gaez_unsuitable_promotions": 0,
            "gaez_compared_pairs": 0,
            "gaez_directional_agreement_count": 0,
            "mean_assessed_factors_per_crop": [],
        }
        for name in variants
    }

    # Synthetic/representative FAO calendar window for boreal vs austral growing seasons
    for row in rows:
        lat, lon = float(row["latitude"]), float(row["longitude"])
        country = row["country"]
        ds = archived_history(request_parameters(lat, lon, date(2001, 1, 1), date(2025, 12, 31)))
        if ds is None:
            continue

        window = Window(5, 1, 9, 30) if lat >= 0 else Window(11, 1, 3, 31)
        soil_arch = soil_context(lat, lon, offline=True)
        inferred_ph = soil_arch["value"] if soil_arch.get("status") == "verified" else 6.1

        cal_rows = [
            {
                "crop": "General",
                "zone": f"{country} primary rainfed zone",
                "season": "Main season",
                "sow_from": "1 Apr" if lat >= 0 else "1 Oct",
                "sow_to": "31 May" if lat >= 0 else "30 Nov",
                "harvest_from": "1 Sep" if lat >= 0 else "1 Mar",
                "harvest_to": "31 Oct" if lat >= 0 else "30 Apr",
            }
        ]
        cal_match = match_crop_calendar(window, cal_rows)

        for v_name, cfg in variants.items():
            farm = Farm(
                country=country,
                latitude=lat,
                longitude=lon,
                windows=(window,),
                ph=inferred_ph if cfg["use_soil"] else None,
                drainage="well_drained",
                irrigation="rainfed",
                irrigation_mm=0.0,
                rain_fraction=0.70,
            )
            cards = find_options(farm, ds)
            m = metrics[v_name]
            for c in cards:
                cid = c["id"]
                m["total_evaluations"] += 1
                factors_n = len(c["assessed"]) + int(cfg["use_gaez"] and cid in GAEZ_CROP_ID_MAP) + int(cfg["use_calendar"])
                m["mean_assessed_factors_per_crop"].append(factors_n)

                if cfg["use_gaez"] or cfg["use_calendar"]:
                    layers = build_evidence_layers(
                        c,
                        farm,
                        modelled_soil={"value": inferred_ph} if cfg["use_soil"] else None,
                        calendar_match=cal_match if cfg["use_calendar"] else None,
                    )
                    if not cfg["use_gaez"]:
                        # Isolate calendar-only or soil-only effect when use_gaez is False
                        code = (
                            "not_compatible"
                            if c["status"] == "blocked"
                            else (
                                "important_constraints"
                                if c["status"] == "outside"
                                else (
                                    "insufficient_evidence"
                                    if c["status"] == "unknown"
                                    else ("conditional_compatibility" if c["status"] == "check" else "worth_investigating")
                                )
                            )
                        )
                    else:
                        code = layers["classification_code"]
                else:
                    code = (
                        "not_compatible"
                        if c["status"] == "blocked"
                        else (
                            "important_constraints"
                            if c["status"] == "outside"
                            else (
                                "insufficient_evidence"
                                if c["status"] == "unknown"
                                else ("conditional_compatibility" if c["status"] == "check" else "worth_investigating")
                            )
                        )
                    )

                if code == "worth_investigating":
                    m["worth_investigating_count"] += 1
                elif code == "conditional_compatibility":
                    m["conditional_count"] += 1
                elif code in {"important_constraints", "not_compatible"}:
                    m["constraints_or_blocked_count"] += 1
                else:
                    m["insufficient_evidence_count"] += 1

                # Benchmark against GAEZ v5 suitability class at this station
                gaez_name = GAEZ_CROP_ID_MAP.get(cid)
                if gaez_name:
                    g_pt = gaez_point(lat, lon, gaez_name, "rainfed")
                    if g_pt.get("status") == "verified":
                        m["gaez_compared_pairs"] += 1
                        g_code = g_pt["class_code"]
                        if g_code in {7, 8} and code == "worth_investigating":
                            m["unflagged_gaez_unsuitable_promotions"] += 1
                        if (g_code in {1, 2, 3, 4, 5, 6} and code in {"worth_investigating", "conditional_compatibility"}) or (
                            g_code in {7, 8} and code in {"conditional_compatibility", "important_constraints", "not_compatible"}
                        ):
                            m["gaez_directional_agreement_count"] += 1

    summary_table = []
    for v_name, m in metrics.items():
        tot = max(m["total_evaluations"], 1)
        gp = max(m["gaez_compared_pairs"], 1)
        summary_table.append(
            {
                "variant": v_name,
                "total_evaluations": m["total_evaluations"],
                "mean_assessed_factors": round(float(np.mean(m["mean_assessed_factors_per_crop"])), 2),
                "worth_investigating_rate": round(m["worth_investigating_count"] / tot, 4),
                "conditional_compatibility_rate": round(m["conditional_count"] / tot, 4),
                "constraints_or_blocked_rate": round(m["constraints_or_blocked_count"] / tot, 4),
                "insufficient_evidence_rate": round(m["insufficient_evidence_count"] / tot, 4),
                "unflagged_gaez_unsuitable_promotion_rate": round(m["unflagged_gaez_unsuitable_promotions"] / gp, 4),
                "gaez_directional_agreement_rate": round(m["gaez_directional_agreement_count"] / gp, 4),
            }
        )

    return {
        "stations_evaluated": len(rows),
        "variants": summary_table,
    }
