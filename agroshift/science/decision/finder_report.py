"""Farmer downloads use the same option records the screen renders."""

from dataclasses import asdict
from datetime import datetime, timezone
from html import escape
import json
from agroshift.science.decision.decision import verify_climate


def make_record(dataset, farm, cards, weights, context=None):
    verify_climate(dataset.frame, farm)
    from agroshift.earth_data.farm_context import capabilities
    from agroshift.science.knowledge.knowledge import knowledge_status

    return dict(
        capabilities=capabilities(farm, dataset, cards),
        reference_versions=knowledge_status()["versions"],
        environmental_context=context or {},
        schema="agroshift.crop-finder.v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        farm=asdict(farm),
        location_source="farmer-selected point",
        climate=dataset.provenance,
        coverage_notes=dataset.issues,
        options=cards,
        weights=weights,
        scope="Historical environmental screening. An unassessed requirement is unknown. No field yield or probability is estimated.",
    )


def readable(record):
    def e(x):
        return escape(str(x), quote=True)

    status_labels = {
        "possible": ("● Worth considering", "#E6F4EA", "#17643A", "#8EC9A3"),
        "check": ("▲ Check before planting", "#FDF3DC", "#7A4D00", "#E2B96B"),
        "outside": ("◆ Outside reference range", "#FCECE3", "#8C3D0E", "#E0A080"),
        "blocked": ("✕ Does not fit reported conditions", "#FBE9E7", "#9E2A2B", "#E09891"),
        "unknown": ("○ Not enough information", "#ECEFEA", "#3E4C43", "#C5CCC7"),
    }
    cards = []
    for r in record["options"]:
        st_lbl, bg, fg, bdr = status_labels.get(
            r.get("status", "unknown"), status_labels["unknown"]
        )
        refs = "".join(
            f'<li><a href="{e(v["url"])}">{e(v["title"])}</a>: {e(v["url"])}</li>'
            for v in r["sources"]
        )
        details = "".join(
            f"<li>{e(v)}</li>"
            for v in [
                *r["constraints"],
                *r["details"],
                "Assessed: " + ", ".join(r.get("assessed", [])),
                "Still unknown: " + ", ".join(r.get("unknown", [])),
            ]
        )
        cards.append(
            f'<section class="crop-card">'
            f'<div class="card-head"><h2>{e(r["name"])}</h2>'
            f'<span class="badge" style="background:{bg};color:{fg};border:1px solid {bdr}">{e(st_lbl)}</span></div>'
            f'<p class="summary">{e(r["summary"])}</p>'
            f'<p class="reason">{e(r["reason"])}</p>'
            f'<p class="water"><strong>Water:</strong> {e(r["water"])}</p>'
            f"<ul>{details}</ul>"
            f"<h3>Sources</h3><ul>{refs}</ul></section>"
        )
    farm = record["farm"]
    p = record["climate"]
    where = f'{farm["latitude"]}, {farm["longitude"]} ({farm["country"]})'
    context = {k: v for k, v in record.items() if k != "options"}
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>AgroShift AI · Agricultural Extension Bulletin</title>'
        "<style>"
        "body{font:15px/1.6 'Inter',system-ui,sans-serif;color:#1B2A21;background:#F7F5EF;max-width:56rem;margin:2rem auto;padding:0 1.25rem}"
        "header{background:linear-gradient(135deg,#143D24,#1F5634);color:#FFF;padding:1.5rem 1.75rem;border-radius:14px;margin-bottom:1.5rem}"
        "header h1{font-family:Georgia,serif;margin:0 0 .35rem;font-size:1.75rem}"
        "header p{margin:.2rem 0;color:#E6EFE9;font-size:.92rem}"
        ".scope-box{background:#F5EDDA;border:1px solid #DFC798;color:#5C3D04;padding:.85rem 1.1rem;border-radius:10px;margin-bottom:1.25rem;font-size:.92rem}"
        "section.crop-card{background:#FFF;border:1px solid #D5DDD2;border-radius:12px;padding:1.15rem 1.35rem;margin-bottom:1rem;box-shadow:0 2px 6px rgba(20,45,28,.04);break-inside:avoid}"
        ".card-head{display:flex;justify-content:space-between;align-items:center;gap:.75rem;flex-wrap:wrap;border-bottom:1px solid #E5E8E3;padding-bottom:.5rem;margin-bottom:.6rem}"
        "h2{font-family:Georgia,serif;margin:0;font-size:1.25rem;color:#143D24}"
        "h3{font-size:.95rem;color:#47584C;margin:.75rem 0 .25rem}"
        ".badge{font-size:.78rem;font-weight:700;padding:.2rem .65rem;border-radius:99px}"
        ".water{background:#F0F6FA;border-left:3px solid #1F5F9E;padding:.4rem .7rem;border-radius:4px}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#EFECE2;padding:1rem;border-radius:8px;font-size:.82rem}"
        "li{overflow-wrap:anywhere;margin-bottom:.25rem}a{color:#1F6B3A}"
        "@media print{body{background:#FFF;margin:0}header{background:#143D24;-webkit-print-color-adjust:exact;print-color-adjust:exact}}"
        "</style>"
        f'<header><h1>Your crop options · AgroShift AI</h1><p>{e(where)} · {e(farm["input_origin"])}</p><p>{e(p["mode"])} · {e(p["request"]["start"])}–{e(p["request"]["end"])}</p></header>'
        f'<div class="scope-box">{e(record["scope"])}</div>'
        + "".join(cards)
        + f"<details><summary>Evidence and inputs</summary><pre>{e(json.dumps(context,indent=2))}</pre></details></html>"
    )
