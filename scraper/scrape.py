"""Orchestrator — the entry point GitHub Actions runs every ~15 minutes.

Pipeline:  scrape raw rows -> normalize (per-DISCOM config) -> geo-enrich ->
write docs/data/latest.json (+ a history snapshot for trends).

Design rules that matter:
  * Per-DISCOM isolation. One portal failing must not blank the dashboard. Each
    DISCOM is wrapped in try/except; its error is recorded in the payload and the
    other two still publish. The frontend shows "EPDCL data stale" honestly.
  * --mock runs the FULL pipeline on fixtures with no network, so the dashboard
    has real-shaped data today and CI can smoke-test without hitting the portals.

Usage:
    python scrape.py --mock              # offline, uses each scraper's fixtures
    python scrape.py                     # live, via Playwright (Chromium)
    python scrape.py --discom apepdcl    # just one portal
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib

from dateutil import tz

import geo
import normalizer
from discoms.apcpdcl import ApcpdclScraper
from discoms.apepdcl import ApepdclScraper
from discoms.apspdcl import ApspdclScraper

IST = tz.gettz("Asia/Kolkata")
REPO = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "docs" / "data"
HISTORY_DIR = DATA_DIR / "history"

SCRAPERS = {
    "apepdcl": ApepdclScraper,
    "apcpdcl": ApcpdclScraper,
    "apspdcl": ApspdclScraper,
}


def _now_ist() -> dt.datetime:
    return dt.datetime.now(tz=IST).replace(microsecond=0)


def _run_one(scraper, page, mock: bool, centroids: dict) -> tuple[list[dict], dict]:
    """Returns (records, status_dict) for a single DISCOM. Never raises."""
    name = scraper.discom
    try:
        raw = scraper.scrape(page=page, mock=mock)
        # geo is handled centrally in geo.enrich, so pass no centroids here.
        records = normalizer.normalize(raw, scraper.config, centroids={})
        status = {"status": "ok", "count": len(records), "error": None}
        return records, status
    except Exception as exc:  # noqa: BLE001 — isolation is the whole point
        print(f"[{name}] FAILED: {exc!r}")
        return [], {"status": "error", "count": 0, "error": str(exc)}


def collect(mock: bool, only: str | None) -> dict:
    chosen = {only: SCRAPERS[only]} if only else SCRAPERS
    feeder_coords = geo.load_feeder_coords()
    centroids = geo.load_centroids()

    all_records: list[dict] = []
    discom_status: dict[str, dict] = {}

    # Only spin up a browser if some chosen scraper actually needs one (most use
    # the direct-HTTP strategy, so usually we don't — keeps CI fast and avoids
    # the Chromium-on-runner fragility that an HTTP POST sidesteps entirely).
    need_browser = (not mock) and any(c.requires_browser for c in chosen.values())
    page = browser = pw = None
    if need_browser:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context().new_page()

    try:
        for key, cls in chosen.items():
            scraper = cls()
            records, status = _run_one(scraper, page, mock, centroids)
            status["scraped_at"] = _now_ist().isoformat()
            discom_status[scraper.discom] = status
            all_records.extend(records)
    finally:
        if browser:
            browser.close()
        if pw:
            pw.stop()

    geo.enrich(all_records, feeder_coords, centroids)

    return {
        "generated_at": _now_ist().isoformat(),
        "source": "mock" if mock else "live",
        "discoms": discom_status,
        "totals": {
            "ongoing": sum(r["status"] == "ongoing" for r in all_records),
            "restored": sum(r["status"] == "restored" for r in all_records),
            "all": len(all_records),
        },
        "outages": all_records,
    }


def write_payload(payload: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    latest = DATA_DIR / "latest.json"
    latest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    stamp = _now_ist().strftime("%Y%m%d-%H%M")
    snap = HISTORY_DIR / f"{stamp}.json"
    # store a slim snapshot (counts only) to keep the repo from ballooning
    snap.write_text(json.dumps({
        "generated_at": payload["generated_at"],
        "discoms": payload["discoms"],
        "totals": payload["totals"],
    }, indent=2), encoding="utf-8")
    print(f"[write] {latest.relative_to(REPO)}  ({payload['totals']['all']} outages)")
    print(f"[write] {snap.relative_to(REPO)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="APDISCOMs OMS scraper")
    ap.add_argument("--mock", action="store_true", help="run on fixtures, no network")
    ap.add_argument("--discom", choices=SCRAPERS, help="scrape only one DISCOM")
    args = ap.parse_args()

    payload = collect(mock=args.mock, only=args.discom)
    write_payload(payload)


if __name__ == "__main__":
    main()
