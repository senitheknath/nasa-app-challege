"""Six-layer scientifically defensible evidence combination without double-counting correlated models."""
from __future__ import annotations

from agroshift.earth_data.providers import GAEZ_CROP_ID_MAP, gaez_point
from agroshift.science.soil_water.soil import reconcile_soil_evidence


CLASSIFICATION_LABELS = {
    "worth_investigating": "Worth investigating",
    "conditional_compatibility": "Conditional compatibility",
    "important_constraints": "Important constraints identified",
    "not_compatible": "Not compatible with documented conditions",
    "insufficient_evidence": "Insufficient evidence",
}


def build_evidence_layers(
    card: dict,
    farm,
    *,
    crop_identity: dict | None = None,
    previous_crop_identity: dict | None = None,
    water_balance: dict | None = None,
    extremes: dict | None = None,
    modelled_soil: dict | None = None,
    calendar_match: dict | None = None,
) -> dict:
    """Construct the 6-layer scientific evidence synthesis (Layers A–F) for a screened crop option."""
    crop_id = card["id"]
    status = card["status"]
    support = card["support"]
    assessed = list(card.get("assessed", []))
    unknown = list(card.get("unknown", []))
    constraints = list(card.get("constraints", []))

    # Layer A: Eligibility and Scope
    data_categories = {
        "observed_data": [],
        "reanalysis_or_modelled": ["NASA POWER daily agroclimatology (MERRA-2 / CERES)"],
        "published_references": [s.get("title", "") for s in card.get("sources", []) if "NASA" not in s.get("title", "")],
        "farmer_measurements": [],
        "farmer_estimates": [],
        "hypothetical_simulations": [],
        "unknown_information": unknown,
    }
    if farm.ph is not None:
        data_categories["farmer_measurements"].append(f"Measured soil pH ({farm.ph:g})")
    if farm.area_ha is not None:
        data_categories["farmer_measurements"].append(f"Field area ({farm.area_ha:g} ha)")
    if farm.drainage != "unknown":
        data_categories["farmer_estimates"].append(f"Reported field drainage ({farm.drainage})")
    if farm.irrigation != "unknown":
        data_categories["farmer_estimates"].append(f"Irrigation access ({farm.irrigation})")
    if farm.irrigation_mm is not None and farm.irrigation != "rainfed":
        cat_key = "farmer_measurements" if getattr(farm, "irrigation_basis", "") == "measurement" else "farmer_estimates"
        data_categories[cat_key].append(f"Seasonal net irrigation ({farm.irrigation_mm:g} mm)")
    if farm.rain_fraction is not None:
        data_categories["farmer_estimates"].append(f"Usable rainfall fraction ({farm.rain_fraction:g})")

    layer_a = {
        "layer": "A",
        "name": "Eligibility and Scope",
        "support_scope": support,
        "country": farm.country,
        "pilot_confirmed": bool(farm.pilot_confirmed),
        "eligible_for_screening": status in {"possible", "check", "outside", "blocked", "unknown"},
        "data_categories": data_categories,
    }

    # Layer B: Hard Agronomic Constraints
    hard_blockers = []
    if status == "blocked":
        hard_blockers.extend(constraints or [card.get("reason", "Hard agronomic constraint triggered.")])
    if extremes and extremes.get("status") == "verified":
        if extremes.get("seasons_with_frost_fraction", 0.0) >= 0.5 and crop_id in {
            "rice", "maize", "sorghum", "pearl_millet", "finger_millet", "cassava", "sweet_potato",
            "groundnut", "sesame", "cotton", "sugarcane", "banana", "tomato", "common_bean",
        }:
            frost_msg = (
                f"Historical frost (Tmin < 0 °C) occurred in {extremes['seasons_with_frost_fraction']:.0%} "
                "of seasons during this window."
            )
            if frost_msg not in hard_blockers:
                hard_blockers.append(frost_msg)

    layer_b = {
        "layer": "B",
        "name": "Hard Agronomic Constraints",
        "blocked": status == "blocked",
        "hard_constraints": hard_blockers,
        "rule": "Hard physical/biological constraints cannot be compensated by favourable averages in other layers.",
    }

    # Layer C: Environmental Screening (NASA POWER + FAO-56 Water Balance + Extremes + Soil Reconciliation)
    soil_reconciled = reconcile_soil_evidence(farm.ph, modelled_soil)
    if soil_reconciled["provisional_modelled_use"]:
        data_categories["reanalysis_or_modelled"].append("ISRIC SoilGrids 2.0 (~250 m) provisional topsoil pH context")

    layer_c = {
        "layer": "C",
        "name": "Environmental Screening",
        "assessed_factors": assessed,
        "water_balance": water_balance,
        "extreme_weather_risk": extremes,
        "soil_reconciliation": soil_reconciled,
    }

    # Layer D: Correlated Model Context (Non-Double-Counting Safeguard)
    gaez_name = GAEZ_CROP_ID_MAP.get(crop_id)
    water_mode = "irrigated" if farm.irrigation in {"reliable", "supplemental"} else "rainfed"
    gaez_res = (
        gaez_point(farm.latitude, farm.longitude, gaez_name, water_mode)
        if gaez_name
        else {"status": "unavailable", "value": None, "class_code": None}
    )
    if gaez_res.get("status") == "verified":
        data_categories["reanalysis_or_modelled"].append(
            f"FAO/IIASA GAEZ v5 ({gaez_name}, {water_mode}: {gaez_res['value']})"
        )
        code = gaez_res["class_code"]
        if status == "possible" and code in {7, 8}:
            alignment = "divergent_caution"
        elif status in {"outside", "blocked"} and code in {1, 2, 3}:
            alignment = "divergent_local_constraint"
        else:
            alignment = "aligned"
    else:
        alignment = "not_mapped"

    layer_d = {
        "layer": "D",
        "name": "Correlated Model Context",
        "correlated_reanalysis_double_counted": False,
        "gaez_v5": {
            "mapped_crop": gaez_name,
            "water_regime": water_mode,
            "status": gaez_res.get("status"),
            "suitability_class": gaez_res.get("value"),
            "class_code": gaez_res.get("class_code"),
            "alignment_with_screening": alignment,
            "non_double_counting_note": (
                "GAEZ v5 (AgERA5) and NASA POWER (MERRA-2) share correlated historical atmospheric reanalysis inputs. "
                "GAEZ v5 is used strictly as an independent ~10 km agro-ecological cross-check and never added to climate scores."
            ),
        },
    }

    # Layer E: Farmer Constraints, Previous Crop Family & Calendar Alignment
    curr_family = (crop_identity or {}).get("family")
    prev_family = (previous_crop_identity or {}).get("family")
    same_family_warning = None
    if farm.current not in (None, "unknown") and curr_family and prev_family and curr_family == prev_family:
        same_family_warning = (
            f"Shares botanical family ({curr_family}) with previous crop ({farm.current}); "
            "successive same-family planting can increase host-specific pest and disease carryover."
        )

    layer_e = {
        "layer": "E",
        "name": "Farmer Constraints and Field Context",
        "previous_crop": farm.current,
        "crop_family": curr_family,
        "previous_crop_family": prev_family,
        "same_family_succession_warning": same_family_warning,
        "calendar_alignment": calendar_match,
    }

    # Layer F: Final Decision-Support Classification
    if status == "blocked":
        final_code = "not_compatible"
    elif status == "outside":
        final_code = "important_constraints"
    elif status == "unknown":
        final_code = "insufficient_evidence"
    elif status == "check" or alignment == "divergent_caution" or same_family_warning is not None:
        final_code = "conditional_compatibility"
    else:
        final_code = "worth_investigating"

    layer_f = {
        "layer": "F",
        "name": "Final Decision-Support Classification",
        "classification_code": final_code,
        "classification_label": CLASSIFICATION_LABELS[final_code],
        "screening_status": status,
        "decision_support_disclaimer": (
            "Decision-support classification reflects compatibility with checked historical and reference evidence only; "
            "it is never a harvest guarantee or yield prediction."
        ),
    }

    return {
        "classification_code": final_code,
        "classification_label": CLASSIFICATION_LABELS[final_code],
        "layer_a_eligibility": layer_a,
        "layer_b_hard_constraints": layer_b,
        "layer_c_environmental": layer_c,
        "layer_d_correlated_models": layer_d,
        "layer_e_farmer_context": layer_e,
        "layer_f_classification": layer_f,
    }
