"""Scraper für kleinanzeigen.de (vormals eBay Kleinanzeigen)."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import config
from scrapers.base import Scraper, Listing, parse_float


class KleinanzeigenScraper(Scraper):
    name = "kleinanzeigen"
    base_url = "https://www.kleinanzeigen.de"

    def fetch(self) -> list[Listing]:
        results: list[Listing] = []
        for page in range(1, 6):
            path = (
                f"/s-wohnung-mieten/muenchen/preis:{int(config.MIN_PRICE)}:{int(config.MAX_PRICE)}/"
                f"seite:{page}/c203l6411+wohnung_mieten.qm_d:{int(config.MIN_SIZE_M2)},"
            )
            url = urljoin(self.base_url, path)
            resp = self.get(url)
            if not resp:
                break
            soup = BeautifulSoup(resp.text, "lxml")
            articles = soup.select("article.aditem")
            if not articles:
                break
            for art in articles:
                listing = self._parse_article(art)
                if listing:
                    results.append(listing)
            if len(results) >= config.MAX_PER_PLATFORM:
                break
        return results

    def _parse_article(self, art) -> Listing | None:
        adid = art.get("data-adid")
        if not adid:
            return None
        link = art.select_one("a.ellipsis")
        if not link:
            return None
        title = link.get_text(strip=True)
        href = link.get("href", "")
        url = urljoin(self.base_url, href)

        price_el = art.select_one(".aditem-main--middle--price-shipping--price")
        price = parse_float(price_el.get_text(strip=True)) if price_el else None

        desc_el = art.select_one(".aditem-main--middle--description")
        description = desc_el.get_text(" ", strip=True) if desc_el else ""

        size_m2, rooms = None, None
        for tag in art.select(".simpletag"):
            t = tag.get_text(strip=True)
            if "m²" in t:
                size_m2 = parse_float(t)
            elif "Zimmer" in t or "Zi." in t:
                rooms = parse_float(t)

        loc_el = art.select_one(".aditem-main--top--left")
        address = loc_el.get_text(" ", strip=True) if loc_el else None
        if address:
            address = re.sub(r"\s+", " ", address).replace("Heute, ", "").strip()

        img_el = art.select_one(".imagebox img, .aditem-image img")
        image_url = None
        if img_el:
            image_url = img_el.get("src") or img_el.get("data-imgsrc") or img_el.get("data-src")

        return Listing(
            id=f"kleinanzeigen_{adid}",
            platform=self.name,
            title=title,
            url=url,
            price=price,
            size_m2=size_m2,
            rooms=rooms,
            address=address,
            image_url=image_url,
            description=description,
        )
