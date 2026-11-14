"""Refresh dated public reference samples offline from the farmer request path.

Run from the checkout: python scripts/refresh_provider_data.py {gaez,faostat,samples,all}
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PIL import Image
from agroshift.providers import (DATA, GAEZ_CROPS, WATER, calendar_crops, crop_calendars, gaez_context,
                                soil_context, terminology)
from agroshift.provider_http import get

QCL_CATALOG = "https://bulks-faostat.fao.org/production/datasets_E.json"
RES05_SHEET = "https://data.apps.fao.org/catalog/dataset/514c92d5-9e01-4c70-814a-80ea1ca9fe6a/resource/768b08ad-be9c-427a-84be-3a3d6dd7835a/download/_readme_res05.xlsx"
RES05_BASE = "https://storage.googleapis.com/fao-gismgr-gaez-v5-data/DATA/GAEZ-V5/MAPSET/RES05-SIX/"
LEGEND = "https://data.apps.fao.org/gismgr/api/v2/catalog/workspaces/GAEZ-V5/styles/SIX/sld"
COUNTRIES = {"144": "LK", "356": "IN", "404": "KE", "076": "BR", "840": "US", "036": "AU"}
ITEMS = {"56", "15", "27", "83", "116"}


def now():
    return datetime.now(timezone.utc).isoformat()


def download(url, target, limit):
    with get(url, {}, timeout=(5, 45)) as response, target.open("wb") as out:
        size = 0
        for chunk in response.iter_content(262144):
            size += len(chunk)
            if size > limit:
                raise ValueError("Provider download exceeded its size limit.")
            out.write(chunk)


def json_file(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def refresh_faostat(tmp):
    catalog_path = tmp / "catalog.json"
    download(QCL_CATALOG, catalog_path, 2_000_000)
    record = next(x for x in json.loads(catalog_path.read_bytes())["Datasets"]["Dataset"] if x["DatasetCode"] == "QCL")
    url = record["FileLocation"]
    if not url.startswith("https://bulks-faostat.fao.org/production/") or not url.endswith("_(Normalized).zip"):
        raise ValueError("Unexpected QCL distribution URL")
    path = tmp / "qcl.zip"
    download(url, path, 160_000_000)
    rows = []
    seen = set()
    with zipfile.ZipFile(path) as archive:
        member = next(m for m in archive.infolist() if m.filename.endswith("_(Normalized).csv"))
        if member.file_size > 2_000_000_000:
            raise ValueError("Unexpected QCL table size")
        with io.TextIOWrapper(archive.open(member), encoding="utf-8-sig") as table:
            for row in csv.DictReader(table):
                code = row["Area Code (M49)"].lstrip("'")
                if (code not in COUNTRIES or row["Item Code"] not in ITEMS or row["Year"] not in {"2022","2023","2024"}
                        or row["Element Code"] != "5510" or row["Unit"] != "t" or not row["Value"]):
                    continue
                value = float(row["Value"])
                if not 0 <= value < float("inf"):
                    raise ValueError("Invalid FAOSTAT quantity")
                key = (code, row["Item Code"], row["Year"])
                if key in seen:
                    raise ValueError("Duplicate national statistic")
                seen.add(key)
                rows.append(dict(country_code=COUNTRIES[code], country=row["Area"], crop=row["Item"],
                                 year=int(row["Year"]), tonnes=value, flag=row["Flag"], item_code=row["Item Code"]))
        with io.TextIOWrapper(archive.open("Production_Crops_Livestock_E_Flags.csv"), encoding="utf-8-sig") as flags:
            flag_labels = {r["Flag"]: r["Description"] for r in csv.DictReader(flags, skipinitialspace=True)}
        for row in rows:
            row["flag_meaning"] = flag_labels[row["flag"]]
    if not rows:
        raise ValueError("Empty FAOSTAT extract")
    doc = dict(source=url, version=record["DateUpdate"], retrieved_at=now(), zip_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
               license="CC BY 4.0 subject to FAO Statistical Database Terms", rows=rows,
               rows_sha256=hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest())
    staged = tmp / "faostat_qcl_sample.json"
    json_file(staged, doc)
    staged.replace(DATA / staged.name)
    print(f"FAOSTAT: {len(rows)} annual, national crop statistics")


def refresh_gaez(tmp):
    from agroshift.providers import GAEZ_CLASSES, _pixel_at
    sheet = tmp / "catalog.xlsx"
    download(RES05_SHEET, sheet, 20_000_000)
    with zipfile.ZipFile(sheet) as catalog:
        # Confirm filenames against the LIST_FILES sheet, following the official notebook.
        vocab = [''.join(e.itertext()) for e in ET.fromstring(catalog.read("xl/sharedStrings.xml"))]
        names = set()
        with catalog.open("xl/worksheets/sheet2.xml") as src:
            for _, cell in ET.iterparse(src, events=("end",)):
                if cell.tag.endswith("}c") and cell.get("t") == "s":
                    entry = vocab[int(cell.findtext("{*}v"))]
                    if entry.startswith("GAEZ-V5.RES05-SIX.HP0120.AGERA5.HIST."):
                        names.add(entry)
                    cell.clear()
    legend = tmp / "legend.xml"
    download(LEGEND, legend, 50_000)
    classes = {int(float(item.attrib["quantity"])): item.attrib["label"] for item in ET.parse(legend).findall(".//{*}ColorMapEntry")}
    if any(not classes.get(i, "").lower().endswith(label.lower()) for i,label in enumerate(GAEZ_CLASSES)):
        raise ValueError("FAO class legend changed")
    stage = tmp / "grids"
    stage.mkdir()
    records = {}
    for crop, crop_code in GAEZ_CROPS.items():
        for water, code in WATER.items():
            stem = f"GAEZ-V5.RES05-SIX.HP0120.AGERA5.HIST.{crop_code}.{code}"
            if stem not in names:
                raise ValueError(f"{stem} is absent from the official catalogue")
            name = stem + ".tif"
            path = stage / name
            url = RES05_BASE + name
            download(url, path, 5_000_000)
            with Image.open(path) as layer:
                if (layer.mode != "P" or layer.size != (4320,2160) or layer.getextrema()[1] > 9
                        or layer.tag_v2.get(42113) != "0"):
                    raise ValueError("Unexpected GAEZ grid encoding")
                _pixel_at(layer, 8.3, 80.4)
            records[name] = dict(crop=crop, water=water, url=url, retrieved_at=now(),
                                 sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    dest = DATA / "gaez"
    dest.mkdir(exist_ok=True)
    json_file(stage / "manifest.json", records)
    for name in [*records, "manifest.json"]:
        (stage / name).replace(dest / name)
    print(f"GAEZ: {len(records)} verified historical class rasters")


def refresh_samples():
    calls = [(terminology, ("maize","en")), (terminology, ("maíz","es")), (gaez_context, ("AU",)),
             (soil_context, (8.3114,80.4037)),
             (soil_context, (-1.28333,36.81667))]
    for call, args in calls:
        result = call(*args, record=True)
        if result["access"] != "live" or result["value"] in (None, []):
            raise ValueError(f"{call.__name__}{args} failed: {result['detail']}")
        print(call.__name__, args, result["retrieved_at"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=["all","gaez","faostat","samples"])
    choice = parser.parse_args().dataset
    with tempfile.TemporaryDirectory(prefix=".provider-refresh-", dir=DATA) as work:
        if choice in {"gaez","all"}:
            refresh_gaez(Path(work))
        if choice in {"faostat","all"}:
            refresh_faostat(Path(work))
        if choice in {"samples","all"}:
            refresh_samples()
