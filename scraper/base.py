"""Base scraper: the parts every DISCOM portal has in common.

All three portals (APEPDCL / APCPDCL / APSPDCL) are server-rendered Java apps
behind a jsessionid. The live-interruption screens we care about render an HTML
<table>. So the common job is always the same:

    open a session -> navigate to the report -> read the table -> rows of dicts

Everything portal-specific (the URL, how you reach the live-interruption report,
the table selector) lives in the per-DISCOM subclass + its YAML config. That is
deliberate: when a portal tweaks its markup, you edit one subclass/config, and
the normalizer, geo, frontend and the other two DISCOMs are untouched.
"""

from __future__ import annotations

import pathlib

import yaml

CONFIG_DIR = pathlib.Path(__file__).parent / "configs"


class BaseScraper:
    # subclasses set these
    discom: str = ""           # APEPDCL | APCPDCL | APSPDCL
    config_name: str = ""      # filename stem under configs/
    report_url: str = ""       # the live-interruption report endpoint
    table_selector: str = "table"  # CSS selector for the data table

    def __init__(self):
        if not self.config_name:
            raise ValueError(f"{type(self).__name__} must set config_name")
        self.config = self._load_config()
        self.discom = self.config["discom"]

    def _load_config(self) -> dict:
        path = CONFIG_DIR / f"{self.config_name}.yaml"
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    # ------------------------------------------------------------------ #
    # The one method subclasses usually override. Default works for any
    # portal whose live report is a single static HTML <table> at a URL.
    # Portals that need clicks/filters first should override navigate().
    # ------------------------------------------------------------------ #
    def navigate(self, page):
        """Drive the page until the data table is on screen. Override as needed."""
        page.goto(self.report_url, wait_until="networkidle", timeout=60_000)
        page.wait_for_selector(self.table_selector, timeout=30_000)

    def extract_rows(self, page) -> list[dict]:
        """Read the first matching <table> into a list of {header: cell} dicts.

        Uses the first row as headers. This is intentionally generic — most of
        these report tables follow it. If a portal uses a non-standard grid,
        override this method in the subclass.
        """
        return page.evaluate(
            """(selector) => {
                const table = document.querySelector(selector);
                if (!table) return [];
                const rows = [...table.querySelectorAll('tr')];
                if (rows.length < 2) return [];
                const headers = [...rows[0].querySelectorAll('th,td')]
                    .map(c => c.innerText.trim());
                return rows.slice(1).map(tr => {
                    const cells = [...tr.querySelectorAll('td')].map(c => c.innerText.trim());
                    const rec = {};
                    headers.forEach((h, i) => { rec[h] = cells[i] ?? null; });
                    return rec;
                }).filter(rec => Object.values(rec).some(v => v));
            }""",
            self.table_selector,
        )

    def scrape(self, page) -> list[dict]:
        """Return raw portal rows (un-normalized). Orchestrator normalizes them."""
        self.navigate(page)
        return self.extract_rows(page)

    # Optional: a fixture of raw rows so the pipeline can run without network.
    def mock_rows(self) -> list[dict]:
        return []
