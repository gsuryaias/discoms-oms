# AP DISCOMs Outage Dashboard

A unified, near-real-time dashboard tracking power outages across Andhra Pradesh's
three distribution companies — **APEPDCL** (Eastern), **APCPDCL** (Central) and
**APSPDCL** (Southern) — with map, drill-down, and trend history. **No official
APIs required:** it scrapes the same public OMS report pages a browser loads,
normalizes their three different formats into one schema, and serves a static
dashboard from GitHub Pages.

Source portals:
- EPDCL — https://oms.apeasternpower.com/homenew
- CPDCL — https://apcpdcl.in/OMS/
- SPDCL — https://www.apspdcl.in/OMS/omsweb

## How it works

```
GitHub Actions (cron, ~15 min)            GitHub Pages (static, /docs)
┌────────────────────────────┐            ┌──────────────────────────┐
│ scraper/scrape.py          │  commits   │ index.html + JS          │
│  Playwright → raw rows      │  JSON →    │  fetch data/latest.json  │
│  normalize (per-DISCOM cfg) │ ─────────▶ │  Leaflet map · drill ·   │
│  geo-enrich (feeder pins)   │            │  ECharts · auto-refresh  │
│  write docs/data/*.json     │            └──────────────────────────┘
└────────────────────────────┘
```

A static host can't scrape, so **GitHub Actions is the backend**: it runs the
scraper on a schedule and commits the resulting JSON. The page just reads that
JSON and re-fetches it every 60s. "Real-time" is therefore bounded by the cron
cadence (~15 min) — the UI shows a "last updated" stamp so this is honest.

## Repository layout

| Path | Purpose |
|------|---------|
| `scraper/schema.py` | The one canonical outage record every DISCOM maps onto |
| `scraper/normalizer.py` | Config-driven raw → canonical (no per-portal code) |
| `scraper/configs/*.yaml` | Each portal's column dialect + value maps |
| `scraper/discoms/*.py` | Per-portal Playwright scrapers (isolated) |
| `scraper/geo.py`, `scraper/geo/` | Feeder→coords lookup + district centroids |
| `scraper/scrape.py` | Orchestrator; writes `docs/data/latest.json` |
| `docs/` | The static dashboard (GitHub Pages root) |
| `.github/workflows/scrape.yml` | The scheduled scrape + commit |

## Run locally

```bash
cd scraper
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Offline: runs the FULL pipeline on built-in fixtures (no network)
python scrape.py --mock

# Live: real scrape via headless Chromium
python -m playwright install chromium
python scrape.py                 # or: python scrape.py --discom apepdcl

# Preview the dashboard
cd ../docs && python3 -m http.server 8000   # → http://localhost:8000
```

## Deploy to GitHub Pages

1. Push this repo to GitHub.
2. **Settings → Pages →** Source: *Deploy from a branch*, Branch: `main`, Folder:
   `/docs`. Save.
3. **Settings → Actions → General →** Workflow permissions: *Read and write*.
4. The `scrape.yml` workflow then runs every ~15 min, commits fresh data, and
   Pages redeploys. Trigger the first run manually via **Actions → Scrape OMS →
   Run workflow**.

## ⚠️ Before it shows REAL data: confirm the report endpoints

The scrapers currently ship **mock fixtures** plus best-guess report URLs. To go
live you must do this once per portal (it's the only manual step):

1. Open the portal's **live-interruption** report in Chrome with **DevTools →
   Network** open.
2. Note the request URL that returns the outage table, and the table's CSS
   selector.
3. Put them in the matching `scraper/discoms/*.py` (`report_url`,
   `table_selector`). If columns differ from the fixtures, adjust the
   `field_map` in `scraper/configs/*.yaml` — **that's a config edit, not code.**

The architecture is built so one portal changing its HTML breaks only its own
module; the other two keep publishing (see the per-DISCOM `try/except` in
`scrape.py` and the health strip in the UI).

## Roadmap / known gaps

- **Feeder coordinates** (`scraper/geo/feeder_coords.csv`) are seeded for the
  mock feeders only. Precise pins require growing this lookup; unmapped feeders
  fall back to a district centroid and render as hollow "approximate" markers.
  The scraper logs every unmapped feeder to make the CSV easy to extend.
- **Trend charts**: `docs/data/history/` accumulates slim snapshots every run —
  wire these into a time-series view (outages over the day/week).
- **District boundary shading**: drop an AP districts GeoJSON into the map for
  choropleth-by-outage-count alongside the feeder pins.

## Legal / etiquette

Public government data, scraped politely (one scheduled pass every ~15 min, a
single page load per portal). Not affiliated with or endorsed by any DISCOM; each
portal remains the authoritative source. Review each site's terms before public
deployment.
