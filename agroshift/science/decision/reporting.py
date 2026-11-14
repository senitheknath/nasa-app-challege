"""Portable reports carrying farm inputs, evidence, assumptions and limitations."""
from dataclasses import asdict
from datetime import datetime, timezone
import html
import json
import math
from agroshift.science.climate.climate import seasonal_summary, season_samples
from agroshift.science.decision.decision import KNOWLEDGE, normalized_weights, verify_climate, capability

LIMITATIONS = [
    "Reference-informed prototype, not agronomically calibrated or field-validated.",
    "Historical gridded NASA data is not a farm sensor or a future forecast.",
    "Scores are heuristic preference intervals, not yield, profit or probability.",
    "Unknown components span 0–1; interval overlap means ordering is unresolved.",
    "Water screening, when enabled, uses a user-specified rainfall-use assumption. Paddy total water is not scored.",
    "Cultivar, sowing date, nutrient interpretation, market and disease review remain local decisions.",
]


def report_json(dataset, farm, weights, results, scenario=None):
    verify_climate(dataset.frame, farm)
    scenario_values = scenario or {}
    climate_windows = []
    for window in farm.windows:
        summary = seasonal_summary(season_samples(dataset.frame, window,
                     scenario_values.get("rain_factor", 1), scenario_values.get("temp_delta", 0)))
        values = {k: (None if isinstance(v,float) and not math.isfinite(v) else v)
                  for k,v in summary.items()}
        climate_windows.append({"window": window.label, **values})
    return json.dumps(dict(climate_windows=climate_windows, capability=capability(farm), assessment_scope="Exploratory compatibility index (0–100 points)",
                           input_origin=farm.input_origin,
                           analysis_kind="hypothetical scenario" if scenario is not None else "historical comparison",
                           project="AgroShift AI", generated_at_utc=datetime.now(timezone.utc).isoformat(),
                           farm=asdict(farm), priorities=normalized_weights(weights),
                           provenance=dataset.provenance, data_issues=dataset.issues,
                           scenario=scenario or {"rain_factor": 1, "temp_delta": 0},
                           comparison=results, limitations=LIMITATIONS, references=KNOWLEDGE["sources"],
                           knowledge_version=KNOWLEDGE["version"]), indent=2, allow_nan=False)


def report_html(dataset, farm, weights, results, scenario=None):
    record = json.loads(report_json(dataset, farm, weights, results, scenario))
    esc = html.escape
    cards = []
    for result in results:
        components = "".join(f"<tr><td>{esc(k.title())}</td><td>{v['low']*100:.0f}–{v['high']*100:.0f}</td><td>{esc(v['reason'])}</td></tr>" for k,v in result["components"].items())
        notes = "".join(f"<li>{esc(n)}</li>" for n in result["constraints"]+result["notes"])
        cards.append(f"<section><h2>{esc(result['name'])}{' · Existing plan' if result['baseline'] else ''}</h2><p>{esc(result['status'])} · Preference interval {result['low']:.1f}–{result['high']:.1f}/100</p><table><tr><th>Component</th><th>Interval</th><th>Reason</th></tr>{components}</table><ul>{notes}</ul></section>")
    sources = "".join(f"<li><a href='{esc(s['url'], quote=True)}'>{esc(s['title'])}</a></li>" for s in KNOWLEDGE["sources"].values())
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>AgroShift AI report</title>
<style>body{font:16px/1.6 system-ui;max-width:960px;margin:40px auto;padding:24px;color:#17382d;background:#fafbf7}h1{font-size:40px}section{background:white;padding:24px;margin:20px 0;border:1px solid #cddbd0;border-radius:14px}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:10px;border-bottom:1px solid #dde5dd}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#17614a}@media print{section{break-inside:avoid}body{margin:0}}</style>""" + f"<h1>AgroShift AI</h1><p>Rotation exploration · {esc(record['generated_at_utc'])}</p><p>{farm.latitude:.4f}, {farm.longitude:.4f} · {(str(farm.area_ha) + ' ha') if farm.area_ha is not None else 'Area unknown'} · {esc(dataset.provenance['mode'])}</p>" + "<ul>"+"".join(f"<li>{esc(s)}</li>" for s in LIMITATIONS)+"</ul>"+"".join(cards)+f"<h2>Sources</h2><ul>{sources}<li><a href='https://power.larc.nasa.gov/'>NASA POWER</a></li></ul><h2>Inputs, provenance and reproducibility</h2><pre>{esc(json.dumps({k:v for k,v in record.items() if k != 'comparison'}, indent=2))}</pre></html>"
