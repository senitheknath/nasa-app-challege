"""Coverage-aware historical summaries and FAO-56 agro-meteorological indices; no silent imputation."""
from dataclasses import dataclass
from datetime import date
import math
import numpy as np
import pandas as pd
from agroshift.science.climate.power import DataError


@dataclass(frozen=True)
class Window:
    start_month: int
    start_day: int
    end_month: int
    end_day: int

    def dates(self, year):
        crosses = (self.end_month, self.end_day) < (self.start_month, self.start_day)
        try:
            return date(year, self.start_month, self.start_day), date(year + int(crosses), self.end_month, self.end_day)
        except ValueError as exc:
            raise DataError("Use valid recurring month/day dates. Use February 28 instead of February 29.") from exc

    @property
    def label(self):
        a, b = self.dates(2023)
        return f"{a:%d %b} – {b:%d %b}" + (" (next year)" if b.year != a.year else "")


def dry_spell(rain):
    """Return longest known <1 mm run and whether it is only a lower bound."""
    longest = run = 0
    for value in rain:
        run = run + 1 if pd.notna(value) and value < 1 else 0
        longest = max(longest, run)
    return longest, bool(rain.isna().any())


def mean_daylength_hours(latitude: float, dates_index: pd.DatetimeIndex) -> float:
    """Compute astronomical photoperiod (daylength in hours) from latitude and day-of-year (FAO-56 Eq. 24-34)."""
    lat_rad = math.radians(float(latitude))
    doy = dates_index.day_of_year.to_numpy(dtype=float)
    decl = 0.409 * np.sin((2.0 * math.pi / 365.0) * doy - 1.39)
    cos_ws = np.clip(-np.tan(lat_rad) * np.tan(decl), -1.0, 1.0)
    ws = np.arccos(cos_ws)
    daylen = (24.0 / math.pi) * ws
    return float(np.mean(daylen))


def compute_daily_agromet_indices(part: pd.DataFrame) -> dict:
    """Derive FAO-56 VPD (kPa), Reference Evapotranspiration ET0 (mm), PAR, GDD10, Heat-Stress & Heavy-Rain days."""
    t_mean = part["T2M"]
    missing = pd.Series(np.nan, index=part.index)
    t_min = part.get("T2M_MIN", missing)
    t_max = part.get("T2M_MAX", missing)
    rh = part.get("RH2M", missing)
    sw = part.get("ALLSKY_SFC_SW_DWN", missing)
    rain = part["PRECTOTCORR"]
    # Tetens saturation vapor pressure (kPa) & VPD (FAO-56 Eq. 11-19)
    es_tmax = 0.6108 * np.exp((17.27 * t_max) / (t_max + 237.3))
    es_tmin = 0.6108 * np.exp((17.27 * t_min) / (t_min + 237.3))
    es = 0.5 * (es_tmax + es_tmin)
    ea = es * (rh / 100.0)
    vpd = np.maximum(0.0, es - ea)

    # FAO-56 equations 21–25 and 52. Convert extraterrestrial radiation from
    # MJ/m²/day to equivalent evaporated water depth before Hargreaves.
    latitude = part.attrs.get("latitude")
    et0_total = np.nan
    et0_pm_total = np.nan
    et0_method = "missing"
    if latitude is not None:
        phi = math.radians(latitude)
        angle = 2 * np.pi * part.index.day_of_year.to_numpy() / 365
        decl = 0.409 * np.sin(angle - 1.39)
        sunset = np.arccos(np.clip(-np.tan(phi) * np.tan(decl), -1, 1))
        radiation = (24*60/np.pi) * 0.0820 * (1+0.033*np.cos(angle)) * (
            sunset*np.sin(phi)*np.sin(decl) + np.cos(phi)*np.cos(decl)*np.sin(sunset))
        daily = (0.0023 * (t_mean+17.8) * (t_max-t_min).clip(lower=0).pow(0.5)
                 * (0.408*np.maximum(radiation,0))).clip(lower=0)
        et0_total = daily.sum(min_count=len(part)) if len(part) else np.nan
        if pd.notna(et0_total):
            et0_method = "fao56_hargreaves"
        if ("WS2M" in part or "WS10M" in part) and len(part):
            from agroshift.science.soil_water.water_balance import compute_fao56_penman_monteith_daily
            pm_df = compute_fao56_penman_monteith_daily(part, latitude=latitude)
            if pm_df["et0_pm_mm"].notna().all():
                et0_pm_total = float(pm_df["et0_pm_mm"].sum())
                et0_method = "fao56_penman_monteith"
    gdd10_daily = (t_mean - 10).clip(lower=0)
    solar_mean = float(sw.mean()) if sw.notna().any() else np.nan
    rh_mean = float(rh.mean()) if rh.notna().any() else np.nan
    vpd_mean = float(vpd.mean()) if vpd.notna().any() else np.nan
    gdd10_sum = float(gdd10_daily.sum(min_count=len(part))) if len(part) else np.nan
    heat_days = int((t_max > 35.0).sum()) if t_max.notna().all() else np.nan
    days_tmin_below_0c = int((t_min < 0).sum()) if t_min.notna().all() else np.nan
    days_rain_at_least_25mm = int((rain >= 25.0).sum()) if rain.notna().all() else np.nan
    days_rain_at_least_50mm = int((rain >= 50.0).sum()) if rain.notna().all() else np.nan

    return {
        "solar_mj_m2_day": solar_mean,
        "rh2m_pct": rh_mean,
        "vpd_kpa": vpd_mean,
        "et0_mm": et0_total,
        "et0_hargreaves_mm": et0_total,
        "et0_pm_mm": et0_pm_total,
        "et0_method": et0_method,
        "gdd_base10": gdd10_sum,
        "days_tmax_over_35c": heat_days,
        "days_tmin_below_0c": days_tmin_below_0c,
        "days_rain_at_least_25mm": days_rain_at_least_25mm,
        "days_rain_at_least_50mm": days_rain_at_least_50mm,
    }


def aggregate(frame, frequency="MS"):
    rows = []
    for stamp, part in frame.resample(frequency):
        expected = len(pd.date_range(stamp, stamp + pd.offsets.MonthEnd(0))) if frequency == "MS" else (366 if stamp.is_leap_year else 365)
        rain_count = part.PRECTOTCORR.count()
        temp_count = part.T2M.count()
        agromet = compute_daily_agromet_indices(part)
        rain_val = part.PRECTOTCORR.sum() if rain_count == expected else np.nan
        rows.append(
            dict(
                date=stamp,
                rainfall_mm=rain_val,
                observed_rainfall_mm=part.PRECTOTCORR.sum(min_count=1),
                rain_coverage=rain_count / expected,
                temperature_c=part.T2M.mean() if temp_count / expected >= 0.9 else np.nan,
                temperature_coverage=temp_count / expected,
                maximum_c=part.T2M_MAX.max(),
                minimum_c=part.T2M_MIN.min(),
                solar_mj_m2_day=agromet["solar_mj_m2_day"],
                rh2m_pct=agromet["rh2m_pct"],
                vpd_kpa=agromet["vpd_kpa"],
                et0_mm=agromet["et0_mm"] if len(part)==expected else np.nan,
                gdd_base10=agromet["gdd_base10"] if len(part)==expected else np.nan,
            )
        )
    return pd.DataFrame(rows).set_index("date")


def season_samples(frame, window, rain_factor=1.0, temp_delta=0.0):
    if not 0 <= rain_factor <= 3 or not -10 <= temp_delta <= 10:
        raise DataError("Scenario changes exceed supported exploratory bounds.")
    rows = []
    for year in range(frame.index.min().year, frame.index.max().year + 1):
        try:
            start, end = window.dates(year)
        except ValueError:
            continue
        index = pd.date_range(start, end)
        if index[0] < frame.index.min() or index[-1] > frame.index.max():
            continue
        part = frame.reindex(index).copy()
        part["PRECTOTCORR"] *= rain_factor
        part[["T2M", "T2M_MIN", "T2M_MAX"]] += temp_delta
        rain = part.PRECTOTCORR
        cdd, partial = dry_spell(rain)
        agromet = compute_daily_agromet_indices(part)
        rain_sum = float(rain.sum()) if not partial else np.nan
        et0_val = agromet["et0_mm"]
        aridity = (rain_sum / et0_val) if (pd.notna(rain_sum) and pd.notna(et0_val) and et0_val > 0) else np.nan
        w_bal = (rain_sum - et0_val) if (pd.notna(rain_sum) and pd.notna(et0_val)) else np.nan
        rows.append(
            dict(
                year=year,
                days=len(part),
                rain_coverage=float(rain.notna().mean()),
                temp_coverage=float(part.T2M.notna().mean()),
                rainfall_mm=rain_sum,
                temperature_c=float(part.T2M.mean()) if part.T2M.notna().mean() >= 0.9 else np.nan,
                maximum_c=part.T2M_MAX.max(),
                minimum_c=part.T2M_MIN.min(),
                dry_spell_days=cdd,
                dry_spell_is_lower_bound=partial,
                solar_mj_m2_day=agromet["solar_mj_m2_day"],
                rh2m_pct=agromet["rh2m_pct"],
                vpd_kpa=agromet["vpd_kpa"],
                et0_mm=et0_val,
                aridity_index=aridity,
                water_balance_mm=w_bal,
                gdd_base10=agromet["gdd_base10"],
                days_tmax_over_35c=agromet["days_tmax_over_35c"],
                days_tmin_below_0c=agromet["days_tmin_below_0c"],
                days_rain_at_least_25mm=agromet["days_rain_at_least_25mm"],
            )
        )
    return pd.DataFrame(rows)


def seasonal_summary(samples):
    if samples.empty:
        return dict(valid_seasons=0)
    complete = samples.dropna(subset=["rainfall_mm", "temperature_c"])
    if complete.empty:
        return dict(valid_seasons=0)
    rain = complete.rainfall_mm
    return dict(
        valid_seasons=len(complete),
        rainfall_median_mm=float(rain.median()),
        rainfall_p25_mm=float(rain.quantile(0.25)),
        rainfall_p75_mm=float(rain.quantile(0.75)),
        rainfall_cv=float(rain.std(ddof=1) / rain.mean()) if len(rain) > 1 and rain.mean() > 0 else None,
        temperature_mean_c=float(complete.temperature_c.mean()),
        longest_dry_spell_days=int(complete.dry_spell_days.max()),
        median_dry_spell_days=float(complete.dry_spell_days.median()),
        temperature_max_c=float(complete.maximum_c.max()),
        temperature_min_c=float(complete.minimum_c.min()),
        solar_mean_mj=float(complete["solar_mj_m2_day"].mean()) if "solar_mj_m2_day" in complete else np.nan,
        rh2m_mean_pct=float(complete["rh2m_pct"].mean()) if "rh2m_pct" in complete else np.nan,
        vpd_mean_kpa=float(complete["vpd_kpa"].mean()) if "vpd_kpa" in complete else np.nan,
        et0_median_mm=float(complete["et0_mm"].median()) if "et0_mm" in complete else np.nan,
        aridity_index_median=float(complete["aridity_index"].median()) if "aridity_index" in complete else np.nan,
        water_balance_median_mm=float(complete["water_balance_mm"].median()) if "water_balance_mm" in complete else np.nan,
        gdd10_median=float(complete["gdd_base10"].median()) if "gdd_base10" in complete else np.nan,
        days_tmax_over_35c_median=float(complete["days_tmax_over_35c"].median()) if "days_tmax_over_35c" in complete else np.nan,
        days_rain_at_least_25mm_median=float(complete["days_rain_at_least_25mm"].median()) if "days_rain_at_least_25mm" in complete else np.nan,
    )


def classify_anomalies(samples):
    """Classify historical seasonal samples by standardized rainfall z-score (descriptive only, not a forecast)."""
    if samples.empty:
        return samples.copy()
    out = samples.copy()
    valid = out["rainfall_mm"].notna() & out["temperature_c"].notna()
    if valid.sum() < 3:
        out["rainfall_z"] = np.nan
        out["temp_anomaly_c"] = np.nan
        out["regime"] = np.where(valid, "Insufficient baseline (<3 seasons)", "Incomplete coverage")
        return out
    rain_mean = float(out.loc[valid, "rainfall_mm"].mean())
    rain_std = float(out.loc[valid, "rainfall_mm"].std(ddof=1))
    temp_mean = float(out.loc[valid, "temperature_c"].mean())
    out["rainfall_z"] = (out["rainfall_mm"] - rain_mean) / rain_std if rain_std > 0 else 0.0
    out.loc[~valid, "rainfall_z"] = np.nan
    out["temp_anomaly_c"] = out["temperature_c"] - temp_mean
    out.loc[~valid, "temp_anomaly_c"] = np.nan
    regimes = []
    for is_ok, z in zip(valid, out["rainfall_z"]):
        if not is_ok or pd.isna(z):
            regimes.append("Incomplete coverage")
        elif z < -1.0:
            regimes.append("Dry anomaly (z < -1.0)")
        elif z > 1.0:
            regimes.append("Wet anomaly (z > +1.0)")
        else:
            regimes.append("Typical range (-1.0 ≤ z ≤ +1.0)")
    out["regime"] = regimes
    return out
