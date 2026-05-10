from .kleinanzeigen import KleinanzeigenScraper
from .immowelt import ImmoweltScraper
from .immoscout import ImmoScoutScraper
from .wohnungsboerse import WohnungsboerseScraper
from .wg_gesucht import WgGesuchtScraper
from .sueddeutsche import SueddeutscheScraper

ALL_SCRAPERS = [
    KleinanzeigenScraper,
    WohnungsboerseScraper,
    ImmoweltScraper,
    WgGesuchtScraper,
    ImmoScoutScraper,
    SueddeutscheScraper,
]
