"""SZ Immobilien — Süddeutsche Zeitung Immobilienmarkt.

Hinweis: SZ-Immobilien wird von Immowelt gespeist. Wir crawlen direkt die
SZ-Listing-Seite, um auch Inserate zu erfassen, die ggf. nur dort gepostet werden.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import config
from scrapers.base import Scraper, Listing, parse_float


class SueddeutscheScraper(Scraper):
    name = "sueddeutsche"
    base_url = "https://immobilienmarkt.sueddeutsche.de"

    def fetch(self) -> list[Listing]:
        results: list[Listing] = []
        for page in range(1, 5):
            url = (
                f"{self.base_url}/Wohnungen/mieten/Muenchen/Bayern"
                f"?price-max={int(config.MAX_PRICE)}"
                f"&price-min={int(config.MIN_PRICE)}"
                f"&livingarea-min={int(config.MIN_SIZE_M2)}"
                f"&page={page}"
            )
            resp = self.get(url)
            if not resp:
                break
            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("article, li.classifiedListItem, div.list-item")
            page_results = []
            seen = set()
            for card in cards:
                listing = self._parse_card(card, seen)
                if listing:
                    page_results.append(listing)
            if not page_results:
                break
            results.extend(page_results)
            if len(results) >= config.MAX_PER_PLATFORM:
                break
        return results

    def _parse_card(self, card, seen: set) -> Listing | None:
        link = card.find("a", href=True)
        if not link:
            return None
        href = link["href"]
        m = re.search(r"/(\d{5,})(?:[/?]|$)", href) or re.search(r"id[=-](\d{5,})", href)
        if not m:
            return None
        oid = m.group(1)
        if oid in seen:
            return None
        seen.add(oid)
        url = urljoin(self.base_url, href)

        title = (link.get("title") or link.get_text(" ", strip=True))[:200] or f"SZ Immobilien {oid}"

        text = card.get_text(" ", strip=True)
        price = parse_float(m.group(1)) if (m := re.search(r"([0-9.,]+)\s*€", text)) else None
        size_m2 = parse_float(m.group(1)) if (m := re.search(r"([0-9.,]+)\s*m²", text)) else None
        rooms = parse_float(m.group(1)) if (m := re.search(r"([0-9.,]+)\s*Zi", text)) else None

        img = card.find("img")
        image_url = None
        if img:
            image_url = img.get("src") or img.get("data-src")

        return Listing(
            id=f"sueddeutsche_{oid}",
            platform=self.name,
            title=title,
            url=url,
            price=price,
            size_m2=size_m2,
            rooms=rooms,
            image_url=image_url,
        )
