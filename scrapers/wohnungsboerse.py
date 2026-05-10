"""Scraper für wohnungsboerse.net."""

from __future__ import annotations

import re
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

import config
from scrapers.base import Scraper, Listing, parse_float


class WohnungsboerseScraper(Scraper):
    name = "wohnungsboerse"
    base_url = "https://www.wohnungsboerse.net"

    def fetch(self) -> list[Listing]:
        results: list[Listing] = []
        for page in range(1, 6):
            params = {
                "estate_marketing_type": "miete",
                "estate_types[]": "2",  # Wohnung
                "pricetag-from": int(config.MIN_PRICE),
                "pricetag-to": int(config.MAX_PRICE),
                "square_meters-from": int(config.MIN_SIZE_M2),
                "search_field": "München",
                "page": page,
            }
            url = f"{self.base_url}/searches/index?{urlencode(params, doseq=True)}"
            resp = self.get(url)
            if not resp:
                break
            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("article, .estate-card, .estate, .search-result")
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
        link = card.select_one('a[href*="/expose/"]') or card.select_one("a[href]")
        if not link:
            return None
        href = link.get("href", "")
        m = re.search(r"/expose/(\d+)", href) or re.search(r"/(\d{5,})(?:/|$)", href)
        if not m:
            return None
        oid = m.group(1)
        if oid in seen:
            return None
        seen.add(oid)
        url = urljoin(self.base_url, href)

        title = (link.get("title") or link.get_text(" ", strip=True))[:200] or f"Wohnungsbörse {oid}"

        text = card.get_text(" ", strip=True)
        price = None
        m_price = re.search(r"([0-9.,]+)\s*€", text)
        if m_price:
            price = parse_float(m_price.group(1))
        size_m2 = None
        m_size = re.search(r"([0-9.,]+)\s*m²", text)
        if m_size:
            size_m2 = parse_float(m_size.group(1))
        rooms = None
        m_rooms = re.search(r"([0-9.,]+)\s*Zi", text)
        if m_rooms:
            rooms = parse_float(m_rooms.group(1))

        addr = None
        addr_el = card.select_one(".location, .address, [class*='location']")
        if addr_el:
            addr = addr_el.get_text(" ", strip=True)

        img = card.find("img")
        image_url = None
        if img:
            image_url = img.get("src") or img.get("data-src") or img.get("data-original")

        return Listing(
            id=f"wohnungsboerse_{oid}",
            platform=self.name,
            title=title,
            url=url,
            price=price,
            size_m2=size_m2,
            rooms=rooms,
            address=addr,
            image_url=image_url,
        )
