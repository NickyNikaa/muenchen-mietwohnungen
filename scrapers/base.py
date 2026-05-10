"""Basis-Klassen und Datenmodelle für alle Scraper."""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional

import requests

import config


@dataclass
class Listing:
    id: str
    platform: str
    title: str
    url: str
    price: Optional[float] = None
    size_m2: Optional[float] = None
    rooms: Optional[float] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    image_url: Optional[str] = None
    description: str = ""
    posted_at: Optional[str] = None
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class Scraper:
    """Basis-Scraper. Kindklassen implementieren `fetch()`."""

    name: str = "base"
    base_url: str = ""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(self._default_headers())

    def _default_headers(self) -> dict:
        return {
            "User-Agent": random.choice(config.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        try:
            time.sleep(random.uniform(1.0, 2.5))
            resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT, **kwargs)
            if resp.status_code == 200:
                return resp
            print(f"  [{self.name}] HTTP {resp.status_code} bei {url}")
            return None
        except requests.RequestException as e:
            print(f"  [{self.name}] Fehler bei {url}: {e}")
            return None

    def fetch(self) -> list[Listing]:
        raise NotImplementedError


def parse_float(text: str) -> Optional[float]:
    """Wandelt '1.234,56 €' o.ä. in 1234.56 um."""
    if not text:
        return None
    s = text.strip()
    s = s.replace("€", "").replace("EUR", "").replace("m²", "").replace("qm", "")
    s = s.replace("Zi.", "").replace("Zimmer", "").replace("\xa0", " ").strip()
    digits = []
    for ch in s:
        if ch.isdigit() or ch in ",.":
            digits.append(ch)
        elif ch == " " and digits:
            break
    if not digits:
        return None
    raw = "".join(digits)
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None
