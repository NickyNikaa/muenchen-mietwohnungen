"""Zentrale Konfiguration der Suche."""

# Filterkriterien
MIN_PRICE = 600
MAX_PRICE = 1800
MIN_SIZE_M2 = 45

# München-Zentrum (Marienplatz) + Radius in km
CENTER_LAT = 48.1374
CENTER_LNG = 11.5754
RADIUS_KM = 4.0

# Wenn keine Koordinaten ermittelbar sind: Listing trotzdem behalten?
KEEP_WITHOUT_COORDS = True

# Maximale Listings pro Plattform (Schutz vor Endlos-Pagination)
MAX_PER_PLATFORM = 200

# HTTP-Timeout pro Request
REQUEST_TIMEOUT = 25

# User-Agents (rotieren)
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]
