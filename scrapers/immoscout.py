"""Scraper für immobilienscout24.de.

⚠️ Hinweis: ImmoScout24 hat starken Bot-Schutz (Akamai/Cloudflare).
In GitHub-Actions-Umgebungen wird der Scraper häufig blockiert (HTTP 403/429
oder Captcha-Seite). Wir versuchen es trotzdem mit realistischen Headers,
schreiben aber keine Fehlschlagsmeldung als kritisch.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

import config
from scrapers.base import Scraper, Listing, parse_float


class ImmoScoutScraper(Scraper):
    name = "immoscout"
    base_url = "https://www.immobilienscout24.de"

    def _default_headers(self) -> dict:
        h = super()._default_headers()
        h["Referer"] = "https://www.immobilienscout24.de/"
        return h

    def fetch(self) -> list[Listing]:
        results: list[Listing] = []
        for page in range(1, 4):
            url = (
                f"{self.base_url}/Suche/de/bayern/muenchen/wohnung-mieten"
                f"?price={int(config.MIN_PRICE)}.0-{int(config.MAX_PRICE)}.0"
                f"&livingspace={int(config.MIN_SIZE_M2)}.0-"
                f"&pagenumber={page}"
                f"&sorting=2"
            )
            resp = self.get(url)
            if not resp:
                break

            soup = BeautifulSoup(resp.text, "lxml")
            page_listings = self._parse(soup)
            if not page_listings:
                break
            results.extend(page_listings)
            if len(results) >= config.MAX_PER_PLATFORM:
                break
        return results

    def _parse(self, soup: BeautifulSoup) -> list[Listing]:
        out: list[Listing] = []
        # ImmoScout liefert oft JSON in einem `IS24.resultList` Skript-Tag.
        for script in soup.find_all("script"):
            text = script.string or ""
            if "resultListModel" in text or "searchResponseModel" in text:
                m = re.search(r"resultListModel\s*[:=]\s*(\{.+?\})\s*[,;]\s*", text, re.DOTALL)
                if m:
                    try:
                        data = json.loads(m.group(1))
                        out.extend(self._from_json(data))
                        if out:
                            return out
                    except json.JSONDecodeError:
                        pass

        # HTML-Fallback: result-list-entry__brand-title-container etc.
        for li in soup.select('li[data-id], article[data-id]'):
            oid = li.get("data-id")
            if not oid:
                continue
            link = li.select_one('a[href*="/expose/"]')
            if not link:
                continue
            href = link.get("href", "")
            url = href if href.startswith("http") else self.base_url + href
            title = link.get_text(" ", strip=True)
            text = li.get_text(" ", strip=True)
            price = parse_float(re.search(r"([0-9.,]+)\s*€", text).group(1)) if re.search(r"([0-9.,]+)\s*€", text) else None
            size_m2 = parse_float(re.search(r"([0-9.,]+)\s*m²", text).group(1)) if re.search(r"([0-9.,]+)\s*m²", text) else None
            rooms = parse_float(re.search(r"([0-9.,]+)\s*Zi", text).group(1)) if re.search(r"([0-9.,]+)\s*Zi", text) else None
            img = li.find("img")
            image_url = (img.get("src") or img.get("data-src")) if img else None
            out.append(Listing(
                id=f"immoscout_{oid}",
                platform=self.name,
                title=title[:200],
                url=url,
                price=price,
                size_m2=size_m2,
                rooms=rooms,
                image_url=image_url,
            ))
        return out

    def _from_json(self, data: dict) -> list[Listing]:
        out: list[Listing] = []
        try:
            entries = data.get("searchResponseModel", {}).get("resultlist.resultlist", {}).get("resultlistEntries", [])
            if entries and isinstance(entries[0], dict):
                items = entries[0].get("resultlistEntry", [])
            else:
                items = []
        except (KeyError, AttributeError):
            return out

        for it in items:
            try:
                obj = it.get("resultlist.realEstate", {})
                oid = str(obj.get("@id", ""))
                if not oid:
                    continue
                title = obj.get("title", "")
                url = f"{self.base_url}/expose/{oid}"

                price = obj.get("price", {}).get("value")
                size_m2 = obj.get("livingSpace")
                rooms = obj.get("numberOfRooms")

                addr = obj.get("address", {})
                address = " ".join(filter(None, [addr.get("street"), addr.get("postcode"), addr.get("city"), addr.get("quarter")]))
                wgs = addr.get("wgs84Coordinate", {})
                lat = wgs.get("latitude")
                lng = wgs.get("longitude")

                image_url = None
                galleryAttachments = obj.get("galleryAttachments", {}).get("attachment", [])
                if galleryAttachments and isinstance(galleryAttachments, list):
                    urls = galleryAttachments[0].get("urls", [])
                    if urls:
                        image_url = urls[0].get("url", {}).get("@href")

                out.append(Listing(
                    id=f"immoscout_{oid}",
                    platform=self.name,
                    title=title,
                    url=url,
                    price=float(price) if price else None,
                    size_m2=float(size_m2) if size_m2 else None,
                    rooms=float(rooms) if rooms else None,
                    address=address or None,
                    lat=float(lat) if lat else None,
                    lng=float(lng) if lng else None,
                    image_url=image_url,
                ))
            except (KeyError, ValueError, TypeError):
                continue
        return out
