"""APEPDCL (Eastern) scraper — WIRED TO LIVE DATA.

Source: https://oms.apeasternpower.com/HTServicesLiveInterruptions
A server-rendered `table.dashboard-table` of currently-interrupted 11kV HT
services. Columns (confirmed 2026-06):

  Sl. No | Circle Name | Division | Sub-Division Name | Section |
  Consumer Number | Short Name | CMD (KVA) | Outage Start Time |
  Outage End Time | Interruption Duration

"Outage End Time" is literally "OPEN" while the service is still out, else a
timestamp. We derive a clean Status/Restored Time from it, expand the 3-letter
Circle code to a full district name (for centroid mapping), and tag each row as
one affected service. Everything else (date parsing, ids) is handled generically
by the normalizer via configs/apepdcl.yaml.
"""

from __future__ import annotations

from base import BaseScraper

# EPDCL circle codes → district name (must match keys in geo/centroids.json).
# Best-effort; unknown codes pass through unmapped (no pin, logged by geo).
CIRCLE_MAP = {
    "SKL": "Srikakulam", "PVP": "Parvathipuram", "VZM": "Vizianagaram",
    "VSP": "Visakhapatnam", "AKP": "Anakapalli", "ASR": "Alluri Sitharama Raju",
    "KKD": "Kakinada", "AML": "Amalapuram", "RJY": "Rajahmundry", "ELR": "Eluru",
}

# Volatile columns dropped before hashing so an outage's id stays stable across
# polls (duration ticks up every scrape; Sl. No re-numbers on sort).
_VOLATILE = ["Sl. No", "Interruption Duration (HH:MM:SS)"]


class ApepdclScraper(BaseScraper):
    config_name = "apepdcl"
    report_url = "https://oms.apeasternpower.com/HTServicesLiveInterruptions"
    table_selector = "table.dashboard-table"

    def scrape(self, page) -> list[dict]:
        rows = super().scrape(page)
        out = []
        for r in rows:
            circle = (r.get("Circle Name") or "").strip()
            if not circle:               # skip blank / totals rows
                continue
            end = (r.get("Outage End Time") or "").strip()
            is_open = end == "" or end.upper() == "OPEN"
            for k in _VOLATILE:
                r.pop(k, None)
            r["District"] = CIRCLE_MAP.get(circle.upper(), circle)
            r["Status"] = "OPEN" if is_open else "CLOSED"
            r["Restored Time"] = "" if is_open else end
            r["Voltage"] = "11kV"
            r["Services"] = "1"          # each HT row = one interrupted service
            out.append(r)
        return out

    # Fixture mirrors the live raw shape so --mock exercises the same path.
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
