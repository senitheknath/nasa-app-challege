"""Isolated FAO Paper 66 / AquaCrop water-driven biomass and canopy simulation prototype (simulation=True)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from agroshift.science.soil_water.water_balance import compute_fao56_penman_monteith_daily


AQUACROP_CROP_DEFAULTS: dict[str, dict] = {
    "maize": {"photosynthesis": "C4", "wp_star_g_m2": 33.7, "hi0": 0.48, "kcb_max": 1.05, "cc0": 0.015, "ccx": 0.96, "ky": 1.25, "root_depth_m": 1.2, "p_upper": 0.55},
    "sorghum": {"photosynthesis": "C4", "wp_star_g_m2": 32.0, "hi0": 0.45, "kcb_max": 1.00, "cc0": 0.015, "ccx": 0.90, "ky": 0.90, "root_depth_m": 1.4, "p_upper": 0.55},
    "pearl_millet": {"photosynthesis": "C4", "wp_star_g_m2": 30.0, "hi0": 0.35, "kcb_max": 0.95, "cc0": 0.015, "ccx": 0.85, "ky": 0.85, "root_depth_m": 1.4, "p_upper": 0.60},
    "wheat": {"photosynthesis": "C3", "wp_star_g_m2": 15.0, "hi0": 0.45, "kcb_max": 1.10, "cc0": 0.040, "ccx": 0.94, "ky": 1.05, "root_depth_m": 1.2, "p_upper": 0.55},
    "rice": {"photosynthesis": "C3", "wp_star_g_m2": 19.0, "hi0": 0.45, "kcb_max": 1.10, "cc0": 0.040, "ccx": 0.95, "ky": 1.10, "root_depth_m": 0.6, "p_upper": 0.20},
    "soybean": {"photosynthesis": "C3_legume", "wp_star_g_m2": 15.0, "hi0": 0.40, "kcb_max": 1.10, "cc0": 0.025, "ccx": 0.95, "ky": 0.85, "root_depth_m": 1.0, "p_upper": 0.50},
    "groundnut": {"photosynthesis": "C3_legume", "wp_star_g_m2": 14.0, "hi0": 0.38, "kcb_max": 1.05, "cc0": 0.025, "ccx": 0.90, "ky": 0.70, "root_depth_m": 0.8, "p_upper": 0.50},
    "potato": {"photosynthesis": "C3_tuber", "wp_star_g_m2": 18.0, "hi0": 0.75, "kcb_max": 1.10, "cc0": 0.020, "ccx": 0.92, "ky": 1.10, "root_depth_m": 0.5, "p_upper": 0.35},
    "sunflower": {"photosynthesis": "C3_oilseed", "wp_star_g_m2": 18.0, "hi0": 0.35, "kcb_max": 1.10, "cc0": 0.020, "ccx": 0.92, "ky": 0.95, "root_depth_m": 1.3, "p_upper": 0.45},
    "cotton": {"photosynthesis": "C3", "wp_star_g_m2": 15.0, "hi0": 0.35, "kcb_max": 1.10, "cc0": 0.015, "ccx": 0.92, "ky": 0.85, "root_depth_m": 1.4, "p_upper": 0.65},
}


def run_aquacrop_water_driven_prototype(
    season_frame: pd.DataFrame,
    crop_id: str,
    *,
    latitude: float | None = None,
    available_water_capacity_mm_m: float = 140.0,
    seasonal_irrigation_mm: float = 0.0,
) -> dict:
    """Run an isolated FAO Paper 66 / AquaCrop water-driven daily canopy and transpiration simulation.

    CRITICAL BOUNDARY: This prototype is strictly isolated from primary screening (`find_options`).
    All outputs carry `simulation=True` and `data_category="hypothetical_simulation"`.
    """
    if crop_id not in AQUACROP_CROP_DEFAULTS:
        return {
            "status": "unsupported_crop",
            "crop_id": crop_id,
            "simulation": True,
            "data_category": "hypothetical_simulation",
            "calibrated_to_farm": False,
        }
    if season_frame.empty or season_frame["PRECTOTCORR"].isna().any() or season_frame["T2M"].isna().any():
        return {
            "status": "incomplete_weather_coverage",
            "crop_id": crop_id,
            "simulation": True,
            "data_category": "hypothetical_simulation",
            "calibrated_to_farm": False,
        }

    params = AQUACROP_CROP_DEFAULTS[crop_id]
    lat = latitude if latitude is not None else season_frame.attrs.get("latitude")
    et_df = compute_fao56_penman_monteith_daily(season_frame, latitude=lat)
    et0 = et_df["et0_mm"].to_numpy(dtype=float)
    rain = season_frame["PRECTOTCORR"].to_numpy(dtype=float)
    n_days = len(season_frame)

    taw = max(30.0, float(params["root_depth_m"]) * float(available_water_capacity_mm_m))
    raw_exp = float(params["p_upper"]) * 0.70 * taw  # Canopy expansion stress threshold (more sensitive)
    raw_sto = float(params["p_upper"]) * taw  # Stomatal closure threshold

    dr = 0.20 * taw
    irr_per_day = float(seasonal_irrigation_mm) / max(n_days, 1)

    cc_series = []
    tr_series = []
    evap_series = []
    ks_sto_series = []
    norm_tr_sum = 0.0

    for day_idx, (p_val, et0_val) in enumerate(zip(rain, et0)):
        progress = (day_idx + 1) / max(n_days, 1)
        # Logistic green canopy cover curve before senescence
        if progress <= 0.15:
            cc_pot = params["cc0"] + (0.25 - params["cc0"]) * (progress / 0.15)
        elif progress <= 0.50:
            cc_pot = 0.25 + (params["ccx"] - 0.25) * ((progress - 0.15) / 0.35)
        elif progress <= 0.80:
            cc_pot = params["ccx"]
        else:
            cc_pot = params["ccx"] * max(0.15, 1.0 - 0.80 * ((progress - 0.80) / 0.20))

        water_in = max(0.0, p_val * 0.85) + irr_per_day
        dr_pre = max(0.0, dr - water_in)

        ks_exp = 1.0 if dr_pre <= raw_exp else float(np.clip((taw - dr_pre) / max(taw - raw_exp, 1.0), 0.0, 1.0))
        ks_sto = 1.0 if dr_pre <= raw_sto else float(np.clip((taw - dr_pre) / max(taw - raw_sto, 1.0), 0.0, 1.0))

        cc_actual = cc_pot * (0.65 + 0.35 * ks_exp)
        tr = ks_sto * cc_actual * params["kcb_max"] * et0_val
        ke = max(0.0, (1.0 - cc_actual) * 0.45 * (1.0 - min(dr_pre / taw, 1.0)))
        evap = ke * et0_val
        etc_adj = tr + evap
        deep_perc = max(0.0, water_in - dr - etc_adj)
        dr = float(np.clip(dr - water_in + etc_adj + deep_perc, 0.0, taw))

        if et0_val > 0.1:
            norm_tr_sum += tr / et0_val

        cc_series.append(cc_actual)
        tr_series.append(tr)
        evap_series.append(evap)
        ks_sto_series.append(ks_sto)

    # FAO Paper 66 Eq. 4: B = WP* * sum(Tr / ET0) (g/m² -> t/ha via * 0.01)
    simulated_biomass_t_ha = round(float(params["wp_star_g_m2"] * norm_tr_sum * 0.01), 2)
    potential_tr = float(np.sum(np.asarray(cc_series) * params["kcb_max"] * et0))
    actual_tr = float(np.sum(tr_series))
    rel_et_deficit = max(0.0, 1.0 - (actual_tr / max(potential_tr, 1.0)))
    relative_water_limited_yield_index = round(float(np.clip(1.0 - params["ky"] * rel_et_deficit, 0.0, 1.0)), 3)

    return {
        "status": "simulated",
        "crop_id": crop_id,
        "simulation": True,
        "data_category": "hypothetical_simulation",
        "calibrated_to_farm": False,
        "used_in_primary_screening": False,
        "days": n_days,
        "photosynthetic_pathway": params["photosynthesis"],
        "transpiration_total_mm": round(actual_tr, 1),
        "soil_evaporation_total_mm": round(float(np.sum(evap_series)), 1),
        "mean_canopy_cover_fraction": round(float(np.mean(cc_series)), 3),
        "mean_stomatal_ks": round(float(np.mean(ks_sto_series)), 3),
        "relative_water_limited_index": relative_water_limited_yield_index,
        "illustrative_dry_biomass_index_t_ha": simulated_biomass_t_ha,
        "unmeasured_assumed_parameters": {
            "wp_star_g_m2": params["wp_star_g_m2"],
            "hi0_reference": params["hi0"],
            "kcb_max": params["kcb_max"],
            "ky_yield_response_factor": params["ky"],
            "root_depth_m": params["root_depth_m"],
            "available_water_capacity_mm_m": available_water_capacity_mm_m,
            "seasonal_irrigation_mm": seasonal_irrigation_mm,
        },
        "scientific_disclaimer": (
            "EXPLORATORY SIMULATION ONLY (FAO Paper 66 / AquaCrop water-driven formulation). "
            "Uses generic published FAO parameters without site-specific cultivar calibration, "
            "soil horizon hydraulic measurements, nutrient balance, or pest dynamics. "
            "Never interpret as an expected farm yield."
        ),
    }
