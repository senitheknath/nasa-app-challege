"""Fetch a real, reproducible 2001–2025 Anuradhapura snapshot for offline demos."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import date
import json
from agroshift.power import PowerClient

root = Path(__file__).resolve().parents[1]
client = PowerClient(root / ".cache/power")
result = client.fetch(8.3114, 80.4037, date(2001,1,1), date(2025,12,31))
for path in client.cache.glob("*.json"):
    envelope = json.loads(path.read_text())
    if envelope["request"] == result.provenance["request"]:
        (root / "data/demo_power.json").write_text(json.dumps(envelope), encoding="utf-8")
        print(f"Saved {len(result.frame)} actual days. Sources: {result.provenance['header']['sources']}")
        break
else:
    raise RuntimeError("Successful response was not persisted; no snapshot written.")
