"""APEPDCL (Eastern) scraper.

Portal: https://oms.apeasternpower.com/homenew  (server-rendered, jsessionid)
Live-interruption report renders an HTML table. The exact report URL/selector
below is a placeholder — confirm it once with browser DevTools (Network tab,
filter XHR/Doc) on the live "11KV/33KV Live Interruptions" screen, then update
report_url + table_selector. Nothing else changes.
"""

from __future__ import annotations

from base import BaseScraper


class ApepdclScraper(BaseScraper):
    config_name = "apepdcl"
    # TODO(confirm): open the live-interruptions report, copy its URL here.
    report_url = "https://oms.apeasternpower.com/homenew"
    table_selector = "table"  # TODO(confirm): e.g. "#liveInterruptionsGrid table"

    def mock_rows(self) -> list[dict]:
        # Raw rows exactly as the portal's table would yield them (its own
        # column headers). The normalizer maps these via configs/apepdcl.yaml.
        return [
            {"Circle": "Visakhapatnam", "Division": "Vizag Urban", "Sub Division": "Gajuwaka",
             "Section": "Kurmannapalem", "Feeder": "11KV Steel Plant", "Voltage": "11KV",
             "Type": "FORCED", "Reason": "Cable Fault", "Affected Services": "2150",
             "Villages": "Gajuwaka, Kurmannapalem", "Trip Time": "14-06-2026 09:12",
             "Expected Restoration": "14-06-2026 12:30", "Status": "OPEN"},
            {"Circle": "Visakhapatnam", "Division": "Vizag Rural", "Sub Division": "Anakapalle",
             "Section": "Anakapalle Town", "Feeder": "11KV Market", "Voltage": "11KV",
             "Type": "PLANNED", "Reason": "Maintenance", "Affected Services": "880",
             "Villages": "Anakapalle", "Trip Time": "14-06-2026 06:00",
             "Expected Restoration": "14-06-2026 10:00", "Status": "OPEN"},
            {"Circle": "Vizianagaram", "Division": "Vizianagaram", "Sub Division": "Bobbili",
             "Section": "Bobbili", "Feeder": "33KV Bobbili Town", "Voltage": "33KV",
             "Type": "FORCED", "Reason": "Tree Fall", "Affected Services": "3400",
             "Villages": "Bobbili, Therlam", "Trip Time": "14-06-2026 08:45",
             "Expected Restoration": "", "Status": "OPEN"},
            {"Circle": "Srikakulam", "Division": "Srikakulam", "Sub Division": "Amadalavalasa",
             "Section": "Amadalavalasa", "Feeder": "11KV Rural", "Voltage": "11KV",
             "Type": "FORCED", "Reason": "Lightning", "Affected Services": "1200",
             "Villages": "Amadalavalasa", "Trip Time": "14-06-2026 07:20",
             "Expected Restoration": "14-06-2026 09:00", "Status": "CLOSED"},
            {"Circle": "Kakinada", "Division": "Kakinada", "Sub Division": "Kakinada Town",
             "Section": "Sarpavaram", "Feeder": "11KV Sarpavaram", "Voltage": "11KV",
             "Type": "PLANNED", "Reason": "Line Shifting", "Affected Services": "640",
             "Villages": "Sarpavaram", "Trip Time": "14-06-2026 05:30",
             "Expected Restoration": "14-06-2026 08:30", "Status": "CLOSED"},
            {"Circle": "Rajahmundry", "Division": "Rajahmundry", "Sub Division": "RJY Town",
             "Section": "Danavaipeta", "Feeder": "11KV Danavaipeta", "Voltage": "11KV",
             "Type": "FORCED", "Reason": "Transformer Failure", "Affected Services": "1950",
             "Villages": "Danavaipeta", "Trip Time": "14-06-2026 10:05",
             "Expected Restoration": "", "Status": "OPEN"},
        ]
