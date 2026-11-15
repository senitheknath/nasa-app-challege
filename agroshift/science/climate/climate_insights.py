"""Site climatology and FAO growing-period hints for the farmer interface.

These helpers summarise the verified NASA POWER history that is already loaded.
They never alter screening results, and they never choose a season for the
farmer. The growing-period rule follows FAO agro-ecological zoning: the rainfed
growing period is the part of the year when precipitation is at least half of
potential evapotranspiration and mean temperature is at least 5 °C. Here it is
applied to *monthly* means with no soil-water carry-over, so it is an
approximation and is labelled as one.
"""

from __future__ import annotations

import calendar

import numpy as np
import pandas as pd

from agroshift.science.climate.climate import aggregate

MIN_YEARS = 10
LGP_RAIN_FRACTION = 0.5
LGP_MIN_TEMPERATURE_C = 5.0
METHOD = (
    "FAO agro-ecological zoning rule (rain ≥ ½ reference evapotranspiration and "
    "mean temperature ≥ 5 °C) applied to monthly NASA POWER averages. "
    "Monthly approximation without soil-water carry-over; Hargreaves ET₀ (FAO-56 Eq. 52)."
)
_CACHE: dict = {}


def _key(dataset):
    p = dataset.provenance
    return (p.get("sha256"), p.get("dataset_id"), tuple(p.get("request", {}).items()) if isinstance(p.get("request"), dict) else None)


def monthly_climatology(frame: pd.DataFrame, min_years: int = MIN_YEARS) -> pd.DataFrame:
    """Return mean monthly climate (index 1–12) from complete months only.

    Columns: rain_mm, et0_mm, t_mean, t_max, t_min, years_rain, years_temp.
    A value is NaN when fewer than ``min_years`` complete months exist.
    """
    monthly = aggregate(frame)
    month = monthly.index.month
    rain = monthly["rainfall_mm"].groupby(month)
    et0 = monthly["et0_mm"].groupby(month)
    temp = monthly["temperature_c"].groupby(month)
    daily = frame[[c for c in ("T2M_MAX", "T2M_MIN") if c in frame]]
    out = pd.DataFrame(index=pd.Index(range(1, 13), name="month"))
    out["years_rain"] = rain.count().reindex(out.index).fillna(0).astype(int)
    out["years_temp"] = temp.count().reindex(out.index).fillna(0).astype(int)
    out["rain_mm"] = rain.mean().reindex(out.index).where(out["years_rain"] >= min_years)
    out["et0_mm"] = et0.mean().reindex(out.index).where(et0.count().reindex(out.index).fillna(0) >= min_years)
    out["t_mean"] = temp.mean().reindex(out.index).where(out["years_temp"] >= min_years)
    for col, name in (("T2M_MAX", "t_max"), ("T2M_MIN", "t_min")):
        if col in daily:
            grouped = daily[col].resample("MS")
            counts = grouped.count()
            expected = counts.index.days_in_month
            means = grouped.mean().where(counts >= 0.9 * expected)
            by_month = means.groupby(means.index.month)
            out[name] = by_month.mean().reindex(out.index).where(by_month.count().reindex(out.index).fillna(0) >= min_years)
        else:
            out[name] = np.nan
    return out


def climatology_for(dataset) -> pd.DataFrame:
    """Cached climatology keyed by the dataset's verified digest."""
    key = _key(dataset)
    if key not in _CACHE:
        if len(_CACHE) > 32:
            _CACHE.clear()
        _CACHE[key] = monthly_climatology(dataset.frame)
    return _CACHE[key].copy()


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    """Circular runs of True as (start_index, length) over 12 months."""
    n = len(flags)
    if all(flags):
        return [(0, n)]
    if not any(flags):
        return []
    start = next(i for i in range(n) if not flags[i])  # rotate so a False comes first
    runs, i = [], 0
    while i < n:
        idx = (start + i) % n
        if flags[idx]:
            j = i
            while j < n and flags[(start + j) % n]:
                j += 1
            runs.append((idx, j - i))
            i = j
        else:
            i += 1
    return runs


def growing_period(clim: pd.DataFrame) -> dict:
    """Months supported by rain under the FAO LGP rule (monthly approximation)."""
    needed = clim[["rain_mm", "et0_mm", "t_mean"]]
    if needed.isna().any().any():
        missing = [calendar.month_abbr[m] for m in needed.index[needed.isna().any(axis=1)]]
        return dict(status="unknown", supported=[], run=None, method=METHOD,
                    note="Too few complete years for: " + ", ".join(missing) + ".")
    flags = [
        bool(r >= LGP_RAIN_FRACTION * e and t >= LGP_MIN_TEMPERATURE_C)
        for r, e, t in zip(clim["rain_mm"], clim["et0_mm"], clim["t_mean"])
    ]
    supported = [m for m, f in zip(range(1, 13), flags) if f]
    runs = _runs(flags)
    if not runs:
        return dict(status="none", supported=[], run=None, method=METHOD,
                    note="On average no month reaches half of reference evapotranspiration. Rainfed cropping is likely to need irrigation.")
    start, length = max(runs, key=lambda r: (r[1], clim["rain_mm"].iloc[[(r[0] + k) % 12 for k in range(r[1])]].sum()))
    run = (start + 1, (start + length - 1) % 12 + 1, length)
    status = "all" if length == 12 else "partial"
    note = (
        "On average every month reaches half of reference evapotranspiration."
        if status == "all"
        else f"Longest rain-supported period: {calendar.month_name[run[0]]} to {calendar.month_name[run[1]]} ({length} months)."
    )
    return dict(status=status, supported=supported, run=run, method=METHOD, note=note)


def suggest_window(clim: pd.DataFrame, gp: dict | None = None) -> dict | None:
    """A season the farmer *may* choose. Returns None when no basis exists."""
    gp = gp or growing_period(clim)
    if gp["status"] in ("unknown", "none"):
        return None
    if gp["status"] == "all":
        rain = clim["rain_mm"].to_numpy()
        sums = [sum(rain[(i + k) % 12] for k in range(4)) for i in range(12)]
        i = int(np.argmax(sums))
        return dict(start_month=i + 1, end_month=(i + 3) % 12 + 1, months=4,
                    basis="Wettest four consecutive months (every month is rain-supported on average)")
    start, end, length = gp["run"]
    return dict(start_month=start, end_month=end, months=length,
                basis="Longest rain-supported period from your location's weather history")


def site_summary(dataset) -> dict:
    """Headline numbers for KPI tiles. Values are None when not computable."""
    clim = climatology_for(dataset)
    gp = growing_period(clim)
    rain = clim["rain_mm"]
    temp = clim["t_mean"]
    req = dataset.provenance.get("request", {})
    first, last = str(req.get("start", ""))[:4], str(req.get("end", ""))[:4]
    hottest = int(clim["t_max"].idxmax()) if clim["t_max"].notna().any() else None
    coolest = int(clim["t_min"].idxmin()) if clim["t_min"].notna().any() else None
    return dict(
        annual_rain_mm=float(rain.sum()) if rain.notna().all() else None,
        annual_et0_mm=float(clim["et0_mm"].sum()) if clim["et0_mm"].notna().all() else None,
        mean_temp_c=float(temp.mean()) if temp.notna().all() else None,
        hottest_month=hottest,
        hottest_tmax_c=float(clim["t_max"].max()) if hottest else None,
        coolest_month=coolest,
        coolest_tmin_c=float(clim["t_min"].min()) if coolest else None,
        wettest_month=int(rain.idxmax()) if rain.notna().any() else None,
        supported_months=len(gp["supported"]),
        growing_period=gp,
        years=f"{first}–{last}" if first and last else "",
        climatology=clim,
    )


def window_months(window) -> list[int]:
    """Calendar months touched by a recurring Window (handles New Year crossing)."""
    if window is None:
        return []
    s, e = window.start_month, window.end_month
    return [((s - 1 + k) % 12) + 1 for k in range(((e - s) % 12) + 1)]


def seasonal_weather_risk_summary(dataset, window) -> dict | None:
    """Compute historical weather-extreme frequencies and decadal shift for a recurring window."""
    if dataset is None or window is None or dataset.frame.empty:
        return None
    from agroshift.science.climate.extremes import analyze_season_extremes

    frame = dataset.frame
    rows = []
    for year in range(frame.index.min().year, frame.index.max().year + 1):
        start, end = window.dates(year)
        days = pd.date_range(start, end)
        if days[0] < frame.index.min() or days[-1] > frame.index.max():
            continue
        sub = frame.reindex(days)
        if sub["T2M"].isna().any() or sub["PRECTOTCORR"].isna().any():
            continue
        ext = analyze_season_extremes(sub)
        if ext.get("status") != "complete":
            continue
        rows.append(
            dict(
                year=year,
                t_mean=float(sub["T2M"].mean()),
                rain_mm=float(sub["PRECTOTCORR"].sum()),
                frost_days=int(ext.get("frost_days") or 0),
                heat_days=int(ext.get("heat_stress_days") or 0),
                longest_dry_days=int(ext.get("longest_dry_spell_days") or 0),
                heavy_rain_25=int(ext.get("heavy_rain_25mm_days") or 0),
                gdd=float(ext.get("gdd_total") or 0.0),
            )
        )
    if len(rows) < 5:
        return None
    df = pd.DataFrame(rows)
    n = len(df)
    early = df[df["year"] <= 2012]
    recent = df[df["year"] >= 2013]
    warming_delta = (
        float(recent["t_mean"].mean() - early["t_mean"].mean())
        if len(early) >= 3 and len(recent) >= 3
        else None
    )
    dry_delta = (
        float(recent["longest_dry_days"].mean() - early["longest_dry_days"].mean())
        if len(early) >= 3 and len(recent) >= 3
        else None
    )
    return dict(
        seasons_evaluated=n,
        frost_seasons=int((df["frost_days"] > 0).sum()),
        median_frost_days=int(df["frost_days"].median()),
        heat_seasons=int((df["heat_days"] > 0).sum()),
        median_heat_days=int(df["heat_days"].median()),
        dry_spell_14d_seasons=int((df["longest_dry_days"] >= 14).sum()),
        median_dry_spell_days=int(df["longest_dry_days"].median()),
        max_dry_spell_days=int(df["longest_dry_days"].max()),
        heavy_rain_seasons=int((df["heavy_rain_25"] > 0).sum()),
        median_heavy_rain_days=int(df["heavy_rain_25"].median()),
        median_gdd10=round(float(df["gdd"].median()), 0),
        warming_delta_c=round(warming_delta, 2) if warming_delta is not None else None,
        dry_spell_delta_days=round(dry_delta, 1) if dry_delta is not None else None,
    )


def crop_12month_sowing_matrix(dataset, cards: list[dict], max_crops: int = 8) -> dict | None:
    """Evaluate how each candidate crop fits all 12 possible planting start months."""
    if dataset is None or not cards:
        return None
    from agroshift.science.knowledge.knowledge import global_traits

    clim = climatology_for(dataset)
    if clim["t_mean"].isna().all():
        return None

    all_traits = {}
    for row in global_traits():
        if row.get("review_status") == "reviewed" and row.get("scope") == "global":
            all_traits.setdefault(row["crop_id"], {})[row["trait"]] = row

    matrix_rows = []
    for card in cards:
        if len(matrix_rows) >= max_crops:
            break
        cid = card["id"]
        ct = all_traits.get(cid, {})
        t_ref = ct.get("preferred_daily_mean_air_temperature")
        w_ref = ct.get("seasonal_crop_et")
        d_ref = ct.get("indicative_cycle_duration")
        if not t_ref:
            continue
        dur_days = float(d_ref["low"] + d_ref["high"]) / 2.0 if d_ref else 110.0
        n_months = max(2, min(8, round(dur_days / 30.0)))
        t_lo, t_hi = float(t_ref["low"]), float(t_ref["high"])
        w_lo = float(w_ref["low"]) if w_ref else None

        cells = []
        best_months = []
        for s_m in range(1, 13):
            span = [((s_m - 1 + k) % 12) + 1 for k in range(n_months)]
            sub = clim.loc[span]
            t_avg = float(sub["t_mean"].mean())
            r_sum = float(sub["rain_mm"].sum())
            t_ok = t_lo <= t_avg <= t_hi
            t_near = (t_lo - 2.5) <= t_avg <= (t_hi + 2.5)
            r_ok = True if w_lo is None else (r_sum >= 0.65 * w_lo)
            if t_ok and r_ok:
                state, code = "optimal", "●"
                best_months.append(calendar.month_abbr[s_m])
            elif t_ok and not r_ok:
                state, code = "needs_water", "▲"
            elif t_near:
                state, code = "marginal", "◆"
            else:
                state, code = "outside", "✕"
            cells.append(
                dict(
                    month=s_m,
                    month_abbr=calendar.month_abbr[s_m],
                    end_abbr=calendar.month_abbr[span[-1]],
                    state=state,
                    code=code,
                    t_avg=round(t_avg, 1),
                    rain_mm=round(r_sum, 0),
                )
            )
        matrix_rows.append(
            dict(
                id=cid,
                name=card["name"],
                cycle_months=n_months,
                temp_range=f"{t_lo:g}–{t_hi:g} °C",
                water_min_mm=round(w_lo) if w_lo else None,
                best_sowing_months=best_months,
                cells=cells,
            )
        )
    if not matrix_rows:
        return None
    return dict(rows=matrix_rows)


def crop_stage_water_demand(crop_id: str, dataset, window) -> list[dict] | None:
    """Compute 4-stage FAO-56 crop water demand (ETc = Kc * ET0) vs historical rainfall."""
    if dataset is None or window is None:
        return None
    from agroshift.science.knowledge.knowledge import growth_stages

    stages = growth_stages(crop_id)
    if not stages:
        return None
    clim = climatology_for(dataset)
    months = window_months(window)
    if not months:
        return None
    sub = clim.loc[months]
    if sub["et0_mm"].isna().all() or sub["rain_mm"].isna().all():
        return None
    total_days = max(30, len(months) * 30.4)
    daily_et0 = float(sub["et0_mm"].sum()) / total_days
    daily_rain = float(sub["rain_mm"].sum()) / total_days

    stage_labels = {
        "initial": "1. Establishment (Initial)",
        "development": "2. Vegetative Growth",
        "mid_season": "3. Flowering & Yield Formation",
        "late_season": "4. Ripening & Harvest",
    }
    out = []
    for st_row in stages:
        st_name = st_row["stage_code"]
        kc = 0.5 * (float(st_row.get("kc_min") or 0.8) + float(st_row.get("kc_max") or 0.8))
        f_lo = float(st_row.get("duration_fraction_min") or 0.25)
        f_hi = float(st_row.get("duration_fraction_max") or f_lo)
        days = max(7, round(total_days * 0.5 * (f_lo + f_hi)))
        etc_mm = round(days * daily_et0 * kc, 0)
        rain_mm = round(days * daily_rain, 0)
        out.append(
            dict(
                stage_key=st_name,
                label=stage_labels.get(st_name, st_name.replace("_", " ").title()),
                days=days,
                kc=round(kc, 2),
                etc_mm=etc_mm,
                rain_mm=rain_mm,
                deficit_mm=max(0.0, round(etc_mm - rain_mm, 0)),
                note=st_row.get("note") or "",
            )
        )
    return out


def previous_crop_rotation_badge(previous_crop_id: str | None, candidate_crop_id: str) -> dict | None:
    """Evaluate botanical succession from the farmer's previous crop using rotation_engine."""
    if not previous_crop_id or previous_crop_id in ("unknown", ""):
        return None
    from agroshift.science.knowledge.knowledge import crop_by_id
    from agroshift.rotation import evaluate_transition

    prev_crop = crop_by_id(previous_crop_id)
    cand_crop = crop_by_id(candidate_crop_id)
    if not prev_crop or not cand_crop:
        return None
    res = evaluate_transition(prev_crop, cand_crop)
    if not res:
        return None
    status = res.get("status")
    benefits = res.get("benefits", [])
    cautions = res.get("cautions", [])
    blockers = res.get("blockers", [])
    if blockers:
        return dict(
            kind="blocked",
            label="✕ Rotation conflict",
            detail=blockers[0],
        )
    if any("leguminous" in b.lower() or "fabaceae" in b.lower() for b in benefits):
        return dict(
            kind="legume_benefit",
            label="✓ Legume rotation break",
            detail=benefits[0],
        )
    if status in ("caution", "conditional") and cautions:
        return dict(
            kind="caution",
            label="▲ Same-family / succession caution",
            detail=cautions[0],
        )
    if benefits:
        return dict(
            kind="good",
            label="✓ Botanical family break",
            detail=benefits[0],
        )
    return None
