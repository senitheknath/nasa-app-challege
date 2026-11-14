"""Multi-year extreme weather diagnostics and stage-aware agro-climatic risk assessment."""
from __future__ import annotations

import numpy as np
import pandas as pd

from agroshift.science.climate.climate import dry_spell
from agroshift.science.soil_water.water_balance import DEFAULT_STAGE_FRACTIONS, build_daily_kc_curve


def _longest_run(mask: pd.Series) -> int:
    longest = run = 0
    for val in mask.to_numpy(dtype=bool):
        run = (run + 1) if val else 0
        if run > longest:
            longest = run
    return int(longest)


def compute_crop_gdd_series(
    t_mean: pd.Series,
    base_temp_c: float = 10.0,
    upper_temp_c: float | None = 35.0,
) -> pd.Series:
    """Compute daily Growing Degree Days with crop-specific base and optional upper cutoff temperature."""
    eff_t = t_mean.clip(upper=float(upper_temp_c)) if upper_temp_c is not None else t_mean
    return (eff_t - float(base_temp_c)).clip(lower=0.0)


def analyze_season_extremes(
    season_frame: pd.DataFrame,
    *,
    base_temp_c: float = 10.0,
    upper_temp_c: float = 35.0,
    heat_threshold_c: float = 35.0,
    reproductive_heat_threshold_c: float | None = None,
    frost_threshold_c: float = 0.0,
    sowing_date_confirmed: bool = False,
    stage_fractions: tuple[float, float, float, float] = DEFAULT_STAGE_FRACTIONS,
) -> dict:
    """Analyze extreme temperature, dry-spell, and heavy-rainfall metrics for one seasonal window."""
    if season_frame.empty:
        return {"valid": False, "status": "empty"}

    t_mean = season_frame["T2M"]
    t_min = season_frame["T2M_MIN"]
    t_max = season_frame["T2M_MAX"]
    rain = season_frame["PRECTOTCORR"]

    if t_mean.isna().any() or t_min.isna().any() or t_max.isna().any() or rain.isna().any():
        return {
            "valid": False,
            "status": "incomplete_coverage",
            "days": len(season_frame),
            "missing_days": {
                "T2M": int(t_mean.isna().sum()),
                "T2M_MIN": int(t_min.isna().sum()),
                "T2M_MAX": int(t_max.isna().sum()),
                "PRECTOTCORR": int(rain.isna().sum()),
            },
        }

    repro_thresh = float(reproductive_heat_threshold_c if reproductive_heat_threshold_c is not None else heat_threshold_c)
    gdd_daily = compute_crop_gdd_series(t_mean, base_temp_c=base_temp_c, upper_temp_c=upper_temp_c)
    frost_mask = t_min < float(frost_threshold_c)
    severe_frost_mask = t_min < -2.0
    heat_mask = t_max > float(heat_threshold_c)
    cdd_days, _ = dry_spell(rain)
    heavy_25_mask = rain >= 25.0
    heavy_50_mask = rain >= 50.0
    rx1day = float(rain.max())
    rx3day = float(rain.rolling(3, min_periods=1).sum().max())

    result = {
        "valid": True,
        "status": "complete",
        "days": len(season_frame),
        "gdd_total": round(float(gdd_daily.sum()), 1),
        "frost_days": int(frost_mask.sum()),
        "severe_frost_days": int(severe_frost_mask.sum()),
        "heat_stress_days": int(heat_mask.sum()),
        "longest_heat_wave_days": _longest_run(heat_mask),
        "longest_dry_spell_days": int(cdd_days),
        "heavy_rain_25mm_days": int(heavy_25_mask.sum()),
        "heavy_rain_50mm_days": int(heavy_50_mask.sum()),
        "max_1day_rain_mm": round(rx1day, 1),
        "max_3day_rain_mm": round(rx3day, 1),
        "extreme_tmin_c": round(float(t_min.min()), 2),
        "extreme_tmax_c": round(float(t_max.max()), 2),
    }

    if sowing_date_confirmed:
        _, stages = build_daily_kc_curve(len(season_frame), stage_fractions=stage_fractions)
        stage_series = pd.Series(stages, index=season_frame.index)
        mid_mask = stage_series == "mid_season"
        init_mask = stage_series == "initial"
        late_mask = stage_series == "late_season"
        mid_rain = rain.loc[mid_mask]
        mid_cdd, _ = dry_spell(mid_rain) if not mid_rain.empty else (0, False)
        result["stage_specific_mode"] = "stage_resolved_from_confirmed_sowing"
        result["reproductive_stage"] = {
            "days": int(mid_mask.sum()),
            "heat_days_over_repro_threshold": int((t_max.loc[mid_mask] > repro_thresh).sum()),
            "reproductive_heat_threshold_c": repro_thresh,
            "frost_days": int(frost_mask.loc[mid_mask].sum()),
            "longest_dry_spell_days": int(mid_cdd),
            "Establishment_heavy_rain_25mm_days": int(heavy_25_mask.loc[init_mask].sum()),
            "harvest_heavy_rain_25mm_days": int(heavy_25_mask.loc[late_mask].sum()),
        }
    else:
        result["stage_specific_mode"] = "general_seasonal_exposure_only"
        result["reproductive_stage"] = None

    return result


def summarize_historical_extremes(
    frame: pd.DataFrame,
    window,
    *,
    base_temp_c: float = 10.0,
    upper_temp_c: float = 35.0,
    heat_threshold_c: float = 35.0,
    reproductive_heat_threshold_c: float | None = None,
    frost_threshold_c: float = 0.0,
    sowing_date_confirmed: bool = False,
    stage_fractions: tuple[float, float, float, float] = DEFAULT_STAGE_FRACTIONS,
) -> dict:
    """Summarize multi-year extreme temperature, dry-spell, GDD, and heavy-rainfall risks across seasons."""
    if frame.empty:
        return {"valid_seasons": 0, "status": "no_data"}

    seasons = []
    repro_rows = []
    for year in range(frame.index.min().year, frame.index.max().year + 1):
        try:
            start, end = window.dates(year)
        except ValueError:
            continue
        idx = pd.date_range(start, end)
        if idx[0] < frame.index.min() or idx[-1] > frame.index.max():
            continue
        part = frame.reindex(idx)
        row = analyze_season_extremes(
            part,
            base_temp_c=base_temp_c,
            upper_temp_c=upper_temp_c,
            heat_threshold_c=heat_threshold_c,
            reproductive_heat_threshold_c=reproductive_heat_threshold_c,
            frost_threshold_c=frost_threshold_c,
            sowing_date_confirmed=sowing_date_confirmed,
            stage_fractions=stage_fractions,
        )
        if row.get("valid"):
            row["year"] = year
            seasons.append(row)
            if row.get("reproductive_stage"):
                repro_rows.append(row["reproductive_stage"])

    if not seasons:
        return {"valid_seasons": 0, "status": "insufficient_complete_seasons"}

    df = pd.DataFrame(seasons)
    n_seasons = len(df)
    frost_seasons = int((df["frost_days"] > 0).sum())
    heat_seasons = int((df["heat_stress_days"] > 0).sum())
    dry10_seasons = int((df["longest_dry_spell_days"] >= 10).sum())
    dry15_seasons = int((df["longest_dry_spell_days"] >= 15).sum())
    heavy50_seasons = int((df["heavy_rain_50mm_days"] > 0).sum())

    summary = {
        "status": "verified",
        "valid_seasons": int(n_seasons),
        "thresholds": {
            "base_temp_c": float(base_temp_c),
            "upper_temp_c": float(upper_temp_c),
            "heat_threshold_c": float(heat_threshold_c),
            "reproductive_heat_threshold_c": float(
                reproductive_heat_threshold_c if reproductive_heat_threshold_c is not None else heat_threshold_c
            ),
            "frost_threshold_c": float(frost_threshold_c),
        },
        "gdd_median": round(float(df["gdd_total"].median()), 1),
        "gdd_p25": round(float(df["gdd_total"].quantile(0.25)), 1),
        "gdd_p75": round(float(df["gdd_total"].quantile(0.75)), 1),
        "frost_days_median": round(float(df["frost_days"].median()), 1),
        "frost_days_max": int(df["frost_days"].max()),
        "seasons_with_frost_fraction": round(frost_seasons / n_seasons, 3),
        "heat_stress_days_median": round(float(df["heat_stress_days"].median()), 1),
        "heat_stress_days_p75": round(float(df["heat_stress_days"].quantile(0.75)), 1),
        "heat_stress_days_max": int(df["heat_stress_days"].max()),
        "longest_heat_wave_max_days": int(df["longest_heat_wave_days"].max()),
        "seasons_with_heat_stress_fraction": round(heat_seasons / n_seasons, 3),
        "dry_spell_median_days": round(float(df["longest_dry_spell_days"].median()), 1),
        "dry_spell_p75_days": round(float(df["longest_dry_spell_days"].quantile(0.75)), 1),
        "dry_spell_max_days": int(df["longest_dry_spell_days"].max()),
        "seasons_with_dry_spell_10d_fraction": round(dry10_seasons / n_seasons, 3),
        "seasons_with_dry_spell_15d_fraction": round(dry15_seasons / n_seasons, 3),
        "heavy_rain_25mm_days_median": round(float(df["heavy_rain_25mm_days"].median()), 1),
        "heavy_rain_50mm_days_max": int(df["heavy_rain_50mm_days"].max()),
        "seasons_with_50mm_rain_fraction": round(heavy50_seasons / n_seasons, 3),
        "max_1day_rain_mm": round(float(df["max_1day_rain_mm"].max()), 1),
        "max_3day_rain_mm": round(float(df["max_3day_rain_mm"].max()), 1),
        "extreme_tmin_c": round(float(df["extreme_tmin_c"].min()), 2),
        "extreme_tmax_c": round(float(df["extreme_tmax_c"].max()), 2),
        "stage_specific_mode": (
            "stage_resolved_from_confirmed_sowing"
            if sowing_date_confirmed
            else "general_seasonal_exposure_only"
        ),
    }

    if sowing_date_confirmed and repro_rows:
        rdf = pd.DataFrame(repro_rows)
        summary["reproductive_stage_summary"] = {
            "heat_days_median": round(float(rdf["heat_days_over_repro_threshold"].median()), 1),
            "heat_days_max": int(rdf["heat_days_over_repro_threshold"].max()),
            "frost_days_max": int(rdf["frost_days"].max()),
            "dry_spell_median_days": round(float(rdf["longest_dry_spell_days"].median()), 1),
            "dry_spell_max_days": int(rdf["longest_dry_spell_days"].max()),
            "establishment_heavy_rain_days_median": round(
                float(rdf["Establishment_heavy_rain_25mm_days"].median()), 1
            ),
            "harvest_heavy_rain_days_median": round(
                float(rdf["harvest_heavy_rain_25mm_days"].median()), 1
            ),
        }
        summary["stage_note"] = (
            "Stage-specific exposure evaluated across initial, development, mid-season (flowering/reproductive), "
            "and late-season stages using confirmed sowing dates."
        )
    else:
        summary["reproductive_stage_summary"] = None
        summary["stage_note"] = (
            "Exact sowing/flowering dates are not confirmed; reporting whole-window historical exposure "
            "rather than stage-specific reproductive timing."
        )

    return summary
