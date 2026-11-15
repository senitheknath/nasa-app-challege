"""FAO-56 Penman-Monteith & Hargreaves ET0 and daily root-zone crop water balance."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd


DEFAULT_STAGE_FRACTIONS = (0.18, 0.28, 0.32, 0.22)


def extraterrestrial_radiation_mj(latitude: float, doy: np.ndarray) -> np.ndarray:
    """Compute daily extraterrestrial radiation Ra (MJ/m²/day) using FAO-56 Eq. 21-25."""
    phi = math.radians(float(latitude))
    angle = 2.0 * math.pi * doy / 365.0
    decl = 0.409 * np.sin(angle - 1.39)
    dr = 1.0 + 0.033 * np.cos(angle)
    cos_ws = np.clip(-np.tan(phi) * np.tan(decl), -1.0, 1.0)
    ws = np.arccos(cos_ws)
    ra = (24.0 * 60.0 / math.pi) * 0.0820 * dr * (
        ws * np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.sin(ws)
    )
    return np.maximum(ra, 0.0)


def compute_fao56_penman_monteith_daily(
    frame: pd.DataFrame,
    latitude: float | None = None,
    elevation_m: float | None = None,
) -> pd.DataFrame:
    """Compute daily FAO-56 Penman-Monteith ET0 with automatic Hargreaves fallback when wind/radiation are absent."""
    lat = latitude if latitude is not None else frame.attrs.get("latitude")
    if lat is None:
        raise ValueError("Latitude is required to compute extraterrestrial radiation and ET0.")

    idx = frame.index
    missing = pd.Series(np.nan, index=idx, dtype="float64")
    t_mean = frame.get("T2M", missing).astype("float64")
    t_min = frame.get("T2M_MIN", missing).astype("float64")
    t_max = frame.get("T2M_MAX", missing).astype("float64")
    rh = frame.get("RH2M", missing).astype("float64")
    t_dew = frame.get("T2MDEW", missing).astype("float64")
    rs = frame.get("ALLSKY_SFC_SW_DWN", missing).astype("float64")
    ws2 = frame.get("WS2M", missing).astype("float64")
    ws10 = frame.get("WS10M", missing).astype("float64")
    ps = frame.get("PS", missing).astype("float64")

    # Wind speed at 2m height (FAO-56 Eq. 47 converts 10m wind to 2m wind)
    u2_from_10m = ws10 * (4.87 / math.log(67.8 * 10.0 - 5.42))
    u2 = ws2.where(ws2.notna(), u2_from_10m)

    # Atmospheric pressure P (kPa) and psychrometric constant gamma (kPa/°C, FAO-56 Eq. 7-8)
    elev = float(elevation_m) if elevation_m is not None else 100.0
    p_std = 101.3 * ((293.0 - 0.0065 * elev) / 293.0) ** 5.26
    pressure_kpa = ps.where(ps.notna(), p_std)
    gamma = 0.000665 * pressure_kpa

    # Saturation and actual vapour pressure (kPa, FAO-56 Eq. 11-19)
    es_tmax = 0.6108 * np.exp((17.27 * t_max) / (t_max + 237.3))
    es_tmin = 0.6108 * np.exp((17.27 * t_min) / (t_min + 237.3))
    es = 0.5 * (es_tmax + es_tmin)
    ea_dew = 0.6108 * np.exp((17.27 * t_dew) / (t_dew + 237.3))
    ea_rh = es * (rh / 100.0)
    ea = ea_dew.where(ea_dew.notna(), ea_rh)
    vpd = np.maximum(0.0, es - ea)

    # Slope of saturation vapour pressure curve Delta (kPa/°C, FAO-56 Eq. 13)
    delta = (4098.0 * (0.6108 * np.exp((17.27 * t_mean) / (t_mean + 237.3)))) / ((t_mean + 237.3) ** 2)

    # Radiation terms (MJ/m²/day, FAO-56 Eq. 21-39)
    doy = idx.day_of_year.to_numpy(dtype=float)
    ra = pd.Series(extraterrestrial_radiation_mj(float(lat), doy), index=idx, dtype="float64")
    rso = (0.75 + 2.0e-5 * elev) * ra
    rns = (1.0 - 0.23) * rs
    rel_rs = np.clip(rs / rso.replace(0.0, np.nan), 0.3, 1.0)
    sigma = 4.903e-9
    rnl = (
        sigma
        * (((t_max + 273.16) ** 4 + (t_min + 273.16) ** 4) / 2.0)
        * (0.34 - 0.14 * np.sqrt(np.maximum(ea, 0.0)))
        * (1.35 * rel_rs - 0.35)
    )
    rn = rns - rnl

    # FAO-56 Penman-Monteith (Eq. 6, G = 0 for daily step)
    num_rad = 0.408 * delta * rn
    num_aero = gamma * (900.0 / (t_mean + 273.0)) * u2 * vpd
    denom = delta + gamma * (1.0 + 0.34 * u2)
    et0_pm = ((num_rad + num_aero) / denom).clip(lower=0.0)

    # FAO-56 Hargreaves (Eq. 52) fallback
    et0_hg = (
        0.0023
        * (t_mean + 17.8)
        * (t_max - t_min).clip(lower=0.0).pow(0.5)
        * (0.408 * ra)
    ).clip(lower=0.0)

    et0_best = et0_pm.where(et0_pm.notna(), et0_hg)
    method = pd.Series(
        np.where(
            et0_pm.notna(),
            "fao56_penman_monteith",
            np.where(et0_hg.notna(), "fao56_hargreaves", "missing"),
        ),
        index=idx,
        dtype="object",
    )

    return pd.DataFrame(
        {
            "et0_mm": et0_best,
            "et0_pm_mm": et0_pm,
            "et0_hargreaves_mm": et0_hg,
            "et0_method": method,
            "ra_mj_m2_day": ra,
            "rn_mj_m2_day": rn,
            "vpd_kpa": vpd,
            "u2_m_s": u2,
            "pressure_kpa": pressure_kpa,
        },
        index=idx,
    )


def build_daily_kc_curve(
    days: int,
    kc_ini: float = 0.40,
    kc_mid: float = 1.10,
    kc_end: float = 0.65,
    stage_fractions: tuple[float, float, float, float] = DEFAULT_STAGE_FRACTIONS,
) -> tuple[np.ndarray, list[str]]:
    """Build a piecewise-linear FAO-56 single crop coefficient curve across 4 growth stages."""
    if days <= 0:
        return np.array([], dtype=float), []
    total_frac = sum(stage_fractions)
    fracs = [f / total_frac for f in stage_fractions]
    n_ini = max(1, int(round(days * fracs[0])))
    n_dev = max(1, int(round(days * fracs[1])))
    n_mid = max(1, int(round(days * fracs[2])))
    n_late = max(1, days - (n_ini + n_dev + n_mid))
    # Adjust if rounding exceeded days
    while n_ini + n_dev + n_mid + n_late > days:
        if n_mid > 1:
            n_mid -= 1
        elif n_dev > 1:
            n_dev -= 1
        elif n_late > 1:
            n_late -= 1
        else:
            n_ini = max(0, n_ini - 1)
            break

    kc_vals: list[float] = []
    stages: list[str] = []
    for _ in range(n_ini):
        kc_vals.append(float(kc_ini))
        stages.append("initial")
    for idx in range(n_dev):
        frac = (idx + 1) / max(n_dev, 1)
        kc_vals.append(float(kc_ini + frac * (kc_mid - kc_ini)))
        stages.append("development")
    for _ in range(n_mid):
        kc_vals.append(float(kc_mid))
        stages.append("mid_season")
    for idx in range(n_late):
        frac = (idx + 1) / max(n_late, 1)
        kc_vals.append(float(kc_mid + frac * (kc_end - kc_mid)))
        stages.append("late_season")

    return np.asarray(kc_vals[:days], dtype=float), stages[:days]


def simulate_season_crop_water_balance(
    season_frame: pd.DataFrame,
    *,
    latitude: float | None = None,
    elevation_m: float | None = None,
    kc_ini: float = 0.40,
    kc_mid: float = 1.10,
    kc_end: float = 0.65,
    stage_fractions: tuple[float, float, float, float] = DEFAULT_STAGE_FRACTIONS,
    rooting_depth_m: float = 1.0,
    depletion_fraction_p: float = 0.50,
    available_water_capacity_mm_m: float = 140.0,
    initial_depletion_fraction: float = 0.25,
    effective_rain_method: str = "fao_scs_daily",
    is_paddy: bool = False,
    paddy_land_prep_mm: float = 175.0,
    paddy_percolation_mm_day: float = 3.0,
) -> dict:
    """Simulate daily FAO-56 root-zone crop water balance for a single growing season slice."""
    if season_frame.empty:
        return {"status": "empty", "valid": False}

    rain = season_frame["PRECTOTCORR"].astype("float64")
    et_df = compute_fao56_penman_monteith_daily(season_frame, latitude=latitude, elevation_m=elevation_m)
    et0 = et_df["et0_mm"]
    n_days = len(season_frame)
    kc_arr, stages = build_daily_kc_curve(
        n_days, kc_ini=kc_ini, kc_mid=kc_mid, kc_end=kc_end, stage_fractions=stage_fractions
    )

    if rain.isna().any() or et0.isna().any():
        return {
            "status": "incomplete_coverage",
            "valid": False,
            "days": n_days,
            "rain_missing_days": int(rain.isna().sum()),
            "et0_missing_days": int(et0.isna().sum()),
        }

    taw_max = max(20.0, float(rooting_depth_m) * float(available_water_capacity_mm_m))
    dr = float(np.clip(initial_depletion_fraction, 0.0, 1.0)) * taw_max

    daily_rows = []
    stage_totals = {
        s: {"days": 0, "rain_mm": 0.0, "effective_rain_mm": 0.0, "et0_mm": 0.0, "etc_mm": 0.0, "etc_adj_mm": 0.0, "stress_days": 0}
        for s in ("initial", "development", "mid_season", "late_season")
    }

    longest_stress_spell = 0
    current_stress_spell = 0

    for day_idx, (stamp, p_val, et0_val, kc_val, stage) in enumerate(
        zip(season_frame.index, rain.to_numpy(), et0.to_numpy(), kc_arr, stages)
    ):
        # Progressive root growth from 30% to 100% of max rooting depth across initial + development stages
        root_progress = min(1.0, 0.30 + 0.70 * ((day_idx + 1) / max(1, int(0.46 * n_days))))
        taw = taw_max * root_progress
        etc = float(kc_val * et0_val)
        # Adjust depletion fraction p for atmospheric demand (FAO-56 Table 22 note: p_adj = p + 0.04*(5 - ETc))
        p_adj = float(np.clip(depletion_fraction_p + 0.04 * (5.0 - etc), 0.10, 0.80))
        raw = p_adj * taw

        # Daily runoff / effective rainfall estimate
        if p_val <= 0.0:
            runoff = 0.0
        elif effective_rain_method == "fao_scs_daily":
            # Conservative daily surface runoff increases when root zone is near field capacity and rain > 20 mm
            wetness = max(0.0, 1.0 - (dr / max(taw, 1.0)))
            runoff = max(0.0, (p_val - 20.0) * (0.15 + 0.25 * wetness)) if p_val > 20.0 else 0.0
        else:
            runoff = 0.0
        peff = max(0.0, float(p_val - runoff))

        if is_paddy:
            # Bunded paddy field includes daily seepage/percolation demand
            perc_need = float(paddy_percolation_mm_day)
            water_need = etc + perc_need
            net_flux = peff - water_need
            dr = float(np.clip(dr - net_flux, 0.0, taw))
        else:
            # Unsaturated root-zone water balance before stress
            dr_pre = max(0.0, dr - peff)
            if dr_pre > raw and taw > raw:
                ks = float(np.clip((taw - dr_pre) / (taw - raw), 0.0, 1.0))
            else:
                ks = 1.0
            etc_adj = ks * etc
            deep_perc = max(0.0, peff - dr - etc_adj)
            dr = float(np.clip(dr - peff + etc_adj + deep_perc, 0.0, taw))
            perc_need = deep_perc

        if is_paddy:
            ks = 1.0 if dr <= raw else float(np.clip((taw - dr) / max(taw - raw, 1.0), 0.0, 1.0))
            etc_adj = ks * etc

        stressed = ks < 0.85
        current_stress_spell = (current_stress_spell + 1) if stressed else 0
        longest_stress_spell = max(longest_stress_spell, current_stress_spell)

        st = stage_totals[stage]
        st["days"] += 1
        st["rain_mm"] += float(p_val)
        st["effective_rain_mm"] += peff
        st["et0_mm"] += float(et0_val)
        st["etc_mm"] += etc
        st["etc_adj_mm"] += etc_adj
        st["stress_days"] += int(stressed)

        daily_rows.append(
            {
                "date": stamp,
                "stage": stage,
                "rain_mm": float(p_val),
                "effective_rain_mm": peff,
                "et0_mm": float(et0_val),
                "kc": float(kc_val),
                "etc_mm": etc,
                "ks": ks,
                "etc_adj_mm": etc_adj,
                "depletion_mm": dr,
                "taw_mm": taw,
                "raw_mm": raw,
            }
        )

    daily_df = pd.DataFrame(daily_rows).set_index("date")
    total_rain = float(daily_df["rain_mm"].sum())
    total_peff = float(daily_df["effective_rain_mm"].sum())
    total_et0 = float(daily_df["et0_mm"].sum())
    total_etc = float(daily_df["etc_mm"].sum())
    total_etc_adj = float(daily_df["etc_adj_mm"].sum())
    paddy_extra = float(paddy_land_prep_mm + n_days * paddy_percolation_mm_day) if is_paddy else 0.0
    total_crop_demand = total_etc + paddy_extra
    net_irrigation_req = max(0.0, total_crop_demand - total_peff)
    pm_days = int((et_df["et0_method"] == "fao56_penman_monteith").sum())
    et0_method_used = (
        "fao56_penman_monteith"
        if pm_days == n_days
        else ("fao56_hargreaves" if pm_days == 0 else "mixed_pm_hargreaves")
    )

    return {
        "status": "complete",
        "valid": True,
        "days": n_days,
        "et0_method": et0_method_used,
        "rain_total_mm": round(total_rain, 2),
        "effective_rain_mm": round(total_peff, 2),
        "et0_total_mm": round(total_et0, 2),
        "etc_total_mm": round(total_etc, 2),
        "etc_adj_total_mm": round(total_etc_adj, 2),
        "paddy_additional_water_mm": round(paddy_extra, 2),
        "total_crop_water_need_mm": round(total_crop_demand, 2),
        "net_irrigation_requirement_mm": round(net_irrigation_req, 2),
        "rainfed_supply_ratio": round(total_peff / total_crop_demand, 3) if total_crop_demand > 0 else None,
        "mean_ks": round(float(daily_df["ks"].mean()), 3),
        "water_stress_days": int((daily_df["ks"] < 0.85).sum()),
        "longest_stress_spell_days": int(longest_stress_spell),
        "mid_season_stress_days": int(stage_totals["mid_season"]["stress_days"]),
        "stage_breakdown": {
            k: {
                "days": v["days"],
                "rain_mm": round(v["rain_mm"], 1),
                "effective_rain_mm": round(v["effective_rain_mm"], 1),
                "et0_mm": round(v["et0_mm"], 1),
                "etc_mm": round(v["etc_mm"], 1),
                "etc_adj_mm": round(v["etc_adj_mm"], 1),
                "stress_days": v["stress_days"],
            }
            for k, v in stage_totals.items()
        },
        "assumptions": {
            "kc_curve": [round(kc_ini, 2), round(kc_mid, 2), round(kc_end, 2)],
            "stage_fractions": list(stage_fractions),
            "rooting_depth_m": round(float(rooting_depth_m), 2),
            "depletion_fraction_p": round(float(depletion_fraction_p), 2),
            "available_water_capacity_mm_m": round(float(available_water_capacity_mm_m), 1),
            "is_paddy": bool(is_paddy),
        },
    }


def seasonal_water_balance_summary(
    frame: pd.DataFrame,
    window,
    *,
    latitude: float | None = None,
    elevation_m: float | None = None,
    kc_ini: float = 0.40,
    kc_mid: float = 1.10,
    kc_end: float = 0.65,
    stage_fractions: tuple[float, float, float, float] = DEFAULT_STAGE_FRACTIONS,
    rooting_depth_m: float = 1.0,
    depletion_fraction_p: float = 0.50,
    available_water_capacity_mm_m: float = 140.0,
    is_paddy: bool = False,
) -> dict:
    """Summarize FAO-56 crop water balance across all complete historical seasons in frame."""
    if frame.empty:
        return {"valid_seasons": 0, "status": "no_data"}

    lat = latitude if latitude is not None else frame.attrs.get("latitude")
    seasons = []
    for year in range(frame.index.min().year, frame.index.max().year + 1):
        try:
            start, end = window.dates(year)
        except ValueError:
            continue
        idx = pd.date_range(start, end)
        if idx[0] < frame.index.min() or idx[-1] > frame.index.max():
            continue
        part = frame.reindex(idx).copy()
        part.attrs.update(frame.attrs)
        sim = simulate_season_crop_water_balance(
            part,
            latitude=lat,
            elevation_m=elevation_m,
            kc_ini=kc_ini,
            kc_mid=kc_mid,
            kc_end=kc_end,
            stage_fractions=stage_fractions,
            rooting_depth_m=rooting_depth_m,
            depletion_fraction_p=depletion_fraction_p,
            available_water_capacity_mm_m=available_water_capacity_mm_m,
            is_paddy=is_paddy,
        )
        if sim.get("valid"):
            sim["year"] = year
            seasons.append(sim)

    if not seasons:
        return {"valid_seasons": 0, "status": "insufficient_complete_seasons"}

    s_df = pd.DataFrame(seasons)
    return {
        "status": "verified",
        "valid_seasons": int(len(s_df)),
        "et0_method": str(s_df["et0_method"].mode().iloc[0]),
        "rain_median_mm": round(float(s_df["rain_total_mm"].median()), 1),
        "effective_rain_median_mm": round(float(s_df["effective_rain_mm"].median()), 1),
        "et0_median_mm": round(float(s_df["et0_total_mm"].median()), 1),
        "etc_median_mm": round(float(s_df["etc_total_mm"].median()), 1),
        "total_crop_water_need_median_mm": round(float(s_df["total_crop_water_need_mm"].median()), 1),
        "net_irrigation_req_median_mm": round(float(s_df["net_irrigation_requirement_mm"].median()), 1),
        "net_irrigation_req_p75_mm": round(float(s_df["net_irrigation_requirement_mm"].quantile(0.75)), 1),
        "rainfed_supply_ratio_median": round(float(s_df["rainfed_supply_ratio"].median()), 2),
        "water_stress_days_median": round(float(s_df["water_stress_days"].median()), 1),
        "mid_season_stress_days_median": round(float(s_df["mid_season_stress_days"].median()), 1),
        "longest_stress_spell_max_days": int(s_df["longest_stress_spell_days"].max()),
        "assumptions": seasons[0]["assumptions"],
    }
