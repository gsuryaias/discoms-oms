"""APEPDCL (Eastern) scraper — LIVE via direct HTTP (no browser).

The live-interruptions page (HTServicesLiveInterruptions) fills its table from a
plain POST endpoint:

    POST https://oms.apeasternpower.com/HTServiceDailyPowerSection
    body: DATE=<DD-MM-YYYY>&CIRCLE=0      (CIRCLE=0 = all circles)
    -> HTML fragment containing <table class="dashboard-table">

We hit that endpoint directly with requests + BeautifulSoup. This is what makes
the scrape reliable on GitHub's runners — the earlier browser approach timed out
on Chromium/networkidle. transform() then expands the 3-letter circle code to a
district, derives status from the OPEN/timestamp column, and tags each row as one
affected HT service; the normalizer (configs/apepdcl.yaml) does the rest.
"""

from __future__ import annotations

import datetime as dt
import time

import requests
import urllib3
from bs4 import BeautifulSoup
from dateutil import tz

from base import BaseScraper

IST = tz.gettz("Asia/Kolkata")
DATA_URL = "https://oms.apeasternpower.com/HTServiceDailyPowerSection"
PAGE_URL = "https://oms.apeasternpower.com/HTServicesLiveInterruptions"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "X-Requested-With": "XMLHttpRequest",
    "Referer": PAGE_URL,
    "Content-Type": "application/x-www-form-urlencoded",
}

# EPDCL circle codes → district name (must match keys in geo/centroids.json).
CIRCLE_MAP = {
    "SKL": "Srikakulam", "PVP": "Parvathipuram", "VZM": "Vizianagaram",
    "VSP": "Visakhapatnam", "AKP": "Anakapalli", "ASR": "Alluri Sitharama Raju",
    "KKD": "Kakinada", "AML": "Amalapuram", "RJY": "Rajahmundry", "ELR": "Eluru",
}
# Volatile columns dropped before the normalizer hashes a stable id.
_VOLATILE = ["Sl. No", "Interruption Duration (HH:MM:SS)"]


class ApepdclScraper(BaseScraper):
    config_name = "apepdcl"
    requires_browser = False
    report_url = PAGE_URL

    def fetch(self, page=None) -> list[dict]:
        date_str = dt.datetime.now(tz=IST).strftime("%d-%m-%Y")
        html = _post_with_retry({"DATE": date_str, "CIRCLE": "0"})
        return _parse_table(html)

    def transform(self, rows: list[dict]) -> list[dict]:
        out = []
        for r in rows:
            circle = (r.get("Circle Name") or "").strip()
            if not circle:                       # skip blank / totals rows
                continue
            end = (r.get("Outage End Time") or "").strip()
            is_open = end == "" or end.upper() == "OPEN"
            for k in _VOLATILE:
                r.pop(k, None)
            r["District"] = CIRCLE_MAP.get(circle.upper(), circle)
            r["Status"] = "OPEN" if is_open else "CLOSED"
            r["Restored Time"] = "" if is_open else end
            r["Voltage"] = "11kV"
            r["Services"] = "1"                  # each HT row = one service
            out.append(r)
        return out

    def mock_rows(self) -> list[dict]:
        return [
            {"Circle Name": "SKL", "Division": "PALAKONDA", "Sub-Division Name": "PALAKONDA",
             "Section": "PALAKONDA", "Consumer Number": "SKL443", "Short Name": "M/S. PALAKONDA GOVT. HOSPITAL",
             "CMD (KVA)": "210", "Outage Start Time": "14-06-2026 13:34:38", "Outage End Time": "OPEN"},
            {"Circle Name": "RJY", "Division": "JAGGAMPETA", "Sub-Division Name": "TUNI",
             "Section": "HAMSAVARAM", "Consumer Number": "RJY1037", "Short Name": "VIJAYA SAI PLASTICS",
             "CMD (KVA)": "490", "Outage Start Time": "14-06-2026 08:24:50", "Outage End Time": "OPEN"},
            {"Circle Name": "ELR", "Division": "NARSAPURAM", "Sub-Division Name": "PALAKOL",
             "Section": "PODURU", "Consumer Number": "ELR926", "Short Name": "LAKSHMI SRINIVASA RICE MILL",
             "CMD (KVA)": "120", "Outage Start Time": "14-06-2026 13:32:42",
             "Outage End Time": "14-06-2026 14:05:00"},
        ]


def _post_with_retry(body: dict, attempts: int = 5) -> str:
    """POST the data endpoint robustly.

    The portal serves an incomplete TLS chain (missing intermediate CA), so
    strict verification fails where a browser succeeds. We try verified first,
    then fall back to unverified TLS — safe here because this is public,
    read-only outage data and we send no credentials or secrets. Transient
    connection drops are retried with exponential backoff. Raises if all
    attempts fail, so the orchestrator marks the DISCOM 'unreachable' (keeping
    the last good data) rather than publishing an empty wipe.
    """
    verify = True
    last = None
    for i in range(attempts):
        try:
            resp = requests.post(DATA_URL, data=body, headers=HEADERS,
                                 timeout=30, verify=verify)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.SSLError as exc:
            last = exc
            if verify:                                   # broken chain → go insecure
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                verify = False
                continue                                 # retry immediately
            time.sleep(1.5 * (2 ** i))
        except requests.exceptions.RequestException as exc:
            last = exc
            time.sleep(1.5 * (2 ** i))
    raise RuntimeError(f"APEPDCL endpoint unreachable after {attempts} tries: {last!r}")


def _parse_table(html: str) -> list[dict]:
    """Generic dashboard-table parser: header row -> list of {header: cell}."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.dashboard-table")
    if not table:
        return []
    headers = [th.get_text(strip=True) for th in table.select("thead th")]
    rows = []
    for tr in table.select("tbody tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if not any(cells):
            continue
        rows.append({headers[i]: cells[i] for i in range(min(len(headers), len(cells)))})
    return rows
