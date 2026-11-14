"""Independent NASA API learning exercise, not competition application code.

Downloads seven historical days at three public example coordinates. Keeps raw
responses and request metadata for inspection. No agronomic recommendations,
climate modelling, production cache, or competition UI are implemented here.
Run from any directory: python3 preparation/power_access_exercise.py
"""

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


def main() -> int:
    output = Path(__file__).resolve().parent / "evidence"
    output.mkdir(exist_ok=True)
    locations = [
        ("anuradhapura", 8.3114, 80.4037),
        ("nairobi", -1.2921, 36.8219),
        ("ames", 42.0308, -93.6319),
    ]
    parameters = "T2M,T2M_MIN,T2M_MAX,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN"
    expected = {(date(2025, 1, 1) + timedelta(days=n)).strftime("%Y%m%d") for n in range(7)}
    results = []
    for name, latitude, longitude in locations:
        query = dict(parameters=parameters, community="AG", latitude=latitude,
                     longitude=longitude, start="20250101", end="20250107",
                     format="JSON", **{"time-standard": "LST"})
        url = "https://power.larc.nasa.gov/api/temporal/daily/point?" + urlencode(query)
        record = {"location": name, "request": query, "url": url,
                  "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                  "purpose": "independent data-access learning exercise"}
        try:
            with urlopen(url, timeout=30) as response:
                body = response.read()
                record["http_status"] = response.status
            raw_name = name + "_20250101_20250107.json"
            (output / raw_name).write_bytes(body)
            record["raw_file"] = raw_name
            record["sha256"] = hashlib.sha256(body).hexdigest()
            payload = json.loads(body)
            series = payload["properties"]["parameter"]
            fill = payload["header"]["fill_value"]
            record["header"] = payload["header"]
            record["parameter_metadata"] = payload["parameters"]
            record["returned_geometry"] = payload["geometry"]
            record["messages"] = payload.get("messages", [])
            checks = {}
            for parameter in parameters.split(","):
                values = series[parameter]
                valid = [value for key, value in values.items() if key in expected
                         and isinstance(value, (float, int)) and not isinstance(value, bool)
                         and math.isfinite(value) and value != fill]
                checks[parameter] = {"dates_match": set(values) == expected,
                                     "valid_days": len(valid), "expected_days": 7,
                                     "units": payload["parameters"][parameter]["units"]}
            record["checks"] = checks
            record["passed"] = all(check["dates_match"] and check["valid_days"] == 7
                                   for check in checks.values())
        except Exception as error:
            record["passed"] = False
            record["error"] = f"{type(error).__name__}: {error}"
        results.append(record)
        print(json.dumps({key: record.get(key) for key in
                          ("location", "http_status", "passed", "error", "checks")}), flush=True)
    (output / "access_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0 if all(record["passed"] for record in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
