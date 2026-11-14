"""Educational, source-backed pest, disease, and weed pressure context without outbreak predictions or chemical prescriptions."""
from __future__ import annotations

import pandas as pd

from agroshift.science.knowledge.knowledge import pest_context


def evaluate_crop_pest_context(
    crop_id: str,
    frame: pd.DataFrame | None = None,
    window=None,
) -> dict:
    """Return reviewed educational pest/disease context and historical environmental conduciveness indicators."""
    records = pest_context(crop_id)
    if not records:
        return {
            "crop_id": crop_id,
            "status": "no_reviewed_records",
            "records": [],
            "chemical_prescription_included": False,
            "outbreak_probability_predicted": False,
            "disclaimer": (
                "No reviewed pest or disease context records are loaded for this crop. "
                "Consult local agricultural extension services for regional pest monitoring."
            ),
        }

    # Summarize relevant environmental conduciveness indicators from historical weather if available
    env_indicators = {}
    if frame is not None and not frame.empty and window is not None:
        humid_seasons = 0
        warm_seasons = 0
        dry_spell_seasons = 0
        total_seasons = 0
        for year in range(frame.index.min().year, frame.index.max().year + 1):
            try:
                start, end = window.dates(year)
            except ValueError:
                continue
            idx = pd.date_range(start, end)
            if idx[0] < frame.index.min() or idx[-1] > frame.index.max():
                continue
            part = frame.reindex(idx)
            if part["T2M"].isna().any() or part["PRECTOTCORR"].isna().any():
                continue
            total_seasons += 1
            t_mean = float(part["T2M"].mean())
            if 22.0 <= t_mean <= 32.0:
                warm_seasons += 1
            if "RH2M" in part and part["RH2M"].notna().any() and float(part["RH2M"].mean()) >= 78.0:
                humid_seasons += 1
            if int((part["PRECTOTCORR"] < 1.0).sum()) >= 25:
                dry_spell_seasons += 1

        if total_seasons > 0:
            env_indicators = {
                "valid_seasons_checked": total_seasons,
                "warm_season_fraction": round(warm_seasons / total_seasons, 2),
                "high_humidity_season_fraction": round(humid_seasons / total_seasons, 2),
                "extended_dry_days_season_fraction": round(dry_spell_seasons / total_seasons, 2),
            }

    enriched = []
    for rec in records:
        cond_lower = rec["favorable_condition"].lower()
        note = "General reference context."
        if env_indicators:
            if ("humid" in cond_lower or "wet" in cond_lower) and env_indicators.get("high_humidity_season_fraction", 0) >= 0.4:
                note = (
                    f"Historical window averaged high relative humidity (≥78%) in "
                    f"{env_indicators['high_humidity_season_fraction']:.0%} of seasons; monitor susceptible stages closely."
                )
            elif "drought" in cond_lower and env_indicators.get("extended_dry_days_season_fraction", 0) >= 0.4:
                note = (
                    f"Historical window included extended dry days in "
                    f"{env_indicators['extended_dry_days_season_fraction']:.0%} of seasons; manage late-season moisture stress."
                )
            elif "warm" in cond_lower and env_indicators.get("warm_season_fraction", 0) >= 0.5:
                note = (
                    f"Historical window temperatures averaged 22–32 °C in "
                    f"{env_indicators['warm_season_fraction']:.0%} of seasons."
                )
        enriched.append({**rec, "historical_climate_note": note})

    return {
        "crop_id": crop_id,
        "status": "verified",
        "records": enriched,
        "environmental_indicators": env_indicators,
        "chemical_prescription_included": False,
        "outbreak_probability_predicted": False,
        "disclaimer": (
            "Educational agro-ecological pest, disease, and weed context only. "
            "AgroShift AI does not predict outbreak probabilities or prescribe chemical pesticides; "
            "confirm local pest thresholds with certified extension advisors."
        ),
    }
