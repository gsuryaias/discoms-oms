"""APSPDCL (Southern) scraper.

Portal: https://www.apspdcl.in/OMS/omsweb  (server-rendered, jsessionid)
Menu exposes report names like `performanceDailyReportSection` and
`feederSupplyStatusMap`. Confirm the live-interruption report URL + table
selector via DevTools, then update. Column dialect: configs/apspdcl.yaml.
"""

from __future__ import annotations

from base import BaseScraper


class ApspdclScraper(BaseScraper):
    config_name = "apspdcl"
    # TODO(confirm): e.g. "https://www.apspdcl.in/OMS/feederSupplyStatusMap"
    report_url = "https://www.apspdcl.in/OMS/omsweb"
    table_selector = "table"
    requires_browser = False

    def fetch(self, page=None) -> list[dict]:
        # Not yet wired — see APCPDCL note. Fail cleanly; use --mock for demo.
        raise NotImplementedError("APSPDCL live endpoint not yet confirmed")

    def mock_rows(self) -> list[dict]:
        return [
            {"Circle": "Tirupati", "Division": "Tirupati Urban", "Sub-Division": "Tirupati-1",
             "Section": "AIR Bypass", "Feeder": "11KV AIR Bypass", "Volt": "11KV",
             "Nature": "Unplanned", "Cause of Interruption": "Cable Fault", "No. of Services": "1980",
             "Villages Affected": "Tirupati", "Off Time": "14-06-2026 10:30",
             "Expected On Time": "14-06-2026 13:30", "On Time": "", "Stage": "OFF"},
            {"Circle": "Nellore", "Division": "Nellore", "Sub-Division": "Nellore Town",
             "Section": "Stonehousepet", "Feeder": "11KV Stonehousepet", "Volt": "11KV",
             "Nature": "Unplanned", "Cause of Interruption": "Pole Damage", "No. of Services": "2240",
             "Villages Affected": "Nellore, Stonehousepet", "Off Time": "14-06-2026 09:00",
             "Expected On Time": "", "On Time": "", "Stage": "OFF"},
            {"Circle": "Kadapa", "Division": "Kadapa", "Sub-Division": "Kadapa Town",
             "Section": "Yerramukkapalle", "Feeder": "33KV Yerramukkapalle", "Volt": "33KV",
             "Nature": "Planned", "Cause of Interruption": "Maintenance", "No. of Services": "3100",
             "Villages Affected": "Kadapa", "Off Time": "14-06-2026 06:00",
             "Expected On Time": "14-06-2026 10:00", "On Time": "14-06-2026 09:55", "Stage": "ON"},
            {"Circle": "Anantapur", "Division": "Anantapur", "Sub-Division": "Anantapur-1",
             "Section": "Saibaba Temple", "Feeder": "11KV Saibaba", "Volt": "11KV",
             "Nature": "Unplanned", "Cause of Interruption": "Lightning", "No. of Services": "1430",
             "Villages Affected": "Anantapur", "Off Time": "14-06-2026 11:40",
             "Expected On Time": "14-06-2026 14:00", "On Time": "", "Stage": "OFF"},
            {"Circle": "Kurnool", "Division": "Kurnool", "Sub-Division": "Kurnool Town",
             "Section": "Budhwarpet", "Feeder": "11KV Budhwarpet", "Volt": "11KV",
             "Nature": "Planned", "Cause of Interruption": "Line Shifting", "No. of Services": "690",
             "Villages Affected": "Kurnool", "Off Time": "14-06-2026 05:00",
             "Expected On Time": "14-06-2026 07:30", "On Time": "14-06-2026 07:20", "Stage": "ON"},
        ]
