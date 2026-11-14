"""Build the offline point-in-country index from the pinned Natural Earth 5.1.2 geometry."""

import gzip
import hashlib
import json
from pathlib import Path
import requests

URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_50m_admin_0_countries.geojson"


def main():
    r = requests.get(URL, timeout=(8, 90))
    r.raise_for_status()
    items = []
    for item in r.json()["features"]:
        props, geom = item["properties"], item["geometry"]
        code = next(
            (
                props[k]
                for k in ("ISO_A2_EH", "ISO_A2", "WB_A2")
                if len(str(props.get(k, ""))) == 2
            ),
            None,
        )
        if not code:
            continue
        polys = (
            geom["coordinates"]
            if geom["type"] == "MultiPolygon"
            else [geom["coordinates"]]
        )
        for poly in polys:
            rings = [[[round(x, 4), round(y, 4)] for x, y in ring] for ring in poly]
            xs, ys = zip(*rings[0])
            items.append([code, [min(xs), min(ys), max(xs), max(ys)], rings])
    assert len(items) > 1000
    data = dict(
        source=URL, sha256=hashlib.sha256(r.content).hexdigest(), polygons=items
    )
    out = Path(__file__).resolve().parents[1] / "data/boundaries.json.gz"
    out.write_bytes(
        gzip.compress(json.dumps(data, separators=(",", ":")).encode(), mtime=0)
    )
    print(len(items), "polygons;", out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
