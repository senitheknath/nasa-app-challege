"""Farm presets and explanations of the authoritative reference assessment."""
import json
import os
import requests

from agroshift.science.climate.climate import Window, classify_anomalies, season_samples, seasonal_summary
from agroshift.science.decision.decision import CROPS, KNOWLEDGE, Farm, assess, normalized_weights
from agroshift.science.climate.power import DataError

GLOBAL_SOURCES = KNOWLEDGE["sources"]

CROP_ICONS = {
    "rice": "🌾",
    "mung_bean": "🫛",
    "cowpea": "🌱",
    "maize": "🌽",
    "groundnut": "🥜",
    "soybean": "🌿",
    "sorghum": "🌾",
    "wheat": "🌾",
    "chickpea": "🫘",
    "potato": "🥔",
}

SEASON_TEMPLATES = {
    "Yala then Maha": {
        "label": "☀️ Tropical Monsoon: Dry/Yala (Apr–Jul) → Wet/Maha (Nov–Feb)",
        "windows": (Window(4, 15, 7, 31), Window(11, 1, 2, 28)),
    },
    "Maha then Yala": {
        "label": "🌧️ Tropical Monsoon: Wet/Maha (Nov–Feb) → Dry/Yala (Apr–Jul)",
        "windows": (Window(11, 1, 2, 28), Window(4, 15, 7, 31)),
    },
    "Kharif then Rabi (South Asia)": {
        "label": "🌾 Subtropical Monsoon: Kharif (Jun–Oct) → Rabi (Nov–Mar)",
        "windows": (Window(6, 15, 10, 15), Window(11, 1, 3, 15)),
    },
    "Northern Spring then Autumn": {
        "label": "🌱 Northern Hemisphere: Spring–Summer (Apr–Aug) → Autumn–Winter (Oct–Feb)",
        "windows": (Window(4, 15, 8, 25), Window(10, 1, 2, 15)),
    },
    "Temperate Spring-Autumn": {
        "label": "🌿 Temperate Northern: Spring–Summer (Apr–Aug) → Autumn–Winter (Sep–Jan)",
        "windows": (Window(4, 15, 8, 25), Window(9, 15, 1, 31)),
    },
    "East Africa Bimodal": {
        "label": "🌍 Equatorial Bimodal: Long Rains (Mar–Jul) → Short Rains (Oct–Jan)",
        "windows": (Window(3, 1, 7, 15), Window(10, 15, 1, 31)),
    },
    "East Africa Long-Short Rains": {
        "label": "🌍 Equatorial Bimodal: Long Rains (Mar–Jul) → Short Rains (Oct–Jan)",
        "windows": (Window(3, 1, 7, 15), Window(10, 15, 1, 31)),
    },
    "Southern Wet then Dry": {
        "label": "🌎 Southern Hemisphere: Warm Season (Nov–Mar) → Cool Season (May–Aug)",
        "windows": (Window(11, 1, 3, 15), Window(5, 1, 8, 31)),
    },
    "Southern Hemisphere Summer-Winter": {
        "label": "🌎 Southern Hemisphere: Summer (Nov–Mar) → Winter (May–Sep)",
        "windows": (Window(11, 1, 3, 15), Window(5, 1, 8, 31)),
    },
}

AREA_PRESETS = {
    "small_plot": {"label": "🏡 Small Plot — 0.5 ha (~1.2 acres)", "ha": 0.5},
    "family_farm": {"label": "🌾 Standard Family Farm — 1.0 ha (~2.5 acres)", "ha": 1.0},
    "medium_block": {"label": "🚜 Medium Farm Block — 2.5 ha (~6.2 acres)", "ha": 2.5},
    "commercial_block": {"label": "🏞️ Large Block — 5.0 ha (~12.4 acres)", "ha": 5.0},
    "custom": {"label": "✏️ Custom Farm Size (Enter Hectares)", "ha": None},
}

LOCATION_PRESETS = {
    "anuradhapura": {
        "label": "🇱🇰 South Asia · Anuradhapura Dry Zone, Sri Lanka (8.31°N, 80.40°E)",
        "latitude": 8.3114,
        "longitude": 80.4037,
        "country": "LK",
        "default_season": "Yala then Maha",
    },
    "polonnaruwa": {
        "label": "🇱🇰 South Asia · Polonnaruwa Mahaweli Belt, Sri Lanka (7.94°N, 81.02°E)",
        "latitude": 7.9403,
        "longitude": 81.0188,
        "country": "LK",
        "default_season": "Yala then Maha",
    },
    "kurunegala": {
        "label": "🇱🇰 South Asia · Kurunegala Intermediate Zone, Sri Lanka (7.49°N, 80.36°E)",
        "latitude": 7.4863,
        "longitude": 80.3623,
        "country": "LK",
        "default_season": "Yala then Maha",
    },
    "kandy": {
        "label": "🇱🇰 South Asia · Kandy Wet Highlands, Sri Lanka (7.29°N, 80.63°E)",
        "latitude": 7.2906,
        "longitude": 80.6337,
        "country": "LK",
        "default_season": "Yala then Maha",
    },
    "punjab_india": {
        "label": "🇮🇳 South Asia · Ludhiana (Punjab Plains), India (30.90°N, 75.86°E)",
        "latitude": 30.9010,
        "longitude": 75.8573,
        "country": "IN",
        "default_season": "Kharif then Rabi (South Asia)",
    },
    "maharashtra_india": {
        "label": "🇮🇳 South Asia · Nagpur (Deccan Plateau), India (21.15°N, 79.09°E)",
        "latitude": 21.1458,
        "longitude": 79.0882,
        "country": "IN",
        "default_season": "Kharif then Rabi (South Asia)",
    },
    "dhaka_bangladesh": {
        "label": "🇧🇩 South Asia · Bogura (Bengal Delta), Bangladesh (24.85°N, 89.38°E)",
        "latitude": 24.8465,
        "longitude": 89.3773,
        "country": "BD",
        "default_season": "Kharif then Rabi (South Asia)",
    },
    "faisalabad_pakistan": {
        "label": "🇵🇰 South Asia · Faisalabad (Indus Basin), Pakistan (31.45°N, 73.14°E)",
        "latitude": 31.4504,
        "longitude": 73.1350,
        "country": "PK",
        "default_season": "Kharif then Rabi (South Asia)",
    },
    "mekong_vietnam": {
        "label": "🇻🇳 SE Asia · Can Tho (Mekong Delta), Vietnam (10.05°N, 105.75°E)",
        "latitude": 10.0452,
        "longitude": 105.7469,
        "country": "VN",
        "default_season": "Yala then Maha",
    },
    "central_java": {
        "label": "🇮🇩 SE Asia · Semarang (Central Java), Indonesia (-6.97°S, 110.42°E)",
        "latitude": -6.9667,
        "longitude": 110.4167,
        "country": "ID",
        "default_season": "Southern Wet then Dry",
    },
    "central_luzon": {
        "label": "🇵🇭 SE Asia · Nueva Ecija (Central Luzon), Philippines (15.58°N, 120.97°E)",
        "latitude": 15.5784,
        "longitude": 120.9726,
        "country": "PH",
        "default_season": "Kharif then Rabi (South Asia)",
    },
    "thailand_chao_phraya": {
        "label": "🇹🇭 SE Asia · Nakhon Sawan (Chao Phraya), Thailand (15.69°N, 100.12°E)",
        "latitude": 15.6930,
        "longitude": 100.1226,
        "country": "TH",
        "default_season": "Kharif then Rabi (South Asia)",
    },
    "north_china_plain": {
        "label": "🇨🇳 East Asia · Zhengzhou (North China Plain), China (34.75°N, 113.63°E)",
        "latitude": 34.7466,
        "longitude": 113.6253,
        "country": "CN",
        "default_season": "Northern Spring then Autumn",
    },
    "hokkaido_japan": {
        "label": "🇯🇵 East Asia · Obihiro (Hokkaido), Japan (42.92°N, 143.20°E)",
        "latitude": 42.9239,
        "longitude": 143.1961,
        "country": "JP",
        "default_season": "Northern Spring then Autumn",
    },
    "tashkent_uzbekistan": {
        "label": "🇺🇿 Central Asia · Fergana Valley, Uzbekistan (40.38°N, 71.78°E)",
        "latitude": 40.3842,
        "longitude": 71.7843,
        "country": "UZ",
        "default_season": "Northern Spring then Autumn",
    },
    "nile_delta_egypt": {
        "label": "🇪🇬 North Africa · Tanta (Nile Delta), Egypt (30.79°N, 31.00°E)",
        "latitude": 30.7865,
        "longitude": 31.0004,
        "country": "EG",
        "default_season": "Northern Spring then Autumn",
    },
    "marrakech_morocco": {
        "label": "🇲🇦 North Africa · Gharb & Haouz Plains, Morocco (34.26°N, -6.58°W)",
        "latitude": 34.2610,
        "longitude": -6.5802,
        "country": "MA",
        "default_season": "Northern Spring then Autumn",
    },
    "nairobi_kenya": {
        "label": "🇰🇪 East Africa · Nairobi / Nakuru Highlands, Kenya (-1.29°S, 36.82°E)",
        "latitude": -1.2921,
        "longitude": 36.8219,
        "country": "KE",
        "default_season": "East Africa Bimodal",
    },
    "addis_ethiopia": {
        "label": "🇪🇹 East Africa · Shewa Highlands, Ethiopia (9.03°N, 38.75°E)",
        "latitude": 9.0320,
        "longitude": 38.7469,
        "country": "ET",
        "default_season": "Kharif then Rabi (South Asia)",
    },
    "kano_nigeria": {
        "label": "🇳🇬 West Africa · Kano Sudano-Sahelian Belt, Nigeria (12.00°N, 8.59°E)",
        "latitude": 12.0022,
        "longitude": 8.5920,
        "country": "NG",
        "default_season": "Northern Spring then Autumn",
    },
    "kumasi_ghana": {
        "label": "🇬🇭 West Africa · Kumasi Transition Zone, Ghana (6.69°N, -1.62°W)",
        "latitude": 6.6885,
        "longitude": -1.6244,
        "country": "GH",
        "default_season": "East Africa Bimodal",
    },
    "highveld_south_africa": {
        "label": "🇿🇦 Southern Africa · Free State Maize Triangle, South Africa (-27.75°S, 27.23°E)",
        "latitude": -27.7500,
        "longitude": 27.2333,
        "country": "ZA",
        "default_season": "Southern Wet then Dry",
    },
    "lilongwe_malawi": {
        "label": "🇲🇼 Southern Africa · Lilongwe Plateau, Malawi (-13.96°S, 33.77°E)",
        "latitude": -13.9626,
        "longitude": 33.7741,
        "country": "MW",
        "default_season": "Southern Wet then Dry",
    },
    "po_valley_italy": {
        "label": "🇮🇹 Europe · Bologna (Po Valley), Italy (44.49°N, 11.34°E)",
        "latitude": 44.4949,
        "longitude": 11.3426,
        "country": "IT",
        "default_season": "Northern Spring then Autumn",
    },
    "beauce_france": {
        "label": "🇫🇷 Europe · Chartres (Beauce Grain Belt), France (48.45°N, 1.49°E)",
        "latitude": 48.4469,
        "longitude": 1.4892,
        "country": "FR",
        "default_season": "Northern Spring then Autumn",
    },
    "seville_spain": {
        "label": "🇪🇸 Europe · Seville (Guadalquivir Valley), Spain (37.39°N, -5.98°W)",
        "latitude": 37.3891,
        "longitude": -5.9845,
        "country": "ES",
        "default_season": "Northern Spring then Autumn",
    },
    "poltava_ukraine": {
        "label": "🇺🇦 Europe · Poltava (Chornozem Steppe), Ukraine (49.59°N, 34.55°E)",
        "latitude": 49.5883,
        "longitude": 34.5514,
        "country": "UA",
        "default_season": "Northern Spring then Autumn",
    },
    "ames_usa": {
        "label": "🇺🇸 North America · Ames, Iowa (Corn Belt), USA (42.03°N, -93.63°W)",
        "latitude": 42.0308,
        "longitude": -93.6319,
        "country": "US",
        "default_season": "Northern Spring then Autumn",
    },
    "fresno_usa": {
        "label": "🇺🇸 North America · Fresno (Central Valley, CA), USA (36.74°N, -119.79°W)",
        "latitude": 36.7378,
        "longitude": -119.7871,
        "country": "US",
        "default_season": "Northern Spring then Autumn",
    },
    "saskatoon_canada": {
        "label": "🇨🇦 North America · Saskatoon (Prairie Grain Belt), Canada (52.13°N, -106.67°W)",
        "latitude": 52.1332,
        "longitude": -106.6700,
        "country": "CA",
        "default_season": "Northern Spring then Autumn",
    },
    "obregon_mexico": {
        "label": "🇲🇽 North America · Ciudad Obregón (Yaqui Valley), Mexico (27.48°N, -109.93°W)",
        "latitude": 27.4828,
        "longitude": -109.9304,
        "country": "MX",
        "default_season": "Kharif then Rabi (South Asia)",
    },
    "mato_grosso_brazil": {
        "label": "🇧🇷 South America · Sinop / Sorriso (Mato Grosso), Brazil (-11.86°S, -55.51°W)",
        "latitude": -11.8608,
        "longitude": -55.5095,
        "country": "BR",
        "default_season": "Southern Wet then Dry",
    },
    "pampas_argentina": {
        "label": "🇦🇷 South America · Pergamino (Humid Pampas), Argentina (-33.89°S, -60.57°W)",
        "latitude": -33.8900,
        "longitude": -60.5736,
        "country": "AR",
        "default_season": "Southern Wet then Dry",
    },
    "cusco_peru": {
        "label": "🇵🇪 South America · Sacred Valley (Andean Highlands), Peru (-13.53°S, -71.97°W)",
        "latitude": -13.5320,
        "longitude": -71.9675,
        "country": "PE",
        "default_season": "Southern Wet then Dry",
    },
    "wagga_australia": {
        "label": "🇦🇺 Oceania · Wagga Wagga (Riverina, NSW), Australia (-35.11°S, 147.36°E)",
        "latitude": -35.1082,
        "longitude": 147.3598,
        "country": "AU",
        "default_season": "Southern Wet then Dry",
    },
    "canterbury_nz": {
        "label": "🇳🇿 Oceania · Lincoln (Canterbury Plains), New Zealand (-43.64°S, 172.48°E)",
        "latitude": -43.6400,
        "longitude": 172.4840,
        "country": "NZ",
        "default_season": "Southern Wet then Dry",
    },
    "custom": {
        "label": "🌍 Any Country, City or Interactive World Map Click (-90° to +90°, All 249 Countries)",
        "latitude": None,
        "longitude": None,
        "country": "US",
        "default_season": "Northern Spring then Autumn",
    },
}

DEMO_SCENARIOS = {
    "scenario_1_well_drained": {
        "title": "Scenario 1 · Well-drained lowland transition (pH 6.5)",
        "summary": "Anuradhapura (8.3114°N, 80.4037°E), well-drained soil, measured pH 6.5, rainfed with no assumed rainfall-use fraction.",
        "farm": Farm(
            latitude=8.3114,
            longitude=80.4037,
            country="LK",
            area_ha=1.0,
            previous="rice",
            current="rice",
            baseline=("rice", "rice"),
            drainage="well_drained",
            ph=6.5,
            irrigation="rainfed",
            irrigation_mm=0.0,
            rain_fraction=None,
            pilot_confirmed=True,
            season_name="Yala then Maha",
        ),
    },
    "scenario_2_supplemental_water": {
        "title": "Scenario 2 · Supplemental irrigation & water screening",
        "summary": "Same Anuradhapura field with explicit hypothetical 35% usable rainfall and 250 mm net supplemental irrigation per slot.",
        "farm": Farm(
            latitude=8.3114,
            longitude=80.4037,
            country="LK",
            area_ha=1.0,
            previous="rice",
            current="rice",
            baseline=("rice", "rice"),
            drainage="well_drained",
            ph=6.5,
            irrigation="supplemental",
            irrigation_mm=250.0,
            rain_fraction=0.35,
            pilot_confirmed=True,
            season_name="Yala then Maha",
        ),
    },
    "scenario_3_waterlogged_missing_ph": {
        "title": "Scenario 3 · Persistent waterlogging & unknown soil pH",
        "summary": "Same Anuradhapura location with unmeasured pH/nutrients and persistent waterlogging, demonstrating hard drainage constraints.",
        "farm": Farm(
            latitude=8.3114,
            longitude=80.4037,
            country="LK",
            area_ha=1.0,
            previous="rice",
            current="rice",
            baseline=("rice", "rice"),
            drainage="waterlogged",
            ph=None,
            nutrients="Unknown",
            irrigation="rainfed",
            irrigation_mm=0.0,
            rain_fraction=None,
            pilot_confirmed=True,
            season_name="Yala then Maha",
        ),
    },
}


def assess_global_rotations(frame, farm, weights, rain_factor=1.0, temp_delta=0.0, candidate_crop_ids=None):
    """Compatibility entry point. Regional scope and constraints belong to decision.assess."""
    from dataclasses import replace
    selected = farm if candidate_crop_ids is None else replace(farm, allowed=tuple(candidate_crop_ids))
    return assess(frame, selected, weights, rain_factor, temp_delta)


def eligible_crops_and_rotations(dataset, farm, weights):
    """Group the authoritative sequences by first crop without assigning another score."""
    rotations = assess(dataset.frame, farm, weights)
    eligible, blocked = [], []
    for crop_id in farm.allowed:
        options = [r for r in rotations if r["sequence"][0] == crop_id]
        feasible = [r for r in options if not r["constraints"]]
        card = dict(crop_id=crop_id, name=CROPS[crop_id]["name"], slot=options[0]["slots"][0],
                    rotations=options, best_rotation=feasible[0] if feasible else None)
        (eligible if feasible else blocked).append(card)
    return dict(eligible_crops=eligible, blocked_crops=blocked, all_rotations=rotations)


def build_grounding_brief(dataset, farm: Farm, weights: dict, results: list) -> dict:
    """Assemble a strictly verified dictionary of climate, rotation, and reference facts."""
    from agroshift.science.decision.decision import verify_climate
    verify_climate(dataset.frame, farm)
    window_summaries = []
    for idx, w in enumerate(farm.windows):
        samples = classify_anomalies(season_samples(dataset.frame, w))
        summary = seasonal_summary(samples)
        dry_years = samples.loc[samples.get("regime", "") == "Dry anomaly (z < -1.0)", "year"].tolist() if not samples.empty and "regime" in samples else []
        wet_years = samples.loc[samples.get("regime", "") == "Wet anomaly (z > +1.0)", "year"].tolist() if not samples.empty and "regime" in samples else []
        window_summaries.append({
            "slot": idx + 1,
            "window": w.label,
            "summary": summary,
            "dry_anomaly_years": [int(y) for y in dry_years],
            "wet_anomaly_years": [int(y) for y in wet_years],
        })
    top_candidates = [
        {
            "order": r["order"],
            "id": r["id"],
            "name": r["name"],
            "baseline": r["baseline"],
            "status": r["status"],
            "interval": [round(r["low"], 1), round(r["high"], 1)],
            "evidence_coverage_pct": round(r["evidence_coverage"], 1),
            "missing_or_interval_criteria": r["missing"],
            "constraints": r["constraints"],
            "components": {
                k: {
                    "interval": [round(100 * v["low"], 1), round(100 * v["high"], 1)],
                    "reason": v["reason"],
                }
                for k, v in r["components"].items()
            },
            "sources": [GLOBAL_SOURCES[sid] for sid in r["sources"] if sid in GLOBAL_SOURCES],
        }
        for r in results[:5]
    ]
    blocked_count = sum(1 for r in results if r["status"] == "Blocked")
    return {
        "location": {"latitude": farm.latitude, "longitude": farm.longitude, "country": farm.country},
        "provenance_mode": dataset.provenance.get("mode", "unknown"),
        "period": f"{dataset.provenance['request']['start']}–{dataset.provenance['request']['end']}",
        "farm_inputs": {
            "current_crop": farm.current,
            "baseline": list(farm.baseline),
            "drainage": farm.drainage,
            "ph": farm.ph,
            "irrigation": farm.irrigation,
            "irrigation_mm": farm.irrigation_mm,
            "rain_fraction": farm.rain_fraction,
        },
        "priorities": weights,
        "windows": window_summaries,
        "total_candidates": len(results),
        "blocked_candidates": blocked_count,
        "top_rotations": top_candidates,
    }


def answer_farmer_question(
    question: str,
    dataset,
    farm: Farm,
    weights: dict,
    results: list,
    cards: list | None = None,
) -> dict:
    """Answer a farmer's question using deterministic, citation-grounded rules across both screened crops and rotations."""
    brief = build_grounding_brief(dataset, farm, weights, results)
    if cards is None:
        try:
            from agroshift.science.decision.screening import find_options

            cards = find_options(dataset, farm)
        except Exception:
            cards = []

    q = (question or "").strip().lower()
    citations = []
    seen_urls = set()

    def add_citation(title: str, url: str):
        if url not in seen_urls:
            seen_urls.add(url)
            citations.append({"title": title, "url": url})

    add_citation("NASA POWER Daily Agroclimatology API", "https://power.larc.nasa.gov/docs/services/api/temporal/daily/")
    add_citation("Climdex Consecutive Dry Days (CDD) Index", "https://www.climdex.org/learn/indices/")

    from agroshift.science.soil_water.soil_and_water import fetch_soil_profile

    soil_prior = fetch_soil_profile(farm.latitude, farm.longitude, allow_network=False)
    possible_cards = [c for c in (cards or []) if c.get("status") == "possible"]
    check_cards = [c for c in (cards or []) if c.get("status") == "check"]
    outside_cards = [c for c in (cards or []) if c.get("status") in ("outside", "blocked")]

    worth_names = ", ".join(c["name"] for c in possible_cards[:6]) or "None confirmed yet (more field details needed)"
    check_names = ", ".join(c["name"] for c in check_cards[:6]) or "None"
    outside_names = ", ".join(c["name"] for c in outside_cards[:5]) or "None"
    ph_status = (
        f"Measured field pH {farm.ph:.1f}"
        if farm.ph is not None
        else f"Unmeasured (regional SoilGrids reference is pH ~{soil_prior['ph_median']:.1f}, {soil_prior['usda_texture']})"
    )
    win0_sum = brief["windows"][0]["summary"] if brief.get("windows") else {}
    clim_short = (
        f"Median seasonal rain {win0_sum.get('rainfall_median_mm', 0):.0f} mm, mean temperature {win0_sum.get('temperature_mean_c', 0):.1f} °C, longest dry spell {win0_sum.get('longest_dry_spell_days', 0)} days."
        if win0_sum.get("valid_seasons", 0) > 0
        else "Seasonal climate record loaded."
    )
    next_steps = []
    if farm.ph is None:
        next_steps.append("Enter a soil pH test (or 2-minute pH strip check) to verify acid/alkaline crop compatibility")
    if farm.drainage == "unknown":
        next_steps.append("Confirm whether water drains away or stays standing after heavy rain")
    if farm.irrigation_mm is None and farm.irrigation != "rainfed":
        next_steps.append("Add your seasonal irrigation depth (or number of water turns)")
    if farm.rain_fraction is None:
        next_steps.append("Set your field landform / usable rainfall fraction")

    brief["screened_crops"] = {
        "worth_considering_count": len(possible_cards),
        "check_before_planting_count": len(check_cards),
        "outside_or_blocked_count": len(outside_cards),
        "worth_considering_summary": f"Crops worth considering right now ({len(possible_cards)}): {worth_names}.",
        "check_before_planting_summary": f"Crops marked 'Check before planting' ({len(check_cards)}): {check_names}.",
        "climate_summary": f"Local seasonal climate summary: {clim_short}",
        "soil_summary": f"Soil & drainage profile: {ph_status}; drainage is '{farm.drainage}'.",
        "next_steps_summary": (
            "Recommended field checks to narrow uncertainty: " + "; ".join(next_steps) + "."
            if next_steps
            else "All primary soil and water field inputs are provided."
        ),
    }

    lines = []

    # 1. Plain-language farmer takeaway at the very top tailored to the question & screened crops
    lines.append("### Plain-Language Answer for Your Farm")
    if any(w in q for w in ("ph", "acid", "alkaline", "lime", "soil")):
        lines.append(f"- **Your current soil status:** **{ph_status}**, and field drainage is **`{farm.drainage}`**.")
        if farm.ph is None:
            lines.append(
                f"- **How soil pH affects your options:** Because you haven't entered a soil pH measurement yet, crops cannot be ruled in or out by soil acidity alone. "
                f"Your regional SoilGrids baseline is **pH ~{soil_prior['ph_median']:.1f}** ({soil_prior['usda_texture']}, available water capacity ~{soil_prior['hydraulics']['awc_mm_per_m']:.0f} mm/m). "
                "Entering a quick pH strip or lab value in **Edit my field → Field measurements** will immediately verify pH suitability for every crop."
            )
        else:
            ph_fit = [
                c["name"]
                for c in (possible_cards + check_cards)
                if c.get("id") in CROPS
                and CROPS[c["id"]]["ph_range"][0] <= farm.ph <= CROPS[c["id"]]["ph_range"][1]
            ]
            ph_out = [
                f"{c['name']} (needs pH {CROPS[c['id']]['ph_range'][0]:.1f}–{CROPS[c['id']]['ph_range'][1]:.1f})"
                for c in (cards or [])
                if c.get("id") in CROPS
                and not (CROPS[c["id"]]["ph_range"][0] <= farm.ph <= CROPS[c["id"]]["ph_range"][1])
            ]
            if ph_fit:
                lines.append(f"- **Crops matching your soil pH ({farm.ph:.1f}):** {', '.join(ph_fit[:8])}.")
            if ph_out:
                lines.append(f"- **Crops outside your soil pH ({farm.ph:.1f}):** {', '.join(ph_out[:6])}.")
    elif any(w in q for w in ("check", "before planting", "uncertain", "missing", "unknown", "water")):
        lines.append(
            f"- **Why some crops say 'Check before planting':** A crop is placed in **Check before planting** ({len(check_cards)} crops: **{check_names}**) when its temperature or rainfall is close to your season's historical range, or when an important on-farm detail (such as usable water amount, drainage, or soil pH) hasn't been measured yet."
        )
        for c in check_cards[:4]:
            reason_txt = "; ".join(c.get("reasons", [])[:2]) or c.get("summary", "")
            lines.append(f"  - **{c['name']}:** {c.get('summary', '')} ({reason_txt})")
        if next_steps:
            lines.append("- **Fastest way to resolve these checks:** " + " · ".join(next_steps) + ".")
    else:
        if possible_cards:
            lines.append(
                f"- **Top crops worth considering ({len(possible_cards)}):** **{worth_names}**. These match your growing window's historical temperature and available field conditions."
            )
        if check_cards:
            lines.append(
                f"- **Crops to check before planting ({len(check_cards)}):** **{check_names}**. Review their water, drainage, or soil notes before committing seed."
            )
        if outside_cards:
            lines.append(
                f"- **Crops outside the reference range ({len(outside_cards)}):** **{outside_names}** do not match this season's typical rainfall, temperature, or field drainage."
            )

    lines.append("### Historical Climate Context (NASA POWER)")
    lines.append(
        f"Observations cover **{brief['period']}** ({brief['provenance_mode']}) at **{farm.latitude:.4f}°, {farm.longitude:.4f}° ({farm.country})**. "
        "These are regional gridded historical records (0.5° × 0.625° meteorology), not a future weather forecast."
    )
    for win in brief["windows"]:
        s = win["summary"]
        if s.get("valid_seasons", 0) > 0:
            dry_list = ", ".join(str(y) for y in win["dry_anomaly_years"][:5]) or "none"
            wet_list = ", ".join(str(y) for y in win["wet_anomaly_years"][:5]) or "none"
            lines.append(
                f"- **Slot {win['slot']} ({win['window']}):** Across **{s['valid_seasons']} complete seasons**, "
                f"median rainfall is **{s['rainfall_median_mm']:.0f} mm** (middle 50%: {s['rainfall_p25_mm']:.0f}–{s['rainfall_p75_mm']:.0f} mm), "
                f"mean temperature is **{s['temperature_mean_c']:.1f} °C**, and the longest consecutive `< 1 mm` dry spell is **{s['longest_dry_spell_days']} days**. "
                f"Historical dry-anomaly years ($z < -1$): {dry_list}; wet-anomaly years ($z > +1$): {wet_list}."
            )

    if results:
        baseline = next((r for r in results if r["baseline"]), results[0])
        lead = results[0]
        for r in (lead, baseline):
            for sid in r["sources"]:
                if sid in GLOBAL_SOURCES:
                    src = GLOBAL_SOURCES[sid]
                    add_citation(src["title"], src["url"])

        if not lead["constraints"] and (not q or any(w in q for w in ("rank", "best", "top", "compare", "rotation", "why", "baseline", "rice", "mung", "cowpea", "maize", "groundnut", "wheat", "soy", "potato", "sorghum", "chickpea", "summary"))):
            lines.append("### Rotation Comparison & Trade-Offs")
            lines.append(
                f"- **First in conservative preference ordering:** **{lead['name']}** (`{lead['status']}`, preference interval **{lead['low']:.1f}–{lead['high']:.1f}/100**, "
                f"fully assessed weight: **{lead['evidence_coverage']:.0f}%**)."
            )
            if baseline["id"] != lead["id"]:
                lines.append(
                    f"- **Your existing baseline plan:** **{baseline['name']}** (order **#{baseline['order']}**, `{baseline['status']}`, "
                    f"preference interval **{baseline['low']:.1f}–{baseline['high']:.1f}/100**)."
                )
            overlap = lead["low"] <= max((r["high"] for r in results[1:] if not r["constraints"]), default=-1)
            if overlap:
                lines.append(
                    "- **Important ordering note:** Preference intervals overlap across the top candidates because some criteria remain interval-valued or unmeasured. "
                    "AgroShift AI reports a conditional comparison rather than claiming a guaranteed winner."
                )

        if not q or any(w in q for w in ("block", "waterlog", "drainage", "constraint", "infeasible", "fail", "why")):
            blocked = [r for r in results if r["status"] == "Blocked"]
            if blocked:
                example = blocked[0]
                reason = example["constraints"][0] if example["constraints"] else "Hard constraint triggered."
                lines.append(
                    f"### Hard Agronomic Constraints ({len(blocked)} of {len(results)} sequences blocked)\n"
                    f"- **{len(blocked)} sequences** (including **{example['name']}**) are marked **`Blocked`** regardless of priority weights.\n"
                    f"- **Reason:** {reason}"
                )
            else:
                lines.append(
                    "### Hard Agronomic Constraints\n"
                    "- No candidate sequences are currently blocked by the documented drainage or window-duration checks."
                )

        if farm.ph is None or farm.irrigation_mm is None or not q or any(w in q for w in ("uncertain", "missing", "unknown", "interval", "water", "ph", "soil", "improve", "narrow")):
            missing_items = []
            if farm.ph is None:
                missing_items.append("Measured **soil pH** is blank, widening the soil component interval.")
            if farm.drainage == "unknown":
                missing_items.append("**Field drainage** is unknown; confirming whether the field is well-drained or waterlogged will resolve drainage compatibility.")
            if farm.irrigation_mm is None:
                missing_items.append("Net irrigation quantity is unknown. Water screening remains unassessed.")
            if farm.rain_fraction is None:
                missing_items.append("**Usable-rainfall fraction** is unknown. Quantitative water compatibility is unassessed.")
            if missing_items:
                lines.append("### Uncertainty & Missing Information\n" + "\n".join(f"- {item}" for item in missing_items))

        if any(w in q for w in ("narrow", "improve", "soil", "water", "drought", "heat", "stress", "root", "fao")):
            from agroshift.science.soil_water.soil_and_water import compute_uncertainty_narrowing_guide, simulate_crop_water_and_thermal_physics
            voi = compute_uncertainty_narrowing_guide(dataset.frame, farm, weights)
            if voi.get("available") and voi.get("actions"):
                top_act = voi["actions"][0]
                lines.append(
                    f"### Value-of-Information (VoI) Uncertainty Narrowing\n"
                    f"- **Highest-leverage field input to confirm next:** **{top_act['title']}** "
                    f"(narrows interval uncertainty by up to **±{top_act['impact_pts']:.1f} pts** → *{top_act['suggested_label']}*)."
                )
            lead_crop_slot1 = lead["sequence"][0]
            phys_diag = simulate_crop_water_and_thermal_physics(dataset.frame, farm.windows[0], lead_crop_slot1, farm)
            if phys_diag.get("available"):
                add_citation("FAO Irrigation and Drainage Paper 56 (Crop Evapotranspiration)", "https://www.fao.org/4/x0490e/x0490e00.htm")
                lines.append(
                    f"### FAO-56 Daily Root-Zone & Phenology Diagnostic (Slot 1 · {CROPS[lead_crop_slot1]['name']})\n"
                    f"- **Median Seasonal Crop Demand ($ET_c$):** **{phys_diag['etc_seasonal_median_mm']:.0f} mm** "
                    f"(Root-zone relative ET sufficiency: **{phys_diag['relative_et_sufficiency_pct']:.0f}%**; "
                    f"mid-season flowering moisture-stress days: **{phys_diag['flowering_drought_days_median']} d**; "
                    f"flowering heat-stress days $>35\\,^\\circ\\text{{C}}$: **{phys_diag['flowering_heat_days_median']} d**)."
                )
    else:
        missing_items = []
        if farm.ph is None:
            missing_items.append("Measured **soil pH** is blank; crop pH compatibility remains unassessed until a field soil test is entered.")
        if farm.drainage == "unknown":
            missing_items.append("**Field drainage** is unknown; confirming whether the field is well-drained or waterlogged will resolve drainage compatibility.")
        if farm.irrigation_mm is None:
            missing_items.append("**Net irrigation quantity (mm)** is unknown; quantitative water screening remains unassessed.")
        if farm.rain_fraction is None:
            missing_items.append("**Usable-rainfall fraction** is unknown; quantitative water adequacy remains unassessed.")
        if missing_items:
            lines.append("### Uncertainty & Missing Water / Soil Information\n" + "\n".join(f"- {item}" for item in missing_items))

    return {
        "answer": "\n\n".join(lines),
        "mode": "Explanation from recorded evidence and reference screening",
        "citations": citations,
        "brief": brief,
    }


def run_counterfactual_copilot(scenario_key: str, dataset, farm: Farm, weights: dict) -> dict:
    """Execute a verified counterfactual simulation against decision.assess() and summarize rank & interval shifts."""
    from dataclasses import replace
    from agroshift.science.soil_water.soil_and_water import fetch_soil_profile

    base_results = assess(dataset.frame, farm, weights)
    base_lead = next((r for r in base_results if not r["constraints"]), base_results[0])
    soil_prior = fetch_soil_profile(farm.latitude, farm.longitude, allow_network=False)

    rain_factor = 1.0
    temp_delta = 0.0
    mod_farm = farm
    label = "Baseline comparison"

    if scenario_key == "apply_soil_and_upland_water":
        label = f"Counterfactual · Regional Soil Prior (pH {soil_prior['ph_median']:.1f}, Well-Drained) + Minor Tank Supplemental (180 mm, 60% usable rain)"
        mod_farm = replace(
            farm,
            ph=farm.ph if farm.ph is not None else soil_prior["ph_median"],
            drainage="well_drained" if farm.drainage == "unknown" else farm.drainage,
            soil_type=soil_prior["usda_texture"] if farm.soil_type == "unknown" else farm.soil_type,
            irrigation="supplemental" if farm.irrigation in ("unknown", "rainfed") else farm.irrigation,
            irrigation_mm=180.0 if not farm.irrigation_mm else farm.irrigation_mm,
            rain_fraction=0.60 if farm.rain_fraction is None else farm.rain_fraction,
            irrigation_basis="illustrative scenario",
        )
    elif scenario_key == "severe_drought_heat":
        label = "Counterfactual · Severe Monsoon Deficit (-25% Rainfall) & +1.5 °C Warming"
        rain_factor = 0.75
        temp_delta = 1.5
    elif scenario_key == "waterlogged_paddy_basin":
        label = "Counterfactual · Bunded Lowland Basin with Persistent Waterlogging"
        mod_farm = replace(farm, drainage="waterlogged", rain_fraction=0.72)

    cf_results = assess(dataset.frame, mod_farm, weights, rain_factor=rain_factor, temp_delta=temp_delta)
    cf_lead = next((r for r in cf_results if not r["constraints"]), cf_results[0])
    base_lookup = {r["id"]: r for r in base_results}

    deltas = []
    for r in cf_results[:6]:
        b_r = base_lookup[r["id"]]
        deltas.append({
            "Rotation": r["name"],
            "Baseline Order": f"#{b_r['order']}",
            "Counterfactual Order": f"#{r['order']}",
            "Baseline Interval": f"{b_r['low']:.1f}–{b_r['high']:.1f}",
            "Counterfactual Interval": f"{r['low']:.1f}–{r['high']:.1f}",
            "Evidence Assessed (%)": f"{b_r['evidence_coverage']:.0f}% → {r['evidence_coverage']:.0f}%",
            "Status": r["status"],
        })

    return {
        "scenario_key": scenario_key,
        "label": label,
        "baseline_lead": base_lead["name"],
        "baseline_interval": [round(base_lead["low"], 1), round(base_lead["high"], 1)],
        "counterfactual_lead": cf_lead["name"],
        "counterfactual_interval": [round(cf_lead["low"], 1), round(cf_lead["high"], 1)],
        "lead_changed": base_lead["id"] != cf_lead["id"],
        "width_change_pts": round((cf_lead["high"] - cf_lead["low"]) - (base_lead["high"] - base_lead["low"]), 1),
        "table": deltas,
    }


def query_optional_gemini(question: str, brief: dict, api_key: str | None = None, session=None) -> str:
    """Optional Gemini REST adapter grounded strictly in the verified brief JSON."""
    key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    if not key:
        raise DataError("No GEMINI_API_KEY configured. The built-in grounded assistant works without an API key.")
    http = session or requests
    # The model may select evidence topics. Only application-owned facts are displayed.
    topics = {
        "period": f"Observation period: {brief.get('period', 'recorded history')} ({brief.get('provenance_mode', 'verified')}).",
        "coverage": f"Compared {brief.get('total_candidates', 0)} sequences, including {brief.get('blocked_candidates', 0)} blocked.",
        "water": f"Reported irrigation category: {brief.get('farm_inputs', {}).get('irrigation', 'unknown')}.",
        "scope": "Crop screening uses regional reference ranges and farmer priorities.",
    }
    sc = brief.get("screened_crops")
    if isinstance(sc, dict):
        if sc.get("worth_considering_summary"):
            topics["crops"] = sc["worth_considering_summary"]
        if sc.get("check_before_planting_summary"):
            topics["checks"] = sc["check_before_planting_summary"]
        if sc.get("climate_summary"):
            topics["climate"] = sc["climate_summary"]
        if sc.get("soil_summary"):
            topics["soil"] = sc["soil_summary"]
        if sc.get("next_steps_summary"):
            topics["next_steps"] = sc["next_steps_summary"]

    request = {
        "contents": [
            {
                "parts": [
                    {
                        "text": json.dumps(
                            {
                                "task": "Select the most relevant topic IDs for the farmer's question from the topics dictionary; return ONLY a JSON array of topic key strings.",
                                "question": question[:500],
                                "topics": topics,
                            }
                        )
                    }
                ]
            }
        ],
        "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
    }
    try:
        if session is not None:
            response = http.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
                headers={"x-goog-api-key": key},
                json=request,
                timeout=(5, 20),
            )
            response.raise_for_status()
        else:
            response = None
            for model_id in ("gemini-3.8-flash", "gemini-2.5-flash"):
                resp = http.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent",
                    headers={"x-goog-api-key": key},
                    json=request,
                    timeout=(5, 20),
                )
                if resp.status_code == 200:
                    response = resp
                    break
                response = resp
            response.raise_for_status()
        raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw_text.startswith("```"):
            lines_txt = [ln for ln in raw_text.splitlines() if not ln.strip().startswith("```")]
            raw_text = "\n".join(lines_txt).strip()
        selected = json.loads(raw_text)
        if (
            not isinstance(selected, list)
            or not selected
            or any(not isinstance(k, str) or k not in topics for k in selected)
        ):
            raise ValueError("Unrecognized evidence topics")
        return "\n\n".join(topics[k] for k in dict.fromkeys(selected))
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
        raise DataError("The optional summary is unavailable. The built-in explanation is available above.") from exc
