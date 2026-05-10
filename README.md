# Mietwohnungen München

Sammelt 4× täglich Mietwohnungs-Inserate aus mehreren Portalen, filtert auf
**600–1800 €**, **≥ 45 m²**, **≤ 4 km um Marienplatz** und stellt das Ergebnis
auf einer GitHub-Pages-Website mit Karte und Grid bereit.

## Plattformen

| Plattform | Status | Hinweis |
|---|---|---|
| Kleinanzeigen.de | meist OK | aggressiver Bot-Schutz, ggf. zeitweise Blocks |
| wohnungsboerse.net | OK |  |
| WG-Gesucht.de | OK | Wohnungen + 1-Zi-Apartments |
| Immowelt | best effort | starker Bot-Schutz, oft leer |
| Immonet | über Immowelt | gleiche Datenbasis seit Merger |
| ImmoScout24 | best effort | Akamai-/Captcha-Schutz, aus CI fast immer blockiert |
| SZ Immobilien | best effort | wird von Immowelt gespeist |

> Realistische Erwartung: Kleinanzeigen + Wohnungsbörse + WG-Gesucht decken den
> Großteil ab. ImmoScout/Immowelt sind aus GitHub-Actions schwer zuverlässig
> erreichbar — der Code versucht es, schluckt Fehler aber sauber.

## Lokal testen

```bash
pip install -r requirements.txt
python scrape.py
# danach: docs/data.json öffnen oder docs/ über einen lokalen Webserver bedienen
python -m http.server -d docs 8080
```

## Konfiguration

Filter und Center-Punkt: [`config.py`](config.py).

## Cron-Zeitplan

`.github/workflows/scrape.yml` läuft 4× täglich (UTC 05/10/15/20 ≈ 06–07 / 11–12 / 16–17 / 21–22 Uhr München-Zeit).
