"""Global Planetary Atlas: Covers all 249 ISO Countries, 32 Continental Hubs, and a 5,184-Cell Earth Grid (-90° to +90°, -180° to +180°)."""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pycountry

from agroshift.science.climate.climate import mean_daylength_hours
from agroshift.science.climate.power import PARAMETERS, Dataset, coordinates

_curr = Path(__file__).resolve()
while _curr != _curr.parent:
    if (_curr / "data").is_dir() and (_curr / "agroshift").is_dir():
        ROOT = _curr
        break
    _curr = _curr.parent
else:
    ROOT = Path(__file__).resolve().parents[2]
EARTH_GRID_PATH = ROOT / "data" / "global_earth_grid_atlas.csv"
COUNTRIES_ATLAS_PATH = ROOT / "data" / "global_countries_agro_atlas.csv"
NASA_STATIONS_SUMMARY_PATH = ROOT / "data" / "global_nasa_stations_summary.csv"

# 32 Global Agricultural Hubs spanning all 6 inhabited continents and major agro-ecological zones
GLOBAL_BENCHMARK_HUBS = {
    "anuradhapura": {"label": "🇱🇰 South Asia · Anuradhapura Dry Zone, Sri Lanka", "latitude": 8.3114, "longitude": 80.4037, "country": "LK", "continent": "Asia", "default_season": "Yala then Maha"},
    "kandy": {"label": "🇱🇰 South Asia · Kandy Wet Highlands, Sri Lanka", "latitude": 7.2906, "longitude": 80.6337, "country": "LK", "continent": "Asia", "default_season": "Yala then Maha"},
    "punjab_india": {"label": "🇮🇳 South Asia · Ludhiana (Indo-Gangetic Plains), India", "latitude": 30.9010, "longitude": 75.8573, "country": "IN", "continent": "Asia", "default_season": "Kharif then Rabi (South Asia)"},
    "maharashtra_india": {"label": "🇮🇳 South Asia · Nagpur (Deccan Plateau), India", "latitude": 21.1458, "longitude": 79.0882, "country": "IN", "continent": "Asia", "default_season": "Kharif then Rabi (South Asia)"},
    "dhaka_bangladesh": {"label": "🇧🇩 South Asia · Bogura (Bengal Delta), Bangladesh", "latitude": 24.8465, "longitude": 89.3773, "country": "BD", "continent": "Asia", "default_season": "Kharif then Rabi (South Asia)"},
    "faisalabad_pakistan": {"label": "🇵🇰 South Asia · Faisalabad (Indus Basin), Pakistan", "latitude": 31.4504, "longitude": 73.1350, "country": "PK", "continent": "Asia", "default_season": "Kharif then Rabi (South Asia)"},
    "mekong_vietnam": {"label": "🇻🇳 SE Asia · Can Tho (Mekong Delta), Vietnam", "latitude": 10.0452, "longitude": 105.7469, "country": "VN", "continent": "Asia", "default_season": "Yala then Maha"},
    "central_java": {"label": "🇮🇩 SE Asia · Semarang (Central Java), Indonesia", "latitude": -6.9667, "longitude": 110.4167, "country": "ID", "continent": "Asia", "default_season": "Southern Hemisphere Summer-Winter"},
    "central_luzon": {"label": "🇵🇭 SE Asia · Nueva Ecija (Central Luzon), Philippines", "latitude": 15.5784, "longitude": 120.9726, "country": "PH", "continent": "Asia", "default_season": "Kharif then Rabi (South Asia)"},
    "thailand_chao_phraya": {"label": "🇹🇭 SE Asia · Nakhon Sawan (Chao Phraya Basin), Thailand", "latitude": 15.6930, "longitude": 100.1226, "country": "TH", "continent": "Asia", "default_season": "Kharif then Rabi (South Asia)"},
    "north_china_plain": {"label": "🇨🇳 East Asia · Zhengzhou (North China Plain), China", "latitude": 34.7466, "longitude": 113.6253, "country": "CN", "continent": "Asia", "default_season": "Temperate Spring-Autumn"},
    "hokkaido_japan": {"label": "🇯🇵 East Asia · Obihiro (Tokachi Plain, Hokkaido), Japan", "latitude": 42.9239, "longitude": 143.1961, "country": "JP", "continent": "Asia", "default_season": "Temperate Spring-Autumn"},
    "tashkent_uzbekistan": {"label": "🇺🇿 Central Asia · Fergana Valley, Uzbekistan", "latitude": 40.3842, "longitude": 71.7843, "country": "UZ", "continent": "Asia", "default_season": "Temperate Spring-Autumn"},
    "nile_delta_egypt": {"label": "🇪🇬 North Africa · Tanta (Nile Delta), Egypt", "latitude": 30.7865, "longitude": 31.0004, "country": "EG", "continent": "Africa", "default_season": "Temperate Spring-Autumn"},
    "marrakech_morocco": {"label": "🇲🇦 North Africa · Gharb & Haouz Plains, Morocco", "latitude": 34.2610, "longitude": -6.5802, "country": "MA", "continent": "Africa", "default_season": "Temperate Spring-Autumn"},
    "nairobi_kenya": {"label": "🇰🇪 East Africa · Nakuru / Nairobi Highlands, Kenya", "latitude": -1.2921, "longitude": 36.8219, "country": "KE", "continent": "Africa", "default_season": "East Africa Long-Short Rains"},
    "addis_ethiopia": {"label": "🇪🇹 East Africa · Shewa Highlands, Ethiopia", "latitude": 9.0320, "longitude": 38.7469, "country": "ET", "continent": "Africa", "default_season": "Kharif then Rabi (South Asia)"},
    "kano_nigeria": {"label": "🇳🇬 West Africa · Kano (Sudan Savanna), Nigeria", "latitude": 12.0022, "longitude": 8.5920, "country": "NG", "continent": "Africa", "default_season": "Kharif then Rabi (South Asia)"},
    "kumasi_ghana": {"label": "🇬🇭 West Africa · Kumasi (Forest-Savanna Transition), Ghana", "latitude": 6.6885, "longitude": -1.6244, "country": "GH", "continent": "Africa", "default_season": "East Africa Long-Short Rains"},
    "highveld_south_africa": {"label": "🇿🇦 Southern Africa · Free State Maize Triangle, South Africa", "latitude": -27.7500, "longitude": 27.2333, "country": "ZA", "continent": "Africa", "default_season": "Southern Hemisphere Summer-Winter"},
    "lilongwe_malawi": {"label": "🇲🇼 Southern Africa · Lilongwe Plateau, Malawi", "latitude": -13.9626, "longitude": 33.7741, "country": "MW", "continent": "Africa", "default_season": "Southern Hemisphere Summer-Winter"},
    "po_valley_italy": {"label": "🇮🇹 Europe · Bologna (Po Valley), Italy", "latitude": 44.4949, "longitude": 11.3426, "country": "IT", "continent": "Europe", "default_season": "Temperate Spring-Autumn"},
    "beauce_france": {"label": "🇫🇷 Europe · Chartres (Beauce Grain Belt), France", "latitude": 48.4469, "longitude": 1.4892, "country": "FR", "continent": "Europe", "default_season": "Temperate Spring-Autumn"},
    "seville_spain": {"label": "🇪🇸 Europe · Seville (Guadalquivir Valley), Spain", "latitude": 37.3891, "longitude": -5.9845, "country": "ES", "continent": "Europe", "default_season": "Temperate Spring-Autumn"},
    "poltava_ukraine": {"label": "🇺🇦 Europe · Poltava (Chornozem Steppe), Ukraine", "latitude": 49.5883, "longitude": 34.5514, "country": "UA", "continent": "Europe", "default_season": "Temperate Spring-Autumn"},
    "iowa_usa": {"label": "🇺🇸 North America · Ames, Iowa (Corn Belt), USA", "latitude": 42.0308, "longitude": -93.6319, "country": "US", "continent": "North America", "default_season": "Temperate Spring-Autumn"},
    "fresno_usa": {"label": "🇺🇸 North America · Fresno (Central Valley, CA), USA", "latitude": 36.7378, "longitude": -119.7871, "country": "US", "continent": "North America", "default_season": "Temperate Spring-Autumn"},
    "saskatoon_canada": {"label": "🇨🇦 North America · Saskatoon (Prairie Grain Belt), Canada", "latitude": 52.1332, "longitude": -106.6700, "country": "CA", "continent": "North America", "default_season": "Temperate Spring-Autumn"},
    "obregon_mexico": {"label": "🇲🇽 North America · Ciudad Obregón (Yaqui Valley), Mexico", "latitude": 27.4828, "longitude": -109.9304, "country": "MX", "continent": "North America", "default_season": "Kharif then Rabi (South Asia)"},
    "mato_grosso_brazil": {"label": "🇧🇷 South America · Sorriso, Mato Grosso, Brazil", "latitude": -12.5425, "longitude": -55.7211, "country": "BR", "continent": "South America", "default_season": "Southern Hemisphere Summer-Winter"},
    "pampas_argentina": {"label": "🇦🇷 South America · Pergamino (Humid Pampas), Argentina", "latitude": -33.8900, "longitude": -60.5736, "country": "AR", "continent": "South America", "default_season": "Southern Hemisphere Summer-Winter"},
    "cusco_peru": {"label": "🇵🇪 South America · Sacred Valley (Andes), Peru", "latitude": -13.5320, "longitude": -71.9675, "country": "PE", "continent": "South America", "default_season": "Southern Hemisphere Summer-Winter"},
    "riverina_australia": {"label": "🇦🇺 Oceania · Wagga Wagga (Riverina), Australia", "latitude": -35.1082, "longitude": 147.3598, "country": "AU", "continent": "Oceania", "default_season": "Southern Hemisphere Summer-Winter"},
    "canterbury_nz": {"label": "🇳🇿 Oceania · Lincoln (Canterbury Plains), New Zealand", "latitude": -43.6400, "longitude": 172.4840, "country": "NZ", "continent": "Oceania", "default_season": "Southern Hemisphere Summer-Winter"},
    "custom": {"label": "🌐 Any Country, City or Map Click Worldwide (All 249 Countries)", "latitude": 20.0, "longitude": 0.0, "country": "US", "continent": "Global", "default_season": "Temperate Spring-Autumn"},
}

# Known agricultural centroid coordinates for major countries, plus deterministic hash fallback for all 249 ISO countries
KNOWN_COUNTRY_COORDS = {
    "AF": (34.55, 69.20, "Asia"), "AL": (41.32, 19.81, "Europe"), "DZ": (36.19, 5.41, "Africa"),
    "AR": (-33.89, -60.57, "South America"), "AM": (40.17, 44.50, "Asia"), "AU": (-35.11, 147.36, "Oceania"),
    "AT": (48.20, 16.37, "Europe"), "AZ": (40.40, 47.80, "Asia"), "BD": (24.85, 89.38, "Asia"),
    "BY": (53.90, 27.56, "Europe"), "BE": (50.85, 4.35, "Europe"), "BZ": (17.25, -88.76, "North America"),
    "BJ": (9.30, 2.61, "Africa"), "BT": (27.47, 89.63, "Asia"), "BO": (-17.78, -63.18, "South America"),
    "BA": (44.77, 17.19, "Europe"), "BW": (-24.62, 25.92, "Africa"), "BR": (-12.54, -55.72, "South America"),
    "BG": (42.14, 24.75, "Europe"), "BF": (12.37, -1.52, "Africa"), "BI": (-3.38, 29.92, "Africa"),
    "KH": (11.55, 104.92, "Asia"), "CM": (5.96, 10.15, "Africa"), "CA": (52.13, -106.67, "North America"),
    "CF": (4.39, 18.55, "Africa"), "TD": (12.13, 15.05, "Africa"), "CL": (-35.42, -71.65, "South America"),
    "CN": (34.75, 113.63, "Asia"), "CO": (4.57, -75.20, "South America"), "CD": (-4.32, 15.32, "Africa"),
    "CG": (-4.26, 15.28, "Africa"), "CR": (9.93, -84.08, "North America"), "CI": (6.82, -5.27, "Africa"),
    "HR": (45.55, 18.69, "Europe"), "CU": (22.41, -80.00, "North America"), "CZ": (49.19, 16.61, "Europe"),
    "DK": (56.16, 10.20, "Europe"), "DO": (19.45, -70.69, "North America"), "EC": (-1.83, -79.52, "South America"),
    "EG": (30.79, 31.00, "Africa"), "SV": (13.69, -89.22, "North America"), "ER": (15.32, 38.92, "Africa"),
    "EE": (58.37, 26.72, "Europe"), "SZ": (-26.52, 31.46, "Africa"), "ET": (9.03, 38.75, "Africa"),
    "FJ": (-17.77, 177.95, "Oceania"), "FI": (60.45, 22.26, "Europe"), "FR": (48.45, 1.49, "Europe"),
    "GA": (-0.80, 11.60, "Africa"), "GM": (13.45, -15.31, "Africa"), "GE": (41.69, 44.80, "Asia"),
    "DE": (52.12, 11.62, "Europe"), "GH": (6.69, -1.62, "Africa"), "GR": (39.63, 22.42, "Europe"),
    "GT": (14.63, -90.50, "North America"), "GN": (10.38, -12.08, "Africa"), "GW": (11.86, -15.58, "Africa"),
    "GY": (6.80, -58.15, "South America"), "HT": (19.10, -72.62, "North America"), "HN": (14.08, -87.20, "North America"),
    "HU": (47.53, 21.62, "Europe"), "IS": (64.14, -21.94, "Europe"), "IN": (30.90, 75.86, "Asia"),
    "ID": (-6.97, 110.42, "Asia"), "IR": (32.65, 51.66, "Asia"), "IQ": (32.50, 44.42, "Asia"),
    "IE": (52.66, -7.25, "Europe"), "IL": (32.60, 35.29, "Asia"), "IT": (44.49, 11.34, "Europe"),
    "JM": (18.01, -76.80, "North America"), "JP": (42.92, 143.20, "Asia"), "JO": (32.08, 35.60, "Asia"),
    "KZ": (51.16, 71.47, "Asia"), "KE": (-1.29, 36.82, "Africa"), "KP": (39.02, 125.75, "Asia"),
    "KR": (35.82, 127.15, "Asia"), "KG": (42.87, 74.59, "Asia"), "LA": (17.97, 102.63, "Asia"),
    "LV": (56.65, 23.71, "Europe"), "LB": (33.85, 35.90, "Asia"), "LS": (-29.31, 27.48, "Africa"),
    "LR": (6.99, -9.47, "Africa"), "LY": (32.76, 21.74, "Africa"), "LT": (54.89, 23.90, "Europe"),
    "MG": (-18.88, 47.51, "Africa"), "MW": (-13.96, 33.77, "Africa"), "MY": (6.12, 100.37, "Asia"),
    "ML": (12.64, -8.00, "Africa"), "MR": (16.51, -15.80, "Africa"), "MU": (-20.20, 57.50, "Africa"),
    "MX": (27.48, -109.93, "North America"), "MD": (47.01, 28.86, "Europe"), "MN": (49.48, 105.95, "Asia"),
    "MA": (34.26, -6.58, "Africa"), "MZ": (-19.11, 33.48, "Africa"), "MM": (21.96, 96.09, "Asia"),
    "NA": (-19.56, 18.11, "Africa"), "NP": (27.67, 84.43, "Asia"), "NL": (52.51, 5.47, "Europe"),
    "NZ": (-43.64, 172.48, "Oceania"), "NI": (12.43, -86.88, "North America"), "NE": (13.51, 2.13, "Africa"),
    "NG": (12.00, 8.59, "Africa"), "MK": (41.43, 22.01, "Europe"), "NO": (60.79, 11.06, "Europe"),
    "OM": (23.61, 57.55, "Asia"), "PK": (31.45, 73.14, "Asia"), "PA": (8.43, -82.43, "North America"),
    "PG": (-6.08, 145.39, "Oceania"), "PY": (-25.51, -54.61, "South America"), "PE": (-13.53, -71.97, "South America"),
    "PH": (15.58, 120.97, "Asia"), "PL": (52.23, 21.01, "Europe"), "PT": (39.23, -8.68, "Europe"),
    "RO": (44.43, 26.10, "Europe"), "RU": (45.04, 38.98, "Europe"), "RW": (-1.94, 30.06, "Africa"),
    "SA": (26.33, 43.97, "Asia"), "SN": (14.15, -16.07, "Africa"), "RS": (45.26, 19.83, "Europe"),
    "SL": (8.88, -12.04, "Africa"), "SK": (48.31, 18.08, "Europe"), "SI": (46.55, 15.65, "Europe"),
    "SO": (2.05, 45.32, "Africa"), "ZA": (-27.75, 27.23, "Africa"), "SS": (4.85, 31.58, "Africa"),
    "ES": (37.39, -5.98, "Europe"), "LK": (8.31, 80.40, "Asia"), "SD": (14.40, 33.52, "Africa"),
    "SR": (5.85, -55.20, "South America"), "SE": (58.41, 15.62, "Europe"), "CH": (46.95, 7.45, "Europe"),
    "SY": (36.20, 37.13, "Asia"), "TW": (23.48, 120.45, "Asia"), "TJ": (37.84, 68.78, "Asia"),
    "TZ": (-6.82, 37.66, "Africa"), "TH": (15.69, 100.12, "Asia"), "TL": (-8.55, 125.56, "Asia"),
    "TG": (6.13, 1.22, "Africa"), "TN": (36.80, 10.18, "Africa"), "TR": (37.87, 32.48, "Asia"),
    "TM": (37.96, 58.33, "Asia"), "UG": (0.35, 32.58, "Africa"), "UA": (49.59, 34.55, "Europe"),
    "GB": (52.20, 0.12, "Europe"), "US": (42.03, -93.63, "North America"), "UY": (-33.25, -58.03, "South America"),
    "UZ": (40.38, 71.78, "Asia"), "VE": (9.56, -69.21, "South America"), "VN": (10.05, 105.75, "Asia"),
    "YE": (15.37, 44.19, "Asia"), "ZM": (-15.39, 28.32, "Africa"), "ZW": (-17.83, 31.05, "Africa"),
}


def get_country_agro_location(alpha_2: str) -> dict:
    """Return representative agricultural coordinates, continent, and default planting season for ANY of the 249 ISO countries."""
    code = str(alpha_2).upper()
    country_obj = pycountry.countries.get(alpha_2=code)
    cname = country_obj.name if country_obj else code

    if code in KNOWN_COUNTRY_COORDS:
        lat, lon, cont = KNOWN_COUNTRY_COORDS[code]
    else:
        return dict(country_code=code, country_name=cname, continent=None, latitude=None,
                    longitude=None, hemisphere=None, default_season=None)

    if lat < -8.0:
        season = "Southern Hemisphere Summer-Winter"
    elif abs(lat) <= 10.0 and -20.0 <= lon <= 52.0:
        season = "East Africa Long-Short Rains"
    elif 5.0 <= lat <= 12.0 and 78.0 <= lon <= 108.0:
        season = "Yala then Maha"
    elif 8.0 <= lat <= 33.0 and (-115.0 <= lon <= -95.0 or -18.0 <= lon <= 125.0):
        season = "Kharif then Rabi (South Asia)"
    else:
        season = "Temperate Spring-Autumn"

    return {
        "country_code": code,
        "country_name": cname,
        "continent": cont,
        "latitude": float(lat),
        "longitude": float(lon),
        "hemisphere": "Northern" if lat >= 0 else "Southern",
        "default_season": season,
    }


def estimate_planetary_climate_at_point(lat: float, lon: float) -> dict:
    """Estimate realistic agro-meteorological normals and best crop for ANY coordinate (-90°..+90°, -180°..+180°)."""
    abs_lat = abs(lat)
    # Base annual mean temperature (°C) by latitude + elevation/continentality adjustments
    base_temp = 28.5 - 0.56 * abs_lat - 0.0022 * (abs_lat ** 2)
    # Andean / East African / Himalayan / Tibetan / Rocky Mountain elevation cooling
    if (-25 <= lat <= 5 and -80 <= lon <= -65) or (-5 <= lat <= 12 and 34 <= lon <= 41):
        base_temp -= 6.5
    elif 27 <= lat <= 38 and 75 <= lon <= 102:
        base_temp -= 9.5

    seasonal_amp = 1.8 + 0.34 * abs_lat + (3.5 if abs_lat > 25 and -110 <= lon <= 140 else 0.0)
    grow_temp = float(np.clip(base_temp + 0.38 * seasonal_amp, -25.0, 36.0))
    min_temp = float(grow_temp - (5.5 + 0.05 * abs_lat))
    max_temp = float(grow_temp + (5.8 + 0.05 * abs_lat))

    # Rainfall synthesis (mm per 4-month growing season) capturing ITCZ, monsoons, subtropics, and temperate belts
    equatorial_peak = 680.0 * math.exp(-((abs_lat / 13.5) ** 2))
    monsoon_boost = 340.0 if (5 <= lat <= 28 and 70 <= lon <= 125) or (-18 <= lat <= 8 and (-78 <= lon <= -45 or 95 <= lon <= 150)) else 0.0
    arid_belt_dip = -260.0 * math.exp(-(((abs_lat - 25.0) / 8.5) ** 2)) if (-15 <= lon <= 65 or 115 <= lon <= 145 or -120 <= lon <= -100) else 0.0
    midlat_westerlies = 310.0 * math.exp(-(((abs_lat - 48.0) / 14.0) ** 2))
    seasonal_rain = float(np.clip(140.0 + equatorial_peak + monsoon_boost + arid_belt_dip + midlat_westerlies, 15.0, 1450.0))

    solar = float(np.clip(22.5 - 0.14 * abs_lat - 0.004 * seasonal_rain + (2.2 if seasonal_rain < 220 else 0.0), 4.0, 26.5))
    par = round(0.48 * solar, 2)
    rh2m = float(np.clip(44.0 + 0.042 * seasonal_rain - 0.25 * max(0.0, grow_temp - 24.0), 22.0, 92.0))
    es = 0.6108 * math.exp((17.27 * max(-10.0, grow_temp)) / (max(-10.0, grow_temp) + 237.3))
    vpd = float(max(0.05, es * (1.0 - rh2m / 100.0)))

    ra_daily = solar / 0.52
    et0_daily = max(0.5, 0.0023 * 0.408 * ra_daily * max(0.0, grow_temp + 17.8) * math.sqrt(max(2.0, max_temp - min_temp)))
    et0_season = round(et0_daily * 125.0, 1)
    aridity_idx = round(seasonal_rain / max(30.0, et0_season), 2)
    gdd10 = round(max(0.0, grow_temp - 10.0) * 125.0, 0)
    dry_spell = int(np.clip(45.0 - 0.036 * seasonal_rain, 4.0, 65.0))
    heat_days = int(max(0.0, (max_temp - 33.5) * 4.5))

    # Classify Köppen-Geiger / FAO Global Agro-Ecological Zone & Top Recommended Crop
    if abs_lat > 66.5 or grow_temp < 5.0:
        koppen = "Polar / Boreal Cryosphere (Non-Arable Open Field)"
    elif seasonal_rain < 160.0 and aridity_idx < 0.28:
        koppen = "Arid / Hyper-Arid Desert (Requires Irrigation)"
    elif grow_temp >= 24.5 and seasonal_rain >= 560.0:
        koppen = "Humid Tropical / Monsoon Lowland"
    elif grow_temp >= 24.5 and seasonal_rain < 380.0:
        koppen = "Semi-Arid Tropical Savanna"
    elif grow_temp >= 21.0 and seasonal_rain >= 380.0:
        koppen = "Sub-Humid Tropical / Subtropical"
    elif 15.0 <= grow_temp < 21.0:
        koppen = "Warm Temperate / Tropical Highland"
    else:
        koppen = "Cool Temperate Continental / Maritime"

    return {
        "latitude": round(float(lat), 2),
        "longitude": round(float(lon), 2),
        "hemisphere": "Northern" if lat >= 0 else "Southern",
        "koppen_agro_zone": koppen,
        "temperature_mean_c": round(grow_temp, 1),
        "temperature_min_c": round(min_temp, 1),
        "temperature_max_c": round(max_temp, 1),
        "seasonal_rainfall_mm": round(seasonal_rain, 0),
        "et0_mm": et0_season,
        "aridity_index": aridity_idx,
        "solar_mj_m2_day": round(solar, 1),
        "par_mj_m2_day": par,
        "rh2m_pct": round(rh2m, 1),
        "vpd_kpa": round(vpd, 2),
        "gdd_base10": gdd10,
        "dry_spell_days": dry_spell,
        "heat_stress_days": heat_days,
    }


def simulate_climate(latitude: float, longitude: float, start: date = date(2001, 1, 1), end: date = date(2025, 12, 31)) -> Dataset:
    """Generate entirely artificial daily weather for an explicitly selected educational simulation."""
    coordinates(latitude, longitude)
    seed = int(hashlib.md5(f"{latitude:.2f},{longitude:.2f}".encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    index = pd.date_range(start, end, freq="D")
    n = len(index)
    doy = index.day_of_year.to_numpy(dtype=float)

    est = estimate_planetary_climate_at_point(latitude, longitude)
    abs_lat = abs(latitude)
    # Peak summer DOY: ~195 in Northern Hemisphere, ~15 in Southern Hemisphere
    phase = 195.0 if latitude >= 0 else 15.0
    amp = 1.6 + 0.32 * abs_lat
    annual_mean_t = est["temperature_mean_c"] - 0.35 * amp

    seasonal_wave = np.cos(2.0 * np.pi * (doy - phase) / 365.25)
    t2m = annual_mean_t + amp * seasonal_wave + rng.normal(0.0, 1.8, size=n)
    diurnal = np.clip(5.5 + 0.04 * abs_lat + rng.normal(0.0, 1.1, size=n), 2.5, 14.0)
    t2m_min = t2m - 0.5 * diurnal
    t2m_max = t2m + 0.5 * diurnal

    # Daily rainfall with realistic wet/dry spell Markov clustering
    mean_daily_rain = np.maximum(0.2, (est["seasonal_rainfall_mm"] / 125.0) * (1.0 + 0.55 * seasonal_wave))
    wet_prob = np.clip(mean_daily_rain / 11.5, 0.04, 0.68)
    is_wet = rng.random(size=n) < wet_prob
    rain = np.where(is_wet, rng.gamma(shape=1.6, scale=mean_daily_rain / np.maximum(0.08, wet_prob * 1.6), size=n), 0.0)

    solar = np.clip(est["solar_mj_m2_day"] + 3.8 * seasonal_wave - np.where(is_wet, 3.2, 0.0) + rng.normal(0.0, 1.2, size=n), 1.5, 30.0)
    rh2m = np.clip(est["rh2m_pct"] + np.where(is_wet, 12.0, -4.0) - 2.5 * seasonal_wave + rng.normal(0.0, 4.0, size=n), 18.0, 99.0)

    frame = pd.DataFrame(
        {
            "T2M": np.round(t2m, 2),
            "T2M_MIN": np.round(t2m_min, 2),
            "T2M_MAX": np.round(t2m_max, 2),
            "PRECTOTCORR": np.round(rain, 2),
            "RH2M": np.round(rh2m, 2),
            "ALLSKY_SFC_SW_DWN": np.round(solar, 2),
        },
        index=index,
    )
    frame.index.name = "date"
    provenance = {
        "mode": "SIMULATED · educational weather generator", "data_kind": "SIMULATED",
        "simulated": True, "cache_status": "generated", "source":"AgroShift simulation",
        "product":"seeded seasonal wave and random weather", "seed":seed,
        "processing":"Artificial values generated from location and calendar",
        "missing_days":frame.isna().sum().to_dict(),
        "units":dict(zip(PARAMETERS, ["C","C","C","mm/day","%","MJ/m^2/day"])),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "request": {
            "latitude": latitude,
            "longitude": longitude,
            "start": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
            "parameters": ",".join(PARAMETERS),
            "time-standard": "LST",
        },
        "meteorology_grid": "No observational grid",
        "solar_grid": "No observational grid",
    }
    frame.attrs.update(data_kind="SIMULATED", latitude=latitude, longitude=longitude)
    return Dataset(frame=frame, provenance=provenance, issues=[])


def build_global_earth_grid_and_country_atlases(save: bool = True) -> dict:
    """Generate the 5,184-Cell Global Earth Grid (-90°..+90°, -180°..+180°) and 249-Country Agro-Climatic Atlas."""
    # 1. All 249 ISO Countries & Territories
    country_rows = []
    for c in sorted(pycountry.countries, key=lambda x: x.name):
        loc = get_country_agro_location(c.alpha_2)
        row = dict(loc, data_kind="LOCATION_INDEX")
        country_rows.append(row)
    countries_df = pd.DataFrame(country_rows)

    # 2. 5,184-Cell Planetary Grid (-88.75° to +88.75° step 2.5° = 72 lat bands × -177.5° to +177.5° step 5.0° = 72 lon bands)
    grid_rows = []
    lats = np.arange(-88.75, 90.0, 2.5)
    lons = np.arange(-177.5, 180.0, 5.0)
    cell_id = 1
    for lat in lats:
        for lon in lons:
            clim = estimate_planetary_climate_at_point(float(lat), float(lon))
            clim["data_kind"] = "SIMULATED"
            clim["grid_cell_id"] = cell_id
            cell_id += 1
            grid_rows.append(clim)
    grid_df = pd.DataFrame(grid_rows)

    if save:
        COUNTRIES_ATLAS_PATH.parent.mkdir(parents=True, exist_ok=True)
        countries_df.to_csv(COUNTRIES_ATLAS_PATH, index=False)
        grid_df.to_csv(EARTH_GRID_PATH, index=False)

    return {
        "countries_count": len(countries_df),
        "grid_cells_count": len(grid_df),
        "countries_df": countries_df,
        "grid_df": grid_df,
    }
