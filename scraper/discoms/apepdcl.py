"""APEPDCL (Eastern) scraper — LIVE via direct HTTP.

The live-interruptions page fills its table from a plain POST:
    POST https://oms.apeasternpower.com/HTServiceDailyPowerSection
    body: DATE=<DD-MM-YYYY>&CIRCLE=0   -> HTML fragment with table.dashboard-table

These are 11kV HT (bulk) services currently interrupted. transform() expands the
3-letter circle code to a district, derives status from the OPEN/timestamp end
column, and counts one affected service per row.
"""

from __future__ import annotations

import datetime as dt

from dateutil import tz

import portal_http as http
from base import BaseScraper

IST = tz.gettz("Asia/Kolkata")
DATA_URL = "https://oms.apeasternpower.com/HTServiceDailyPowerSection"
PAGE_URL = "https://oms.apeasternpower.com/HTServicesLiveInterruptions"

# EPDCL circle codes → district name (must match keys in geo/centroids.json).
CIRCLE_MAP = {
    "SKL": "Srikakulam", "PVP": "Parvathipuram", "VZM": "Vizianagaram",
    "VSP": "Visakhapatnam", "AKP": "Anakapalli", "ASR": "Alluri Sitharama Raju",
    "KKD": "Kakinada", "AML": "Amalapuram", "RJY": "Rajahmundry", "ELR": "Eluru",
}
_VOLATILE = ["Sl. No", "Interruption Duration (HH:MM:SS)"]


class ApepdclScraper(BaseScraper):
    config_name = "apepdcl"
    requires_browser = False
    report_url = PAGE_URL

    def fetch(self, page=None) -> list[dict]:
        date_str = dt.datetime.now(tz=IST).strftime("%d-%m-%Y")
        html = http.post_html(DATA_URL, {"DATE": date_str, "CIRCLE": "0"}, PAGE_URL)
        return http.parse_table(html, "table.dashboard-table")

    def transform(self, rows: list[dict]) -> list[dict]:
        out = []
        for r in rows:
            circle = (r.get("Circle Name") or "").strip()
            if not circle:
                continue
            end = (r.get("Outage End Time") or "").strip()
            is_open = end == "" or end.upper() == "OPEN"
            for k in _VOLATILE:
                r.pop(k, None)
            r["District"] = CIRCLE_MAP.get(circle.upper(), circle)
            r["Status"] = "OPEN" if is_open else "CLOSED"
            r["Restored Time"] = "" if is_open else end
            r["Voltage"] = "11kV"
            r["Services"] = "1"
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
