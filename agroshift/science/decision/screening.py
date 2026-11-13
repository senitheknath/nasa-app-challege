"""Evidence-scoped first-season crop screening for the farmer workflow."""
from collections import defaultdict
import json
from pathlib import Path

import pandas as pd

from agroshift.science.decision.decision import CROPS, CRITERIA, KNOWLEDGE, MIN_SEASONS, assess, verify_climate
from agroshift.science.knowledge.knowledge import global_traits, screening_candidates
from agroshift.science.climate.power import DataError

_curr = Path(__file__).resolve()
while _curr != _curr.parent:
    if (_curr / "data").is_dir() and (_curr / "agroshift").is_dir():
        ROOT = _curr
        break
    _curr = _curr.parent
else:
    ROOT = Path(__file__).resolve().parents[2]
REGIONS = json.loads((ROOT / "data/regional_evidence.json").read_text(encoding="utf-8"))
POWER_SOURCE = {"title": "NASA POWER daily weather", "url": "https://power.larc.nasa.gov/data-access-viewer/"}
TRAIT_UNITS = {
    "preferred_daily_mean_air_temperature": "degC",
    "preferred_soil_ph": "pH",
    "persistent_waterlogging_conflict": "boolean",
    "seasonal_crop_et": "mm/crop cycle",
    "indicative_cycle_duration": "days",
}
STATUS_ORDER = {"possible": 0, "check": 1, "outside": 2, "unknown": 3, "blocked": 4}


def region_evidence(country):
    """Country-level source directory. Only the Sri Lankan pack has rotation rules."""
    return REGIONS.get(country.upper(), {
        "country": country, "rotation_pack": None, "title": "Global crop references",
        "scope": "General comparisons are available where a crop has a reviewed reference.", "sources": [],
    })


def _historical_window(frame, window):
    # Equal weight per valid year. Strict daily coverage avoids missing the hottest/coldest days.
    temperatures, rainfall = [], []
    for year in range(frame.index.min().year, frame.index.max().year + 1):
        start, end = window.dates(year)
        days = pd.date_range(start, end)
        if days[0] < frame.index.min() or days[-1] > frame.index.max():
            continue
        observed = frame.reindex(days)
        daily = observed["T2M"]
        if daily.notna().all():
            temperatures.append(daily)
        if observed["PRECTOTCORR"].notna().all():
            rainfall.append(float(observed["PRECTOTCORR"].sum()))
    return temperatures, rainfall


def _make_general_card(crop, traits, farm, window, daily_years, typical_day, rain, dates_covered):
    crop_id = crop["id"]
    details, observed, caution = [], [], []
    sources = {r["source_id"]: {"title": r.get("source_title") or r["source_id"], "url": r["source_url"]} for r in traits.values()}
    for row in traits.values():
        if row["note"]:
            details.append(row["note"])
    status = "unknown"
    assessed, missing = [], []
    temperature = traits.get("preferred_daily_mean_air_temperature")
    if temperature and typical_day is not None:
        assessed.append("historical temperature")
        low, high = temperature["low"], temperature["high"]
        inside = low <= typical_day <= high
        status = "possible" if inside else "outside"
        observed.append(f"The typical day was {typical_day:.1f} °C. This crop prefers {low:g}–{high:g} °C.")
        fractions = [season.between(low, high).mean() for season in daily_years]
        details.append(f"For {window.label}, {len(daily_years)} full years had every daily temperature. "
                       f"In a typical year, {pd.Series(fractions).median():.0%} of days were in the published range.")
    elif temperature:
        details.append(f"Temperature needs at least {MIN_SEASONS} seasons with a full daily record.")

    if not temperature or typical_day is None:
        missing.append("temperature fit")
    soil = traits.get("preferred_soil_ph")
    if soil and farm.ph is not None:
        assessed.append("measured soil pH")
        within = soil["low"] <= farm.ph <= soil["high"]
        observed.append(f"Your pH of {farm.ph:g} is {'inside' if within else 'outside'} the "
                        f"reference range of {soil['low']:g}–{soil['high']:g}.")
        if not within:
            caution.append("Check the soil pH before choosing this crop.")
            status = "outside"
        elif status == "unknown":
            status = "possible"
    elif soil:
        details.append("A field pH test would allow a soil comparison.")
    else:
        details.append("Soil pH compatibility has no reviewed reference for this comparison.")

    if not soil or farm.ph is None:
        missing.append("soil pH fit")
    drainage = traits.get("persistent_waterlogging_conflict")
    if farm.drainage == "waterlogged":
        if drainage and drainage["low"] == drainage["high"] == 1:
            status = "blocked"
            caution.append("This crop struggles where the field stays waterlogged.")
        else:
            caution.append("Check this crop's tolerance of standing water locally.")
            if status == "possible":
                status = "check"

    if drainage and farm.drainage != "unknown":
        assessed.append("reported drainage")
    else:
        missing.append("drainage fit")
    duration = traits.get("indicative_cycle_duration")
    duration_matches = False
    if duration:
        low, high = duration["low"], duration["high"]
        # Compare the exact selected recurring window; a leap-day difference is shown in Research.
        start, end = window.dates(2023)
        length = (end - start).days + 1
        duration_matches = low <= length <= high
        details.append(f"Your window spans {length} days. The indicative crop cycle is {low:g}–{high:g} days.")
        if length < low:
            caution.append("Your dates may be too short. Check the variety's time to harvest.")
            if status in {"possible", "unknown"}:
                status = "check"

    water = "Water supply still needs checking."
    water_ref = traits.get("seasonal_crop_et")
    if water_ref:
        low, high = water_ref["low"], water_ref["high"]
        details.append(f"Indicative full-cycle crop water use is {low:g}–{high:g} mm.")
        net = 0.0 if farm.irrigation == "rainfed" else farm.irrigation_mm
        if duration_matches and dates_covered and net is not None and farm.rain_fraction is not None:
            assessed.append("approximate seasonal water supply")
            estimated = rain * farm.rain_fraction + net
            water = f"Estimated supply is {estimated:.0f} mm against {low:g}–{high:g} mm of crop use."
            details.append("Supply uses median seasonal rain × the chosen usable fraction + net irrigation. Soil reserves and dry spells can change the outcome.")
            if estimated < low:
                caution.append("The water estimate is below the published crop-use range.")
                if status in {"possible", "unknown"}:
                    status = "check"
            elif status == "unknown":
                status = "check"
        elif not duration_matches:
            water = "Check water for the full growing cycle."
        elif farm.irrigation == "rainfed":
            water = "How much rain the roots can use is unknown."
    elif crop_id == "rice":
        water = "Check the water needed to prepare and maintain the paddy."
    if not temperature:
        details.append("Temperature compatibility has no reviewed reference for this comparison.")

    if "approximate seasonal water supply" not in assessed:
        missing.append("water adequacy")
    missing.append("local variety and pests")
    summaries = {
        "possible": "Some field conditions fit",
        "outside": "Outside a preferred range",
        "blocked": "Unsuitable for the conditions reported",
        "check": "Check a field condition",
        "unknown": "More information needed",
    }
    reason = (caution or observed or [f"Check your field pH against {soil['low']:g}–{soil['high']:g}." if soil
                                    else "There is too little evidence to judge this crop for your field."])[0]
    return dict(id=crop_id, name=crop["name"], summary=summaries[status], water=water,
                reason=reason, constraints=caution, details=list(dict.fromkeys(observed + details)),
                sources=[*sources.values(), POWER_SOURCE], support="general", status=status,
                assessed=assessed, unknown=missing)



def find_options(farm, dataset, *, weights=None):
    """Build JSON-ready cards for the first selected window. Missing evidence earns no credit."""
    farm.validate()
    if dataset is None or dataset.frame.empty:
        raise DataError("There is no weather history at this location.")
    frame = dataset.frame
    verify_climate(frame, farm)
    if dataset.provenance.get("simulated") is not False or dataset.provenance.get("data_kind") not in {"REAL", "VERIFIED_CACHE"}:
        raise DataError("Crop Finder requires verified NASA weather history for your field.")

    window = farm.windows[0]
    days, rainfall = _historical_window(frame, window)
    rain = pd.Series(rainfall, dtype=float)
    typical = float(pd.Series([d.median() for d in days]).median()) if len(days) >= MIN_SEASONS else None
    cards = []
    by_crop = defaultdict(dict)
    for trait in global_traits():
        name = trait["trait"]
        # Stage, cultivar and system-specific facts must not accidentally become universal.
        if (TRAIT_UNITS.get(name) != trait["units"] or trait.get("cultivar") or trait.get("system")
                or trait.get("review_status") != "reviewed" or trait.get("scope") != "global"):
            continue
        by_crop[trait["crop_id"]][name] = trait
    for crop in screening_candidates(by_crop):
        key = crop["id"]
        cards.append(_make_general_card(crop, by_crop[key], farm, window, days, typical,
                                        float(rain.median()) if len(rain) else None, len(rain) >= MIN_SEASONS))
    # Ties are alphabetical for browsing; a single matching trait cannot establish a best crop.
    return sorted(cards, key=lambda c: (STATUS_ORDER[c["status"]], c["support"] != "regional", c["name"].casefold()))
