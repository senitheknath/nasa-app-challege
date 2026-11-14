"""Location-specific enrichment. Context never changes farmer measurements."""

from concurrent.futures import ThreadPoolExecutor, wait
import copy
from functools import lru_cache
import os
import time
from agroshift.earth_data import providers
from agroshift.science.climate.power import coordinates
from agroshift.science.decision.screening import region_evidence

_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="farm-context")


@lru_cache(maxsize=64)
def _fetch(country, latitude, longitude, offline, hour):
    def cached_then_live(fn, *args):
        archived = fn(*args, offline=True)
        return (
            archived if offline or archived.get("status") == "verified" else fn(*args)
        )

    pending = {
        "soil": _POOL.submit(
            cached_then_live, providers.soil_context, latitude, longitude
        ),
        "calendar": _POOL.submit(cached_then_live, providers.calendar_crops, country),
    }
    done, _ = wait(pending.values(), timeout=12)
    result = {
        "point": [country, latitude, longitude],
        "regional": region_evidence(country),
    }
    for key, future in pending.items():
        if future in done:
            try:
                result[key] = future.result()
                continue
            except Exception:
                pass
        future.cancel()
        result[key] = dict(
            status="unavailable",
            value=None,
            detail="This source is unavailable. You can retry in Explore.",
            kind="modelled" if key == "soil" else "zone reference",
        )
    return result


def location_context(country, latitude, longitude, *, offline=False):
    coordinates(latitude, longitude)
    if not providers._country(country):
        raise ValueError("Unknown country")
    offline = offline or os.getenv("AGROSHIFT_CONTEXT_OFFLINE") == "1"
    return copy.deepcopy(
        _fetch(
            country,
            float(latitude),
            float(longitude),
            offline,
            int(time.monotonic() // 3600),
        )
    )


def capabilities(farm, dataset, cards):
    from agroshift.earth_data.geography import pilot_scope

    environmental = (
        dataset is not None
        and dataset.provenance.get("data_kind") in {"REAL", "VERIFIED_CACHE"}
        and dataset.provenance.get("simulated") is False
    )
    regional = bool(
        farm
        and len(farm.windows) == 2
        and pilot_scope(
            farm.latitude, farm.longitude, farm.country, farm.pilot_confirmed
        )
    )
    return {
        "A": {
            "label": "Environmental history",
            "available": environmental,
            "scope": "Verified NASA grid history at the selected point; no farm weather station.",
        },
        "B": {
            "label": "General crop screening",
            "available": environmental
            and any(c["support"] == "general" for c in cards),
            "scope": "Only the published factors shown for each crop have been compared.",
        },
        "C": {
            "label": "Regional rotation screening",
            "available": environmental and regional,
            "scope": "Two selected windows in confirmed Sri Lankan lowland dry/intermediate fields only.",
        },
        "D": {
            "label": "Field-validated recommendations",
            "available": False,
            "scope": "Independent agricultural field validation has not been performed.",
        },
    }
