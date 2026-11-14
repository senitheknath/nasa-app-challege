"""Rebuild the global POWER manifest. Persist raw evidence for each verified row."""
import argparse
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agroshift.global_atlas import GLOBAL_BENCHMARK_HUBS, NASA_STATIONS_SUMMARY_PATH
from agroshift.power import DataError, PowerClient, unpack, request_parameters


def collect(client, key, hub, offline):
    lat, lon = hub["latitude"], hub["longitude"]
    start, end = date(2001, 1, 1), date(2025, 12, 31)
    query = request_parameters(lat, lon, start, end)
    row = dict(hub_key=key, country=hub["country"], latitude=lat, longitude=lon,
               start=query["start"], end=query["end"], data_kind="UNAVAILABLE")
    archive = ROOT / "data" / "stations" / (key + ".json.gz")
    try:
        if key == "anuradhapura":
            path = ROOT / "data/demo_power.json"
            dataset = unpack(json.loads(path.read_text()), "bundled NASA snapshot", query)
        elif archive.exists():
            with gzip.open(archive,"rt",encoding="utf-8") as stream:
                dataset = unpack(json.load(stream), "archived NASA snapshot", query)
            path = archive
        elif offline:
            return row
        else:
            dataset = client.fetch(lat, lon, start, end)
            key_hash = hashlib.sha256(json.dumps(query,sort_keys=True).encode()).hexdigest()
            raw = (client.cache / (key_hash+".json")).read_bytes()
            unpack(json.loads(raw), "archived NASA snapshot", query)
            archive.parent.mkdir(exist_ok=True)
            archive.write_bytes(gzip.compress(raw,mtime=0))
            path = archive
        row.update(data_kind="VERIFIED_CACHE", evidence=path.relative_to(ROOT).as_posix(),
                   sha256=dataset.provenance["sha256"], retrieved_at_utc=dataset.provenance["retrieved_at_utc"],
                   valid_daily_values=int(dataset.frame.count().sum()), calendar_days=len(dataset.frame),
                   mean_temperature_c=dataset.frame.T2M.mean())
    except (DataError, OSError) as error:
        row["issue"] = str(error)
    return row


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline",action="store_true",help="Use archived evidence only")
    args=parser.parse_args()
    client=PowerClient()
    rows=[]
    for key,hub in GLOBAL_BENCHMARK_HUBS.items():
        if key == "custom":
            continue
        row=collect(client,key,hub,args.offline)
        rows.append(row)
        print(key,row["data_kind"],flush=True)
    manifest=pd.DataFrame(rows)
    temporary=NASA_STATIONS_SUMMARY_PATH.with_suffix(".tmp")
    manifest.to_csv(temporary,index=False)
    temporary.replace(NASA_STATIONS_SUMMARY_PATH)
