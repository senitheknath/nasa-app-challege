"""Small, public reference requests with bounded memory, exact keys and dated archives."""
import base64
import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

import requests

from agroshift.science.climate.power import DataError

_curr = Path(__file__).resolve()
while _curr != _curr.parent:
    if (_curr / "data").is_dir() and (_curr / "agroshift").is_dir():
        ROOT = _curr
        break
    _curr = _curr.parent
else:
    ROOT = Path(__file__).resolve().parents[2]
ARCHIVES = ROOT / "data" / "provider_samples"
MAX_BYTES = 1_000_000
_cache = OrderedDict()
_locks = [threading.Lock() for _ in range(53)]
_guard = threading.Lock()
_cooldown = {}


def _delay(value):
    try:
        return max(0, int(value))
    except (ValueError, TypeError):
        try:
            return max(0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return 60


def get(url, params, *, stream=True, timeout=(3, 6)):
    """Retry transient transport errors once; honour longer rate-limit windows."""
    host = urlsplit(url).netloc
    for attempt in range(2):
        with _guard:
            if time.monotonic() < _cooldown.get(host, 0):
                raise DataError("Provider rate limit. Try again later.")
        try:
            response = requests.get(url, params=params, timeout=timeout, stream=stream)
            if response.status_code == 429:
                with _guard:
                    _cooldown[host] = time.monotonic() + max(1, _delay(response.headers.get("Retry-After")))
                response.close()
                raise DataError("Provider rate limit. Try again later.")
            if response.status_code in (502, 503, 504) and attempt == 0:
                response.close()
                time.sleep(0.25)
                continue
            try:
                response.raise_for_status()
            except requests.RequestException:
                response.close()
                raise
            return response
        except (requests.Timeout, requests.ConnectionError):
            if attempt:
                raise
            time.sleep(0.25)


def request_key(url, params):
    encoded = json.dumps([url, sorted(params.items())], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _read_archive(path, key):
    envelope = json.loads(path.read_text(encoding="utf-8"))
    raw = base64.b64decode(envelope["payload"], validate=True)
    if (envelope["key"] != key or len(raw) > MAX_BYTES
            or hashlib.sha256(raw).hexdigest() != envelope["sha256"]):
        raise ValueError("Archive integrity check failed")
    date = datetime.fromisoformat(envelope["retrieved_at"])
    if date.tzinfo is None:
        raise ValueError("Archive timestamp lacks a timezone")
    return raw, date.isoformat()


def _load_remote(url, params):
    with get(url, params) as response:
        raw = bytearray()
        for chunk in response.iter_content(65536):
            if len(raw) + len(chunk) > MAX_BYTES:
                raise DataError("Reference response was too large.")
            raw.extend(chunk)
        return bytes(raw), datetime.now(timezone.utc).isoformat()


def _archive_path(key):
    return ARCHIVES / (key + ".json")


def save_archive(url, params, raw, retrieved):
    """Called only by the maintainer's refresh script after parsing the response."""
    key = request_key(url, params)
    payload = {"url": url, "params": params, "key": key, "retrieved_at": retrieved,
               "sha256": hashlib.sha256(raw).hexdigest(), "payload": base64.b64encode(raw).decode()}
    ARCHIVES.mkdir(parents=True, exist_ok=True)
    path = _archive_path(key)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def reference(url, params, parse, *, kind, detail, source=None, offline=False, record=False):
    base = {"kind": kind, "source": source or url, "detail": detail}
    key = request_key(url, params)
    with _locks[int(key[:8], 16) % len(_locks)]:
        with _guard:
            cached = _cache.get(key)
        error = "No saved record for this request."
        if not offline and not record and cached and time.monotonic() < cached[2]:
            raw, retrieved, _ = cached
            access = "cache"
        else:
            raw = None
            if not offline:
                try:
                    body, retrieved = _load_remote(url, params)
                    value = parse(body)
                    if record:
                        save_archive(url, params, body, retrieved)
                    with _guard:
                        _cache[key] = (body, retrieved, time.monotonic() + 86400)
                        _cache.move_to_end(key)
                        while len(_cache) > 64:
                            _cache.popitem(last=False)
                    return dict(base, status="verified", value=value, retrieved_at=retrieved, access="live")
                except (OSError, ValueError, KeyError, TypeError, requests.RequestException) as exc:
                    error = "Provider request or validation failed."
                    if isinstance(exc, DataError):
                        error = str(exc)
            if cached:
                raw, retrieved, _ = cached
                access = "cache"
            else:
                try:
                    raw, retrieved = _read_archive(_archive_path(key), key)
                    access = "archive"
                except (OSError, ValueError, KeyError, TypeError):
                    pass
        if raw is not None:
            try:
                return dict(base, status="verified", value=parse(raw), retrieved_at=retrieved, access=access)
            except (OSError, ValueError, KeyError, TypeError):
                error = "Saved record could not be verified."
        return dict(base, status="unavailable", value=None, retrieved_at=None, access=None, detail=error)
