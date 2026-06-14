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

## Live data sources (all three wired)

All three portals run the same Java OMS app and serve their live-interruption
table from a POST that returns an HTML fragment — so we fetch it directly over
HTTP (`scraper/portal_http.py`), no browser needed:

| DISCOM | POST endpoint | body | table |
|--------|---------------|------|-------|
| APEPDCL | `/HTServiceDailyPowerSection` | `DATE=DD-MM-YYYY&CIRCLE=0` | `table.dashboard-table` (11kV HT services) |
| APCPDCL | `/sectionwiseDailyPowerSection` | `DATE=DD-Mon-YYYY&CIRCLE=0&SECTIONID=ALL` | `table#intermediateTable` (11kV feeders) |
| APSPDCL | `/sectionwiseDailyPowerSection` | `date=DD-MM-YYYY&circle=0&division=ALL&section=ALL` | `table#dataTable` (11kV feeders) |

Each portal's column dialect lives in `scraper/configs/*.yaml`; per-portal cleanup
(circle-code expansion, feeder name/id parsing, status) lives in its
`scraper/discoms/*.py`. The portals serve an **incomplete TLS chain**, so
`portal_http` falls back to unverified TLS (safe: public, read-only data) and
retries transient drops. If a portal changes its HTML, only its own module
breaks — the others keep publishing (per-DISCOM `try/except` in `scrape.py` + the
health strip in the UI). `--mock` runs all three on fixtures offline.

## Roadmap / known gaps

- **Feeder coordinates** (`scraper/geo/feeder_coords.csv`): live feeders pin to
  their **district centroid** (hollow "approximate" markers) because the portals
  give no lat/lng. Precise pins require growing this lookup keyed by
  `(discom, feeder_name)`; the scraper logs every unmapped feeder to make it easy.
- **Consumer counts**: EPDCL HT rows count one service each; CPDCL/SPDCL are
  feeder-level with no per-feeder consumer count, so "Consumers affected" reflects
  EPDCL only. Could be enriched from a feeder→consumer-count table later.
- **Trend charts**: `docs/data/history/` accumulates slim snapshots every run —
  wire these into a time-series view (outages over the day/week).
- **District boundary shading**: drop an AP districts GeoJSON into the map for
  choropleth-by-outage-count alongside the feeder pins.

## Legal / etiquette

Public government data, scraped politely (one scheduled pass every ~15 min, a
single page load per portal). Not affiliated with or endorsed by any DISCOM; each
portal remains the authoritative source. Review each site's terms before public
deployment.
