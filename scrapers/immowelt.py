"""Scraper für immowelt.de (deckt auch immonet.de ab — selbe Datenbasis)."""

from __future__ import annotations

import json
import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

import config
from scrapers.base import Scraper, Listing, parse_float


class ImmoweltScraper(Scraper):
    name = "immowelt"
    base_url = "https://www.immowelt.de"

    def fetch(self) -> list[Listing]:
        results: list[Listing] = []
        for page in range(1, 6):
            params = {
                "d": "true",
                "sd": "DESC",
                "sf": "TIMESTAMP",
                "sp": page,
            }
            url = (
                f"{self.base_url}/liste/muenchen/wohnungen/mieten"
                f"?{urlencode(params)}"
                f"&prma={int(config.MAX_PRICE)}&prmi={int(config.MIN_PRICE)}"
                f"&wflmi={int(config.MIN_SIZE_M2)}"
            )
            resp = self.get(url)
            if not resp:
                break
            soup = BeautifulSoup(resp.text, "lxml")

            # Immowelt hat einen Next.js __NEXT_DATA__ Block mit JSON. Wenn vorhanden: nutzen.
            data_tag = soup.find("script", id="__NEXT_DATA__")
            page_results = []
            if data_tag:
                try:
                    data = json.loads(data_tag.string)
                    page_results = self._extract_from_next_data(data)
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass

            if not page_results:
                page_results = self._extract_from_html(soup)

            if not page_results:
                break
            results.extend(page_results)
            if len(results) >= config.MAX_PER_PLATFORM:
                break
        return results

    def _extract_from_next_data(self, data: dict) -> list[Listing]:
        out: list[Listing] = []
        # Struktur ändert sich gelegentlich; defensiv durch alle "items"/"hits" suchen.
        def walk(obj):
            if isinstance(obj, dict):
                if "id" in obj and ("title" in obj or "headline" in obj) and ("price" in obj or "prices" in obj):
                    out.append(self._listing_from_obj(obj))
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)
        try:
            walk(data.get("props", {}).get("pageProps", {}))
        except Exception:
            pass
        return [l for l in out if l]

    def _listing_from_obj(self, o: dict) -> Listing | None:
        try:
            obj_id = str(o.get("id") or o.get("onlineId") or "")
            if not obj_id:
                return None
            title = o.get("title") or o.get("headline") or ""

            url_part = o.get("url") or o.get("path") or f"/expose/{obj_id}"
            if url_part.startswith("http"):
                url = url_part
            else:
                url = self.base_url + url_part

            price = None
            prices = o.get("prices") or [o.get("price")] if o.get("price") else []
            for p in prices or []:
                if isinstance(p, dict):
                    if p.get("type") in ("rent", "TOTAL_RENT", "BASE_RENT", "rent_total"):
                        price = float(p.get("amount") or p.get("value") or 0) or None
                    elif price is None and (p.get("amount") or p.get("value")):
                        price = float(p.get("amount") or p.get("value"))
                elif isinstance(p, (int, float)):
                    price = float(p)

            size_m2 = None
            rooms = None
            for area in (o.get("areas") or []):
                if not isinstance(area, dict):
                    continue
                if area.get("type") == "LIVING_AREA" or "living" in str(area.get("type", "")).lower():
                    size_m2 = float(area.get("sizeMin") or area.get("size") or 0) or None
                if area.get("type") == "ROOMS" or "room" in str(area.get("type", "")).lower():
                    rooms = float(area.get("sizeMin") or area.get("size") or 0) or None
            size_m2 = size_m2 or (float(o["livingSpace"]) if o.get("livingSpace") else None)
            rooms = rooms or (float(o["rooms"]) if o.get("rooms") else None)

            loc = o.get("location") or o.get("address") or {}
            address_parts = []
            for k in ("street", "city", "postcode", "district", "quarter"):
                if isinstance(loc, dict) and loc.get(k):
                    address_parts.append(str(loc[k]))
            address = ", ".join(address_parts) if address_parts else None

            lat, lng = None, None
            coords = (loc.get("coordinates") if isinstance(loc, dict) else None) or {}
            if coords.get("latitude") and coords.get("longitude"):
                lat = float(coords["latitude"])
                lng = float(coords["longitude"])

            image_url = None
            for media in (o.get("pictures") or o.get("images") or []):
                if isinstance(media, dict):
                    image_url = media.get("imageUri") or media.get("url") or media.get("href")
                    if image_url:
                        break

            return Listing(
                id=f"immowelt_{obj_id}",
                platform=self.name,
                title=title,
                url=url,
                price=price,
                size_m2=size_m2,
                rooms=rooms,
                address=address,
                lat=lat,
                lng=lng,
                image_url=image_url,
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _extract_from_html(self, soup: BeautifulSoup) -> list[Listing]:
        out: list[Listing] = []
        # Fallback: HTML-Parsing über Anchor-Tags mit /expose/ oder /classified-listings/expose
        seen = set()
        for a in soup.select('a[href*="/expose/"]'):
            href = a.get("href", "")
            m = re.search(r"/expose/([a-zA-Z0-9-]+)", href)
            if not m:
                continue
            oid = m.group(1)
            if oid in seen:
                continue
            seen.add(oid)
            url = href if href.startswith("http") else self.base_url + href

            card = a.find_parent(["article", "li", "div"]) or a
            title = (a.get("aria-label") or a.get_text(" ", strip=True))[:200]

            text = card.get_text(" ", strip=True) if card else ""
            price = None
            size_m2 = None
            rooms = None
            m_price = re.search(r"([0-9.,]+)\s*€", text)
            if m_price:
                price = parse_float(m_price.group(1))
            m_size = re.search(r"([0-9.,]+)\s*m²", text)
            if m_size:
                size_m2 = parse_float(m_size.group(1))
            m_rooms = re.search(r"([0-9.,]+)\s*Zi", text)
            if m_rooms:
                rooms = parse_float(m_rooms.group(1))

            img = card.find("img") if card else None
            image_url = None
            if img:
                image_url = img.get("src") or img.get("data-src")

            out.append(Listing(
                id=f"immowelt_{oid}",
                platform=self.name,
                title=title or f"Immowelt-Inserat {oid}",
                url=url,
                price=price,
                size_m2=size_m2,
                rooms=rooms,
                image_url=image_url,
            ))
        return out
