"""Scraper für wg-gesucht.de — Wohnungen und 1-Zimmer-Apartments in München."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import config
from scrapers.base import Scraper, Listing, parse_float


class WgGesuchtScraper(Scraper):
    name = "wg_gesucht"
    base_url = "https://www.wg-gesucht.de"

    def fetch(self) -> list[Listing]:
        results: list[Listing] = []
        # Kategorie 2 = 1-Zi-Wohnung, 3 = Wohnung, 4 = Haus
        for cat_id, cat_name in [(2, "1-zimmer-wohnungen"), (3, "wohnungen")]:
            for page in range(0, 4):
                url = f"{self.base_url}/{cat_name}-in-Muenchen.90.{cat_id}.1.{page}.html"
                resp = self.get(url)
                if not resp:
                    break
                soup = BeautifulSoup(resp.text, "lxml")
                cards = soup.select("div.wgg_card.offer_list_item")
                if not cards:
                    break
                page_results = []
                for card in cards:
                    listing = self._parse_card(card)
                    if listing:
                        page_results.append(listing)
                if not page_results:
                    break
                results.extend(page_results)
                if len(results) >= config.MAX_PER_PLATFORM:
                    return results
        return results

    def _parse_card(self, card) -> Listing | None:
        link = card.select_one('a[href*=".html"]')
        if not link:
            return None
        href = link.get("href", "")
        m = re.search(r"\.(\d{6,})\.html", href)
        if not m:
            return None
        oid = m.group(1)
        url = urljoin(self.base_url, href)
        title = link.get_text(" ", strip=True)[:200] or f"WG-Gesucht {oid}"

        text = card.get_text(" ", strip=True)

        price = None
        for pattern in [r"(\d+)\s*€\s*Warmmiete", r"(\d+)\s*€"]:
            m_p = re.search(pattern, text)
            if m_p:
                price = parse_float(m_p.group(1))
                break

        size_m2 = None
        m_size = re.search(r"(\d+)\s*m²", text)
        if m_size:
            size_m2 = parse_float(m_size.group(1))

        rooms = None
        m_rooms = re.search(r"(\d+(?:[.,]\d+)?)\s*Zimmer", text) or re.search(r"(\d+)-Zi", text)
        if m_rooms:
            rooms = parse_float(m_rooms.group(1))

        addr_el = card.select_one(".col-xs-11")
        address = None
        if addr_el:
            txt = addr_el.get_text(" | ", strip=True)
            parts = [p.strip() for p in txt.split("|") if p.strip()]
            if len(parts) >= 2:
                address = parts[-1]

        img = card.find("img")
        image_url = None
        if img:
            image_url = img.get("src") or img.get("data-src")
            if image_url and image_url.startswith("//"):
                image_url = "https:" + image_url

        return Listing(
            id=f"wg_gesucht_{oid}",
            platform=self.name,
            title=title,
            url=url,
            price=price,
            size_m2=size_m2,
            rooms=rooms,
            address=address,
            image_url=image_url,
        )
