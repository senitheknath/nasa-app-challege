"""Conservative preference intervals, with explicit unknowns and feasibility."""
from dataclasses import dataclass
from itertools import product
import json
import math
from pathlib import Path

from agroshift.science.climate.climate import Window, season_samples
from agroshift.science.climate.power import DataError, coordinates

_curr = Path(__file__).resolve()
while _curr != _curr.parent:
    if (_curr / "data").is_dir() and (_curr / "agroshift").is_dir():
        ROOT = _curr
        break
    _curr = _curr.parent
else:
    ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE = json.loads((ROOT / "data/crops.json").read_text(encoding="utf-8"))
CROPS = KNOWLEDGE["crops"]
CRITERIA = ("temperature", "water", "soil", "diversification")
MIN_SEASONS = 10  # disclosed engineering sufficiency rule, not biological validation


@dataclass
class Farm:
    latitude: float = 8.3114
    longitude: float = 80.4037
    country: str = "LK"
    area_ha: float | None = None
    previous: str = "unknown"
    current: str = "unknown"
    baseline: tuple = ("rice", "rice")
    allowed: tuple = tuple(CROPS)
    drainage: str = "unknown"
    soil_type: str = "unknown"
    ph: float | None = None
    nutrients: str = "Unknown"
    irrigation: str = "unknown"
    irrigation_mm: float | None = None
    irrigation_basis: str = "user supplied"
    water_holding_capacity: str = "unknown"
    input_origin: str = "farm profile"
    rain_fraction: float | None = None
    residues: str = "unknown"
    pilot_confirmed: bool = False
    mung_cultivar: str = "unknown"
    season_name: str = "Custom dates"
    windows: tuple = (Window(4, 15, 7, 31), Window(11, 1, 2, 28))

    def validate(self):
        coordinates(self.latitude, self.longitude)
        if self.drainage not in {"unknown","well_drained","waterlogged"}:
            raise DataError("Choose a supported drainage condition.")
        if self.irrigation not in {"unknown","rainfed","supplemental","reliable"}:
            raise DataError("Choose a supported irrigation category.")
        if self.area_ha is not None and (not math.isfinite(self.area_ha) or self.area_ha <= 0):
            raise DataError("Farm area must be greater than zero.")
        if self.ph is not None and (not math.isfinite(self.ph) or not 0 <= self.ph <= 14):
            raise DataError("Soil pH must be 0–14 or unknown.")
        if not self.allowed or not set(self.allowed) <= set(CROPS):
            raise DataError("Choose at least one supported crop.")
        if self.baseline and (len(self.baseline) != 2 or not set(self.baseline) <= set(CROPS)):
            raise DataError("Select two supported baseline crops.")
        if self.current not in (*CROPS, "unknown") or self.previous not in (*CROPS, "unknown"):
            from agroshift.science.knowledge.knowledge import crop_by_id
            if any(value != "unknown" and crop_by_id(value) is None for value in (self.current, self.previous)):
                raise DataError("Unsupported crop history.")
        if len(self.windows) not in (1, 2):
            raise DataError("Choose one or two growing seasons.")
        occupied = []
        for window in self.windows:
            a, b = window.dates(2023)
            days = (b-a).days+1
            maximum_days = 366 if len(self.windows) == 1 else 240
            if not 30 <= days <= maximum_days:
                raise DataError(f"Each crop window must be 30–{maximum_days} days.")
            # Cyclic calendar check: disallow overlap even across year boundaries.
            import pandas as pd
            occupied.append({(d.month, d.day) for d in pd.date_range(a, b)})
        if len(occupied) == 2 and occupied[0] & occupied[1]:
            raise DataError("The two crop windows must not overlap.")
        if self.rain_fraction is not None and not 0 <= self.rain_fraction <= 1:
            raise DataError("Assumed usable-rainfall fraction must be 0–1.")
        if self.irrigation_mm is not None and (not math.isfinite(self.irrigation_mm) or self.irrigation_mm < 0):
            raise DataError("Irrigation amount must be non-negative or unknown.")
        if self.irrigation == "rainfed" and self.irrigation_mm not in (0, None):
            raise DataError("Rainfed farms cannot have a positive irrigation amount.")


def normalized_weights(weights):
    if set(weights) != set(CRITERIA) or any(not math.isfinite(v) or v < 0 for v in weights.values()):
        raise DataError("Each criterion needs a finite, non-negative priority.")
    total = sum(weights.values())
    if total <= 0:
        raise DataError("At least one priority must be above zero.")
    return {k: v/total for k, v in weights.items()}


def component(low, high, reason, source=None):
    return dict(low=float(low), high=float(high), reason=reason, source=source,
                assessed=bool(low == high))


def unknown(reason):
    return component(0, 1, reason)


def crop_components(crop_id, sample, farm):
    crop = CROPS[crop_id]
    valid = sample.dropna(subset=["rainfall_mm", "temperature_c"]) if not sample.empty else sample
    messages = list(crop["notes"])
    constraints = []
    temp = crop["temperature_c"]
    if len(valid) >= MIN_SEASONS and temp:
        value = valid.temperature_c.between(*temp).mean()
        temperature = component(value, value, "Fraction of historical seasonal means inside the cited preferred range; no crop-stage heat model.", crop["temperature_source"])
    else:
        temperature = unknown("Missing crop temperature reference or fewer than ten complete historical seasons.")
    water = unknown("Paddy land preparation, seepage and ponding are unknown. Total water needs are unassessed." if crop_id == "rice"
                    else "Usable-rainfall assumption, irrigation amount or species water reference is missing.")
    if len(valid) >= MIN_SEASONS and crop["water_mm"] and farm.rain_fraction is not None and farm.irrigation_mm is not None:
        if crop_id == "rice":
            water = unknown("Paddy land preparation, seepage and ponding are unknown; ET alone cannot score its total water needs.")
        else:
            available = valid.rainfall_mm.median()*farm.rain_fraction + farm.irrigation_mm
            low, high = crop["water_mm"]
            water = component(min(available/high, 1), min(available/low, 1),
                              "Hypothetical usable rain + net irrigation divided by indicative seasonal ET range; no soil storage or water timing model.", crop["water_source"])
    if crop["requires_drainage"]:
        if farm.drainage == "waterlogged":
            constraints.append("Reported persistent waterlogging conflicts with the crop's drainage requirement; drainage improvement needs local review.")
        drainage = unknown("Field drainage is unknown.") if farm.drainage == "unknown" else component(
            int(farm.drainage == "well_drained"), int(farm.drainage == "well_drained"),
            "Drainage compatibility with the reported field condition.", crop["soil_source"])
    else:
        drainage = unknown("Rice establishment system and field water management need review.")
    if crop["ph_preferred"] and farm.ph is not None:
        match = int(crop["ph_preferred"][0] <= farm.ph <= crop["ph_preferred"][1])
        ph = component(match, match, "Inside/outside the cited preferred pH range, not a survival threshold.", crop["soil_source"])
    else:
        ph = unknown("Soil pH has not been measured. pH compatibility is unassessed." if farm.ph is None
                     else "A crop-specific pH reference is missing.")
    soil = component((drainage["low"]+ph["low"])/2, (drainage["high"]+ph["high"])/2,
                     drainage["reason"]+" "+ph["reason"], crop["soil_source"])
    return dict(temperature=temperature, water=water, soil=soil), constraints, messages


def verify_climate(frame, farm):
    """Admit only a verified POWER series matched to this farm."""
    if frame.attrs.get("data_kind") not in {"REAL", "VERIFIED_CACHE"}:
        raise DataError("Agricultural assessment requires verified NASA history. Simulated or unverified data is ineligible.")
    if (frame.attrs.get("latitude"), frame.attrs.get("longitude")) != (farm.latitude, farm.longitude):
        raise DataError("Observation coordinates do not match this farm.")


def capability(farm):
    from agroshift.earth_data.geography import pilot_scope
    if len(farm.windows) == 2 and pilot_scope(farm.latitude, farm.longitude, farm.country, farm.pilot_confirmed):
        return "Level 2 · Sri Lankan reference-based crop screening"
    return "Global climate and crop reference screening"


def assess(frame, farm, weights, rain_factor=1.0, temp_delta=0.0):
    """Order by conservative lower bounds; overlap remains explicitly unresolved."""
    from agroshift.earth_data.geography import pilot_scope
    farm.validate()
    if not pilot_scope(farm.latitude, farm.longitude, farm.country, farm.pilot_confirmed):
        raise DataError("Rotation exploration is limited to farmer-confirmed Sri Lankan lowland dry/intermediate settings. Global climate remains available.")
    if len(farm.windows) != 2:
        raise DataError("Choose a second growing season to compare rotations.")
    verify_climate(frame, farm)
    weights = normalized_weights(weights)
    samples = [season_samples(frame, w, rain_factor, temp_delta) for w in farm.windows]
    if any(s.empty or len(s.dropna(subset=["rainfall_mm", "temperature_c"])) < MIN_SEASONS for s in samples):
        raise DataError("At least ten complete historical samples in each crop window are required for comparison. Expand the history or inspect coverage.")
    candidates = list(dict.fromkeys(([tuple(farm.baseline)] if farm.baseline else []) + list(product(farm.allowed, repeat=2))))
    results = []
    for sequence in candidates:
        parts, constraints, messages, sources, slots = [], [], [], set(), []
        for slot, crop_id in enumerate(sequence):
            crop = CROPS[crop_id]
            part, blocked, notes = crop_components(crop_id, samples[slot], farm)
            a, b = farm.windows[slot].dates(2023)
            duration = crop["duration_days"]
            if duration and (b-a).days+1 < duration[0]:
                if crop_id == "mung_bean" and farm.mung_cultivar != "MI 6":
                    messages.append(f"Slot {slot+1}: the window is shorter than the MI 6 example. Verify the intended mung bean cultivar.")
                else:
                    blocked.append("Window is shorter than the cited example's earliest harvest; a different locally reviewed cultivar would be needed.")
            messages.extend(f"Slot {slot+1}: {note}" for note in notes)
            constraints.extend(f"Slot {slot+1} ({crop['name']}): {note}" for note in blocked)
            sources.update(crop["sources"])
            parts.append(part)
            slots.append(dict(crop_id=crop_id, window=farm.windows[slot].label,
                              components=part, constraints=blocked, sources=crop["sources"]))
        transitions = [(farm.current, sequence[0]), (sequence[0], sequence[1])]
        transition_values = [unknown("Previous crop or its regional family reference is unknown.") if previous not in CROPS else
                             component(int(CROPS[previous]["family"] != CROPS[nxt]["family"]),
                                       int(CROPS[previous]["family"] != CROPS[nxt]["family"]),
                                       "Different botanical family is a diversification preference; no quantified pest or nitrogen benefit.")
                             for previous, nxt in transitions]
        components = {key: component(sum(p[key]["low"] for p in parts)/2, sum(p[key]["high"] for p in parts)/2,
                                    " | ".join(p[key]["reason"] for p in parts))
                      for key in CRITERIA if key != "diversification"}
        components["diversification"] = component(sum(v["low"] for v in transition_values)/2,
                                                   sum(v["high"] for v in transition_values)/2,
                                                   "Family changes across current → slot 1 → slot 2; heuristic preference only.")
        low = 100*sum(weights[k]*components[k]["low"] for k in CRITERIA)
        high = 100*sum(weights[k]*components[k]["high"] for k in CRITERIA)
        missing = [k for k in CRITERIA if components[k]["high"] > components[k]["low"]]
        if any(CROPS[c]["legume"] for c in sequence):
            messages.append("Legume nitrogen contribution depends on fixation, harvest and residues; no fixed nitrogen credit is assumed.")
        if farm.previous == farm.current and farm.current in sequence:
            messages.append("Repeated crop history: review local disease and pest risks; this model does not quantify them.")
        results.append(dict(id="__".join(sequence), sequence=sequence,
                            name=" → ".join(CROPS[c]["name"] for c in sequence),
                            baseline=sequence == tuple(farm.baseline), components=components, slots=slots,
                            low=low, high=high, status="Blocked" if constraints else "Conditional exploration",
                            constraints=constraints, notes=list(dict.fromkeys(messages)), missing=missing,
                            sources=sorted(sources), evidence_coverage=100*sum(weights[k] for k in CRITERIA if k not in missing)))
    results.sort(key=lambda x: (bool(x["constraints"]), -x["low"], x["id"]))
    for index, result in enumerate(results):
        result["order"] = index+1
        result["ordering_resolved"] = not result["constraints"] and all(
            result["low"] > other["high"] for other in results if other is not result and not other["constraints"])
    return results


def priority_sensitivity(results, weights):
    """Change each raw priority by ten slider points and recompute the lower-bound order."""
    feasible = [r for r in results if not r["constraints"]]
    rows = []
    for criterion in CRITERIA:
        for delta in (-10, 10):
            altered = dict(weights)
            altered[criterion] = max(0, min(100, altered[criterion]+delta))
            if altered == weights or not sum(altered.values()) or not feasible:
                continue
            normalized = normalized_weights(altered)
            def bound(result, endpoint):
                return 100*sum(normalized[k]*result["components"][k][endpoint] for k in CRITERIA)
            ordered = sorted(feasible, key=lambda r:(-bound(r,"low"),r["id"]))
            lead = ordered[0]
            resolved = all(bound(lead,"low")>bound(other,"high") for other in ordered[1:])
            rows.append({"Criterion":criterion,"Priority":altered[criterion],"First in order":lead["name"],
                         "Lead changed":lead["id"]!=feasible[0]["id"],"Separated from alternatives":resolved})
    return rows
