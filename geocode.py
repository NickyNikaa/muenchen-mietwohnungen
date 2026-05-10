"""Geocoding via Nominatim (OpenStreetMap) mit lokalem JSON-Cache."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

import requests

CACHE_FILE = Path(__file__).parent / "data" / "geocode_cache.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "muenchen-mietwohnungen-scraper (github project, contact via repo)"


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


_cache = _load_cache()


def geocode(address: str) -> Optional[tuple[float, float]]:
    """Address -> (lat, lng) oder None."""
    if not address:
        return None
    key = address.strip().lower()
    if key in _cache:
        v = _cache[key]
        if v is None:
            return None
        return (v["lat"], v["lng"])

    query = address
    if "münchen" not in query.lower() and "munich" not in query.lower():
        query += ", München"

    try:
        time.sleep(1.1)  # Nominatim Usage Policy: max 1 req/sec
        r = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "de"},
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            if data:
                lat, lng = float(data[0]["lat"]), float(data[0]["lon"])
                _cache[key] = {"lat": lat, "lng": lng}
                _save_cache(_cache)
                return (lat, lng)
    except (requests.RequestException, ValueError, KeyError):
        pass

    _cache[key] = None
    _save_cache(_cache)
    return None


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    from math import radians, sin, cos, asin, sqrt
    R = 6371.0
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 2 * R * asin(sqrt(a))
