"""Haupt-Runner: läuft alle Scraper, filtert, dedupliziert, schreibt docs/data.json.

Wird von GitHub Actions per Cron aufgerufen.
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import config
from geocode import geocode, haversine_km
from scrapers import ALL_SCRAPERS
from scrapers.base import Listing


ROOT = Path(__file__).parent
DOCS_DATA = ROOT / "docs" / "data.json"
HISTORY_FILE = ROOT / "data" / "history.json"


def load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"first_seen": {}}


def save_history(history: dict) -> None:
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def passes_filter(listing: Listing) -> bool:
    if listing.price is not None:
        if listing.price < config.MIN_PRICE or listing.price > config.MAX_PRICE:
            return False
    if listing.size_m2 is not None and listing.size_m2 < config.MIN_SIZE_M2:
        return False
    return True


def in_radius(listing: Listing) -> bool:
    if listing.lat is None or listing.lng is None:
        return config.KEEP_WITHOUT_COORDS
    dist = haversine_km(config.CENTER_LAT, config.CENTER_LNG, listing.lat, listing.lng)
    return dist <= config.RADIUS_KM


def enrich_coords(listing: Listing) -> None:
    if listing.lat is not None and listing.lng is not None:
        return
    if not listing.address:
        return
    coords = geocode(listing.address)
    if coords:
        listing.lat, listing.lng = coords


def main() -> int:
    started = datetime.now(timezone.utc)
    print(f"=== Run gestartet: {started.isoformat()} ===")
    print(f"Filter: {config.MIN_PRICE}–{config.MAX_PRICE} €, ≥ {config.MIN_SIZE_M2} m², "
          f"{config.RADIUS_KM} km um Marienplatz")

    history = load_history()
    first_seen: dict = history.get("first_seen", {})

    all_listings: dict[str, Listing] = {}
    stats: dict[str, dict] = {}

    for ScraperCls in ALL_SCRAPERS:
        scraper = ScraperCls()
        platform = scraper.name
        print(f"\n--- {platform} ---")
        try:
            raw = scraper.fetch()
        except Exception:
            print(f"  [{platform}] Crash:")
            traceback.print_exc()
            stats[platform] = {"raw": 0, "kept": 0, "error": "crash"}
            continue

        kept = 0
        for listing in raw:
            if not passes_filter(listing):
                continue
            enrich_coords(listing)
            if not in_radius(listing):
                continue
            # Dedup: gleiche URL = gleiches Inserat
            key = listing.url or listing.id
            if key not in all_listings:
                all_listings[key] = listing
                kept += 1

        stats[platform] = {"raw": len(raw), "kept": kept}
        print(f"  [{platform}] {len(raw)} roh, {kept} nach Filter+Radius")

    # First-seen-Tracking für "neu seit letztem Lauf"
    now_iso = started.isoformat()
    for listing in all_listings.values():
        if listing.id not in first_seen:
            first_seen[listing.id] = now_iso

    # last_run timestamp aus History (vor diesem Lauf)
    previous_run = history.get("last_run")

    # Markiere "neu in diesem Lauf" = first_seen >= previous_run
    output = []
    for listing in all_listings.values():
        d = listing.to_dict()
        d["first_seen"] = first_seen[listing.id]
        d["is_new"] = (previous_run is None) or (first_seen[listing.id] >= previous_run)
        output.append(d)

    # Sortierung: neu zuerst, dann nach first_seen desc
    output.sort(key=lambda x: (not x["is_new"], x["first_seen"]), reverse=False)
    output = sorted(output, key=lambda x: x["first_seen"], reverse=True)
    output.sort(key=lambda x: x["is_new"], reverse=True)

    # Schreibe Frontend-Daten
    DOCS_DATA.parent.mkdir(exist_ok=True)
    DOCS_DATA.write_text(
        json.dumps({
            "generated_at": now_iso,
            "previous_run": previous_run,
            "filter": {
                "min_price": config.MIN_PRICE,
                "max_price": config.MAX_PRICE,
                "min_size_m2": config.MIN_SIZE_M2,
                "center_lat": config.CENTER_LAT,
                "center_lng": config.CENTER_LNG,
                "radius_km": config.RADIUS_KM,
            },
            "stats": stats,
            "listings": output,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # History fortschreiben
    history["last_run"] = now_iso
    history["first_seen"] = first_seen
    # Pflege: First-Seen-Einträge älter als 30 Tage und nicht mehr aktiv → löschen
    active_ids = {l.id for l in all_listings.values()}
    pruned = {oid: ts for oid, ts in first_seen.items() if oid in active_ids}
    history["first_seen"] = pruned
    save_history(history)

    print(f"\n=== Fertig: {len(output)} Listings, davon {sum(1 for o in output if o['is_new'])} neu ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
