"""APCPDCL (Central) scraper.

Portal: https://apcpdcl.in/OMS/  (server-rendered, jsessionid)
Live report endpoints observed in the menu include names like
`liveInterruAnalysisg10m`. Confirm the actual report URL + table selector with
DevTools, then update below. Column dialect is handled in configs/apcpdcl.yaml.
"""

from __future__ import annotations

from base import BaseScraper


class ApcpdclScraper(BaseScraper):
    config_name = "apcpdcl"
    # TODO(confirm): e.g. "https://apcpdcl.in/OMS/liveInterruAnalysisg10m"
    report_url = "https://apcpdcl.in/OMS/"
    table_selector = "table"

    def mock_rows(self) -> list[dict]:
        return [
            {"District": "Vijayawada", "Division": "Vijayawada Urban-1", "SubDivision": "Governorpet",
             "Section": "Governorpet", "Feeder Name": "11KV Governorpet", "KV": "11",
             "Outage Type": "U", "Cause": "Cable Fault", "Consumers Affected": "2600",
             "Affected Areas": "Governorpet; Labbipet", "Interruption Time": "14/06/2026 09:40",
             "ETR": "14/06/2026 13:00", "Restored Time": "", "Current Status": "OFF"},
            {"District": "Vijayawada", "Division": "Vijayawada Rural", "SubDivision": "Gannavaram",
             "Section": "Gannavaram", "Feeder Name": "11KV Airport", "KV": "11",
             "Outage Type": "P", "Cause": "Maintenance", "Consumers Affected": "740",
             "Affected Areas": "Gannavaram", "Interruption Time": "14/06/2026 06:30",
             "ETR": "14/06/2026 09:30", "Restored Time": "14/06/2026 09:10", "Current Status": "ON"},
            {"District": "Guntur", "Division": "Guntur-1", "SubDivision": "Brodipet",
             "Section": "Brodipet", "Feeder Name": "11KV Brodipet", "KV": "11",
             "Outage Type": "U", "Cause": "Overload Tripping", "Consumers Affected": "1850",
             "Affected Areas": "Brodipet; Arundelpet", "Interruption Time": "14/06/2026 11:15",
             "ETR": "", "Restored Time": "", "Current Status": "OFF"},
            {"District": "Eluru", "Division": "Eluru", "SubDivision": "Eluru Town",
             "Section": "R R Pet", "Feeder Name": "33KV Eluru Town", "KV": "33",
             "Outage Type": "U", "Cause": "Tree Fall", "Consumers Affected": "4100",
             "Affected Areas": "R R Pet; Powerpet", "Interruption Time": "14/06/2026 08:20",
             "ETR": "14/06/2026 12:00", "Restored Time": "", "Current Status": "OFF"},
            {"District": "Machilipatnam", "Division": "Machilipatnam", "SubDivision": "Bandar",
             "Section": "Bandar Town", "Feeder Name": "11KV Bandar", "KV": "11",
             "Outage Type": "P", "Cause": "Line Shifting", "Consumers Affected": "560",
             "Affected Areas": "Machilipatnam", "Interruption Time": "14/06/2026 05:45",
             "ETR": "14/06/2026 08:00", "Restored Time": "14/06/2026 07:50", "Current Status": "ON"},
        ]
