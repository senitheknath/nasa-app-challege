"""Scientifically transparent soil unit normalization, pedological interpretation, and measured-vs-modelled reconciliation."""
from __future__ import annotations

import math


SOILGRIDS_PROPERTIES: dict[str, dict] = {
    "phh2o": {
        "name": "Soil pH in H2O",
        "mapped_unit": "pH*10",
        "normalized_unit": "pH (H2O)",
        "scale_divisor": 10.0,
        "bounds": (2.5, 11.0),
        "conversion_method": "raw_value / 10.0 (pH*10 -> pH)",
    },
    "clay": {
        "name": "Clay mass fraction (<0.002 mm)",
        "mapped_unit": "g/kg",
        "normalized_unit": "%",
        "scale_divisor": 10.0,
        "bounds": (0.0, 100.0),
        "conversion_method": "raw_value / 10.0 (g/kg -> %)",
    },
    "sand": {
        "name": "Sand mass fraction (0.05-2 mm)",
        "mapped_unit": "g/kg",
        "normalized_unit": "%",
        "scale_divisor": 10.0,
        "bounds": (0.0, 100.0),
        "conversion_method": "raw_value / 10.0 (g/kg -> %)",
    },
    "silt": {
        "name": "Silt mass fraction (0.002-0.05 mm)",
        "mapped_unit": "g/kg",
        "normalized_unit": "%",
        "scale_divisor": 10.0,
        "bounds": (0.0, 100.0),
        "conversion_method": "raw_value / 10.0 (g/kg -> %)",
    },
    "soc": {
        "name": "Soil organic carbon",
        "mapped_unit": "dg/kg",
        "normalized_unit": "g/kg",
        "scale_divisor": 10.0,
        "bounds": (0.0, 1000.0),
        "conversion_method": "raw_value / 10.0 (dg/kg -> g/kg)",
    },
    "nitrogen": {
        "name": "Total nitrogen",
        "mapped_unit": "cg/kg",
        "normalized_unit": "g/kg",
        "scale_divisor": 100.0,
        "bounds": (0.0, 100.0),
        "conversion_method": "raw_value / 100.0 (cg/kg -> g/kg)",
    },
    "bdod": {
        "name": "Bulk density of fine earth fraction",
        "mapped_unit": "cg/cm³",
        "normalized_unit": "g/cm³",
        "scale_divisor": 100.0,
        "bounds": (0.1, 2.65),
        "conversion_method": "raw_value / 100.0 (cg/cm³ -> g/cm³)",
    },
    "cec": {
        "name": "Cation exchange capacity at pH 7",
        "mapped_unit": "mmol(c)/kg",
        "normalized_unit": "cmol(+)/kg",
        "scale_divisor": 10.0,
        "bounds": (0.0, 200.0),
        "conversion_method": "raw_value / 10.0 (mmol(c)/kg -> cmol(+)/kg)",
    },
    "cfvo": {
        "name": "Volumetric coarse fragments (>2 mm)",
        "mapped_unit": "cm³/dm³ (vol‰)",
        "normalized_unit": "vol%",
        "scale_divisor": 10.0,
        "bounds": (0.0, 100.0),
        "conversion_method": "raw_value / 10.0 (cm³/dm³ -> vol%)",
    },
    "wv0010": {
        "name": "Volumetric water content at -10 kPa",
        "mapped_unit": "0.1 vol% (10⁻³ cm³/cm³)",
        "normalized_unit": "vol%",
        "scale_divisor": 10.0,
        "bounds": (0.0, 100.0),
        "conversion_method": "raw_value / 10.0 (0.1 vol% -> vol%)",
    },
    "wv0033": {
        "name": "Volumetric water content at -33 kPa (field capacity)",
        "mapped_unit": "0.1 vol% (10⁻³ cm³/cm³)",
        "normalized_unit": "vol%",
        "scale_divisor": 10.0,
        "bounds": (0.0, 100.0),
        "conversion_method": "raw_value / 10.0 (0.1 vol% -> vol%)",
    },
    "wv1500": {
        "name": "Volumetric water content at -1500 kPa (permanent wilting point)",
        "mapped_unit": "0.1 vol% (10⁻³ cm³/cm³)",
        "normalized_unit": "vol%",
        "scale_divisor": 10.0,
        "bounds": (0.0, 100.0),
        "conversion_method": "raw_value / 10.0 (0.1 vol% -> vol%)",
    },
}

SOILGRIDS_DEPTHS: dict[str, tuple[int, int]] = {
    "0-5cm": (0, 5),
    "5-15cm": (5, 15),
    "15-30cm": (15, 30),
    "30-60cm": (30, 60),
    "60-100cm": (60, 100),
    "100-200cm": (100, 200),
}

SOILGRIDS_QUANTILES = ("mean", "Q0.05", "Q0.95", "uncertainty")


def normalize_soilgrids_value(prop: str, raw_value: float | int | None) -> dict:
    """Convert raw ISRIC SoilGrids integer value to conventional units while preserving raw provenance."""
    if prop not in SOILGRIDS_PROPERTIES:
        raise ValueError(f"Unsupported SoilGrids property: {prop}")
    spec = SOILGRIDS_PROPERTIES[prop]
    if raw_value is None or (isinstance(raw_value, float) and math.isnan(raw_value)) or raw_value <= -9999:
        return {
            "property": prop,
            "raw_value": raw_value,
            "normalized_value": None,
            "original_unit": spec["mapped_unit"],
            "normalized_unit": spec["normalized_unit"],
            "scale_divisor": spec["scale_divisor"],
            "conversion_method": spec["conversion_method"],
            "valid": False,
        }
    norm = round(float(raw_value) / float(spec["scale_divisor"]), 3)
    low, high = spec["bounds"]
    valid = low <= norm <= high
    return {
        "property": prop,
        "raw_value": raw_value,
        "normalized_value": norm if valid else None,
        "original_unit": spec["mapped_unit"],
        "normalized_unit": spec["normalized_unit"],
        "scale_divisor": spec["scale_divisor"],
        "conversion_method": spec["conversion_method"],
        "valid": valid,
    }


def classify_usda_texture(clay_pct: float | None, sand_pct: float | None, silt_pct: float | None) -> dict:
    """Classify soil texture into the 12 USDA classes and verify compositional closure (clay + sand + silt = 100%)."""
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (clay_pct, sand_pct, silt_pct)):
        return {
            "texture_class": None,
            "compositional_sum_pct": None,
            "compositional_closure_valid": False,
            "normalized_fractions_pct": None,
        }
    raw_sum = float(clay_pct) + float(sand_pct) + float(silt_pct)
    if raw_sum <= 0:
        return {
            "texture_class": None,
            "compositional_sum_pct": round(raw_sum, 2),
            "compositional_closure_valid": False,
            "normalized_fractions_pct": None,
        }
    # Normalize to 100% compositional simplex for USDA triangle lookup
    c = 100.0 * float(clay_pct) / raw_sum
    sa = 100.0 * float(sand_pct) / raw_sum
    si = 100.0 * float(silt_pct) / raw_sum

    if si + 1.5 * c < 15.0:
        tex = "sand"
    elif si + 1.5 * c >= 15.0 and si + 2.0 * c < 30.0:
        tex = "loamy sand"
    elif (c >= 7.0 and c < 20.0 and sa > 52.0 and (si + 2.0 * c) >= 30.0) or (c < 7.0 and si < 50.0 and (si + 2.0 * c) >= 30.0):
        tex = "sandy loam"
    elif c >= 7.0 and c < 27.0 and si >= 28.0 and si < 50.0 and sa <= 52.0:
        tex = "loam"
    elif (si >= 50.0 and (c >= 12.0 and c < 27.0)) or (si >= 50.0 and si < 80.0 and c < 12.0):
        tex = "silt loam"
    elif si >= 80.0 and c < 12.0:
        tex = "silt"
    elif c >= 20.0 and c < 35.0 and si < 28.0 and sa > 45.0:
        tex = "sandy clay loam"
    elif c >= 27.0 and c < 40.0 and sa > 20.0 and sa <= 45.0:
        tex = "clay loam"
    elif c >= 27.0 and c < 40.0 and sa <= 20.0:
        tex = "silty clay loam"
    elif c >= 35.0 and sa > 45.0:
        tex = "sandy clay"
    elif c >= 40.0 and si >= 40.0:
        tex = "silty clay"
    else:
        tex = "clay"

    closure_ok = abs(raw_sum - 100.0) <= 5.0
    return {
        "texture_class": tex,
        "compositional_sum_pct": round(raw_sum, 2),
        "compositional_closure_valid": closure_ok,
        "normalized_fractions_pct": {
            "clay_pct": round(c, 1),
            "sand_pct": round(sa, 1),
            "silt_pct": round(si, 1),
        },
        "closure_note": (
            "Compositional closure verified within ±5%."
            if closure_ok
            else f"Independent SoilGrids raster predictions summed to {raw_sum:.1f}%; renormalized to compositional simplex (100%)."
        ),
    }


def interpret_soil_horizon(horizon: dict) -> dict:
    """Interpret a single depth horizon's physical/chemical properties with pedological safeguards."""
    clay = horizon.get("clay")
    sand = horizon.get("sand")
    silt = horizon.get("silt")
    bdod = horizon.get("bdod")
    soc = horizon.get("soc")
    nitrogen = horizon.get("nitrogen")
    cec = horizon.get("cec")
    cfvo = horizon.get("cfvo")
    wv33 = horizon.get("wv0033")
    wv1500 = horizon.get("wv1500")
    ph = horizon.get("phh2o")

    texture = classify_usda_texture(clay, sand, silt)
    tex_class = texture["texture_class"]

    # Available water capacity (mm/m)
    awc_mm_m = None
    if wv33 is not None and wv1500 is not None and wv33 >= wv1500:
        fine_awc = (float(wv33) - float(wv1500)) * 10.0
        coarse_factor = 1.0 - (float(cfvo) / 100.0) if cfvo is not None else 1.0
        awc_mm_m = round(max(0.0, fine_awc * max(0.0, coarse_factor)), 1)
    elif tex_class is not None:
        # FAO-56 Table 19 indicative AWC by texture class fallback (labeled as pedotransfer fallback)
        fao56_awc = {
            "sand": 70.0,
            "loamy sand": 95.0,
            "sandy loam": 130.0,
            "loam": 165.0,
            "silt loam": 190.0,
            "silt": 195.0,
            "sandy clay loam": 150.0,
            "clay loam": 175.0,
            "silty clay loam": 185.0,
            "sandy clay": 140.0,
            "silty clay": 160.0,
            "clay": 155.0,
        }.get(tex_class, 140.0)
        coarse_factor = 1.0 - (float(cfvo) / 100.0) if cfvo is not None else 1.0
        awc_mm_m = round(fao56_awc * max(0.0, coarse_factor), 1)

    # Bulk density rooting constraint assessment (USDA NRCS texture-dependent thresholds)
    bd_status = "unknown"
    if bdod is not None:
        limit = 1.65
        if tex_class in ("sand", "loamy sand", "sandy loam"):
            limit = 1.80
        elif tex_class in ("clay", "silty clay", "sandy clay", "clay loam", "silty clay loam"):
            limit = 1.47
        if float(bdod) >= limit:
            bd_status = f"elevated_for_texture ({bdod:.2f} g/cm³ >= {limit:.2f} g/cm³ threshold)"
        else:
            bd_status = f"within_normal_range ({bdod:.2f} g/cm³ < {limit:.2f} g/cm³ threshold)"

    cn_ratio = None
    if soc is not None and nitrogen is not None and float(nitrogen) > 0.05:
        cn_ratio = round(float(soc) / float(nitrogen), 1)

    return {
        "ph_h2o": ph,
        "texture": texture,
        "available_water_capacity_mm_m": awc_mm_m,
        "bulk_density_g_cm3": bdod,
        "bulk_density_rooting_context": bd_status,
        "bulk_density_disclaimer": (
            "Bulk density from regional grids informs potential rooting constraints "
            "but does not alone diagnose field-scale mechanical compaction or plough pans."
        ),
        "soc_g_kg": soc,
        "total_nitrogen_g_kg": nitrogen,
        "cn_ratio": cn_ratio,
        "cec_cmol_kg": cec,
        "coarse_fragments_vol_pct": cfvo,
        "fertility_disclaimer": (
            "Soil organic carbon and total nitrogen represent total soil pools, not plant-available mineral N, P, or K. "
            "Do not calculate fertilizer prescriptions from SoilGrids estimates alone."
        ),
        "salinity_ece_ds_m": None,
        "salinity_disclaimer": (
            "Soil salinity (ECe) is not inferred from SoilGrids pH, texture, or CEC; "
            "a direct electrical conductivity measurement is required."
        ),
    }


def interpret_soil_profile(layers_by_depth: dict[str, dict]) -> dict:
    """Compute depth-weighted topsoil (0-30 cm) and subsoil (30-60 cm) summaries and pedological interpretations."""
    if not layers_by_depth:
        return {"status": "empty", "horizons": {}}

    horizon_summaries = {}
    for depth_label, prop_map in layers_by_depth.items():
        flat = {}
        for prop, val in prop_map.items():
            if isinstance(val, dict):
                flat[prop] = val.get("mean") if "mean" in val else val.get("normalized_value")
            else:
                flat[prop] = val
        horizon_summaries[depth_label] = interpret_soil_horizon(flat)

    # Depth-weighted 0-30 cm topsoil summary
    topsoil_depths = [("0-5cm", 5.0), ("5-15cm", 10.0), ("15-30cm", 15.0)]
    weighted_props = {}
    for prop in SOILGRIDS_PROPERTIES:
        num = 0.0
        den = 0.0
        for d_label, thick in topsoil_depths:
            if d_label in layers_by_depth:
                entry = layers_by_depth[d_label].get(prop)
                val = entry.get("mean") if isinstance(entry, dict) and "mean" in entry else (
                    entry.get("normalized_value") if isinstance(entry, dict) else entry
                )
                if val is not None and not (isinstance(val, float) and math.isnan(val)):
                    num += float(val) * thick
                    den += thick
        weighted_props[prop] = round(num / den, 2) if den > 0 else None

    topsoil_interp = interpret_soil_horizon(weighted_props)
    return {
        "status": "verified",
        "topsoil_0_30cm": topsoil_interp,
        "topsoil_0_30cm_properties": weighted_props,
        "horizons": horizon_summaries,
        "scientific_safeguards": [
            topsoil_interp["bulk_density_disclaimer"],
            topsoil_interp["fertility_disclaimer"],
            topsoil_interp["salinity_disclaimer"],
        ],
    }


def reconcile_soil_evidence(
    measured_ph: float | None = None,
    modelled_soil: dict | None = None,
    *,
    measured_metadata: dict | None = None,
    regional_soil: dict | None = None,
    wosis_context: dict | None = None,
) -> dict:
    """Enforce explicit precedence between farmer field measurements and modelled/regional soil estimates."""
    measured_meta = dict(measured_metadata or {})
    has_measured = measured_ph is not None and not (isinstance(measured_ph, float) and math.isnan(measured_ph))

    modelled_ph = None
    modelled_q05 = None
    modelled_q95 = None
    modelled_source = None
    if isinstance(modelled_soil, dict):
        if modelled_soil.get("value") is not None:
            modelled_ph = float(modelled_soil["value"])
            modelled_source = modelled_soil.get("source", "ISRIC SoilGrids 2.0")
        elif isinstance(modelled_soil.get("topsoil_0_30cm"), dict):
            val = modelled_soil["topsoil_0_30cm"].get("ph_h2o")
            if val is not None:
                modelled_ph = float(val)
                modelled_source = modelled_soil.get("source", "ISRIC SoilGrids 2.0")
        q05 = modelled_soil.get("q05")
        q95 = modelled_soil.get("q95")
        if q05 is not None:
            modelled_q05 = float(q05)
        if q95 is not None:
            modelled_q95 = float(q95)

    regional_ph = None
    if isinstance(regional_soil, dict) and regional_soil.get("ph_h2o") is not None:
        regional_ph = float(regional_soil["ph_h2o"])

    disagreement = {
        "evaluated": False,
        "delta_ph": None,
        "outside_90pct_interval": None,
        "meaningful_disagreement": False,
        "summary": None,
    }
    if has_measured and modelled_ph is not None:
        delta = round(float(measured_ph) - modelled_ph, 2)
        outside_pi = False
        if modelled_q05 is not None and modelled_q95 is not None:
            outside_pi = not (modelled_q05 <= float(measured_ph) <= modelled_q95)
        meaningful = abs(delta) >= 0.5 or outside_pi
        disagreement = {
            "evaluated": True,
            "delta_ph": delta,
            "outside_90pct_interval": outside_pi if (modelled_q05 is not None and modelled_q95 is not None) else None,
            "meaningful_disagreement": meaningful,
            "summary": (
                f"Field soil test pH ({float(measured_ph):.1f}) differs from modelled {modelled_source} pH ({modelled_ph:.1f}) "
                f"by {delta:+.1f} pH units. Using measured field value for assessment."
                if meaningful
                else f"Field soil test pH ({float(measured_ph):.1f}) agrees closely with modelled {modelled_source} pH ({modelled_ph:.1f})."
            ),
        }

    if has_measured:
        active_ph = float(measured_ph)
        active_category = "farmer_measurement"
        provisional = False
        precedence_note = (
            "Measured field soil-test pH takes strict precedence over regional modelled estimates. "
            "Modelled estimates are retained for spatial context only."
        )
    elif regional_ph is not None:
        active_ph = regional_ph
        active_category = "modelled_estimate"
        provisional = True
        precedence_note = (
            "No field soil test provided; using USDA NRCS SSURGO map-unit soil estimate provisionally. "
            "Confirm with a local laboratory or field soil test."
        )
    elif modelled_ph is not None:
        active_ph = modelled_ph
        active_category = "modelled_estimate"
        provisional = True
        precedence_note = (
            "No field soil test provided; using ISRIC SoilGrids 2.0 (~250 m) modelled estimate provisionally. "
            "Modelled soil values are never treated as a field soil test."
        )
    else:
        active_ph = None
        active_category = "unknown"
        provisional = False
        precedence_note = "Neither field soil measurement nor modelled soil estimate is available."

    return {
        "active_ph": active_ph,
        "active_source_category": active_category,
        "provisional_modelled_use": provisional,
        "precedence_note": precedence_note,
        "measured": {
            "present": has_measured,
            "data_category": "farmer_measurement" if has_measured else "unknown",
            "ph_h2o": float(measured_ph) if has_measured else None,
            "method": measured_meta.get("method", "Farmer-entered soil test"),
            "sample_date": measured_meta.get("sample_date"),
            "depth_cm": measured_meta.get("depth_cm", "0-20cm"),
        },
        "modelled": {
            "present": modelled_ph is not None,
            "data_category": "modelled_estimate" if modelled_ph is not None else "unknown",
            "ph_h2o": modelled_ph,
            "q05_ph": modelled_q05,
            "q95_ph": modelled_q95,
            "source": modelled_source,
            "spatial_scale": "~250 m global grid (ISRIC SoilGrids 2.0)",
        },
        "regional_survey": regional_soil,
        "wosis_reference_profiles": wosis_context,
        "disagreement": disagreement,
    }
