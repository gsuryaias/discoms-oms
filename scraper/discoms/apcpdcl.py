"""APCPDCL (Central) scraper — LIVE via direct HTTP.

Live 11kV interruptions (feeder-level). The page performanceDailyReportSection1
fills table#dataTable from:
    POST https://apcpdcl.in/OMS/sectionwiseDailyPowerSection
    body: DATE=<DD-Mon-YYYY>&CIRCLE=0&SECTIONID=ALL

Circle is already a full district name (e.g. PALNADU). Every listed feeder is
currently out, so status is ongoing. transform() cleans the feeder name/id,
derives voltage, and strips the phone-number suffix off the subdivision.
"""

from __future__ import annotations

import datetime as dt

from dateutil import tz

import portal_http as http
from base import BaseScraper

IST = tz.gettz("Asia/Kolkata")
DATA_URL = "https://apcpdcl.in/OMS/sectionwiseDailyPowerSection"
PAGE_URL = "https://apcpdcl.in/OMS/performanceDailyReportSection1"
DATA_URL_33 = "https://apcpdcl.in/OMS/liveInterruption33kvDailyReport"
PAGE_URL_33 = "https://apcpdcl.in/OMS/liveInterruption33kvDailyReportPage"


class ApcpdclScraper(BaseScraper):
    config_name = "apcpdcl"
    requires_browser = False
    report_url = PAGE_URL

    def fetch(self, page=None) -> list[dict]:
        date_str = dt.datetime.now(tz=IST).strftime("%d-%b-%Y")   # 14-Jun-2026
        # 11kV feeders. CPDCL renders the data into #intermediateTable; the
        # visible #dataTable is built client-side and is empty in the response.
        html = http.post_html(DATA_URL, {"DATE": date_str, "CIRCLE": "0", "SECTIONID": "ALL"}, PAGE_URL)
        rows = http.parse_table(html, "table#intermediateTable")
        for r in rows:
            r["_src"] = "11kv"

        # 33kV feeders (separate live report). Isolated: a failure here must not
        # drop the 11kV data, so swallow errors and keep going.
        try:
            html33 = http.post_html(DATA_URL_33, {"DATE": date_str, "CIRCLE": "0"}, PAGE_URL_33)
            rows33 = (http.parse_table(html33, "table#intermediateTable")
                      or http.parse_table(html33, "table#liveInterruptionTable"))
            for r in rows33:
                r["_src"] = "33kv"
            rows.extend(rows33)
        except Exception as exc:  # noqa: BLE001
            print(f"[APCPDCL] 33kV feed skipped: {exc!r}")
        return rows

    def transform(self, rows: list[dict]) -> list[dict]:
        out = []
        for r in rows:
            if r.get("_src") == "33kv":
                if not (r.get("Circle Name") or "").strip():
                    continue
                end = (r.get("Outage End Time") or "").strip()
                is_open = end == "" or end.upper() == "OPEN"
                r["FeederName"] = (r.get("Feeder Name") or "").strip() or r.get("Feeder Id")
                r["FeederId"] = r.get("Feeder Id")
                r["Voltage"] = "33kV"
                r["SubDiv"] = http.strip_brackets(r.get("Sub DivisionName", ""))
                r["Section Name"] = ""
                r["Status"] = "OPEN" if is_open else "CLOSED"
                r["Restored Time"] = "" if is_open else end
                out.append(r)
            else:
                if not (r.get("Circle Name") or "").strip():
                    continue
                name, fid, volt = http.split_feeder(r.get("Feeder Name", ""))
                r["FeederName"], r["FeederId"], r["Voltage"] = name, fid, volt
                r["SubDiv"] = http.strip_brackets(r.get("Sub-Division Name", ""))
                r["Status"] = "OPEN"                   # live report = currently out
                out.append(r)
        return out

    def mock_rows(self) -> list[dict]:
        return [
            {"Feeder Name": "11KV TERALA [ 302211340303 ] [ RURAL (AGL+DOMESTIC) ]",
             "Sub Station Name": "33/11KV MANDADI SUB-STATION", "Circle Name": "PALNADU",
             "Division Name": "MACHERLA", "Sub-Division Name": "SD-MACHERLA [ 9440812279 ]",
             "Section Name": "SEC-VELDURTHI", "Outage Start Time": "14-06-2026 08:31:46",
             "Interruption Reason (Entered in AE Login)": "3-ph/S-ph Phase Changing"},
            {"Feeder Name": "11KV CHANDRALA RURAL FEEDER [ 301311540202 ] [ RURAL (AGL+DOMESTIC) ]",
             "Sub Station Name": "33/11KV PEDAKAKANI", "Circle Name": "GUNTUR",
             "Division Name": "GUNTUR", "Sub-Division Name": "SD-MANGALAGIRI [ 9440811234 ]",
             "Section Name": "SEC-PEDAKAKANI", "Outage Start Time": "14-06-2026 11:02:10",
             "Interruption Reason (Entered in AE Login)": "Conductor cut rf work"},
            {"_src": "33kv", "Circle Name": "NTR", "Division Name": "VIJAYAWADA",
             "Sub DivisionName": "SD-PATAMATA", "Feeder Name": "GANGURU", "Feeder Id": "33107",
             "Outage Start Time": "14-06-2026 12:10:00", "Outage End Time": "OPEN"},
        ]
