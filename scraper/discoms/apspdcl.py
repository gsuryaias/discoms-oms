"""APSPDCL (Southern) scraper — LIVE via direct HTTP.

Same OMS app as CPDCL but the page performanceDailyReportSection posts with
lowercase params and a slightly different column set:
    POST https://www.apspdcl.in/OMS/sectionwiseDailyPowerSection
    body: date=<DD-MM-YYYY>&circle=0&division=ALL&section=ALL

Feeder-level, all currently out. Hierarchy is Circle > Division > "Sub Division/
Section" (combined). transform() cleans the feeder name/id and derives voltage.
"""

from __future__ import annotations

import datetime as dt

from dateutil import tz

import portal_http as http
from base import BaseScraper

IST = tz.gettz("Asia/Kolkata")
DATA_URL = "https://www.apspdcl.in/OMS/sectionwiseDailyPowerSection"
PAGE_URL = "https://www.apspdcl.in/OMS/performanceDailyReportSection"


class ApspdclScraper(BaseScraper):
    config_name = "apspdcl"
    requires_browser = False
    report_url = PAGE_URL

    def fetch(self, page=None) -> list[dict]:
        date_str = dt.datetime.now(tz=IST).strftime("%d-%m-%Y")   # 14-06-2026
        html = http.post_html(
            DATA_URL, {"date": date_str, "circle": "0", "division": "ALL", "section": "ALL"}, PAGE_URL)
        return http.parse_table(html, "table#dataTable")

    def transform(self, rows: list[dict]) -> list[dict]:
        out = []
        for r in rows:
            if not (r.get("Circle") or "").strip():
                continue
            name, fid, volt = http.split_feeder(r.get("Feeder Name", ""))
            r["FeederName"], r["FeederId"], r["Voltage"] = name, fid, volt
            r["Status"] = "OPEN"
            out.append(r)
        return out

    def mock_rows(self) -> list[dict]:
        return [
            {"Feeder Name": "11KV WATER WORKS [ 308312240201 - X0476920] [ RWS and PWS ]",
             "Sub Station Name": "33/11 KV NAGARADONA SS", "Circle": "KURNOOL", "Division": "ADONI",
             "Sub Division/ Section": "ALLUR_KNL/ CHIPPAGIRI", "Section/ Sub Station": "9440813395",
             "Outage Start Time": "14-06-2026 03:46:00",
             "Interruption Reason (Entered in AE Login)": ""},
            {"Feeder Name": "11KV GROANDNUT FEEDER [ 401221140307 ] [ RURAL (AGL+DOMESTIC) ]",
             "Sub Station Name": "33/11 KV KADIRI SS", "Circle": "SRISATHYASAI", "Division": "KADIRI",
             "Sub Division/ Section": "KADIRI/ MUTYALACHERUVU", "Section/ Sub Station": "9440812345",
             "Outage Start Time": "14-06-2026 09:15:00",
             "Interruption Reason (Entered in AE Login)": "Line clear for maintenance"},
        ]
