"""Base scraper: the shape every DISCOM scraper shares.

Two fetch strategies are supported, chosen per-DISCOM:

  * HTTP (preferred): the portal's table is populated by a simple POST endpoint
    that returns an HTML fragment. We hit it directly with `requests` — no
    browser, no JS, fast and reliable on CI. Set `requires_browser = False` and
    override `fetch()`.
  * Browser (fallback): for portals that only render via JS with no clean
    endpoint. Set `requires_browser = True`; the orchestrator hands `fetch()` a
    Playwright page and the default navigate/extract reads the first table.

Both strategies return *raw* rows (portal column headers). `transform()` is an
optional per-DISCOM hook to massage raw rows (e.g. expand codes, derive status)
before the generic, config-driven normalizer maps them onto the canonical schema.
Keeping portal quirks here means one portal's change never touches another.
"""

from __future__ import annotations

import pathlib

import yaml

CONFIG_DIR = pathlib.Path(__file__).parent / "configs"


class BaseScraper:
    discom: str = ""
    config_name: str = ""
    report_url: str = ""
    table_selector: str = "table"
    requires_browser: bool = True   # default safe; HTTP scrapers set False

    def __init__(self):
        if not self.config_name:
            raise ValueError(f"{type(self).__name__} must set config_name")
        self.config = self._load_config()
        self.discom = self.config["discom"]

    def _load_config(self) -> dict:
        with (CONFIG_DIR / f"{self.config_name}.yaml").open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    # ---- live fetch (override one strategy) -------------------------------- #
    def fetch(self, page) -> list[dict]:
        """Return raw portal rows. Default = browser strategy."""
        self.navigate(page)
        return self.extract_rows(page)

    # ---- per-DISCOM raw massaging (optional) ------------------------------- #
    def transform(self, rows: list[dict]) -> list[dict]:
        return rows

    # ---- offline fixtures -------------------------------------------------- #
    def mock_rows(self) -> list[dict]:
        return []

    # ---- single entry point the orchestrator calls ------------------------- #
    def scrape(self, page=None, mock: bool = False) -> list[dict]:
        raw = self.mock_rows() if mock else self.fetch(page)
        return self.transform(raw)

    # ---- browser strategy helpers (used only when requires_browser) -------- #
    def navigate(self, page):
        # domcontentloaded + explicit wait for a data row is far more reliable
        # than networkidle, which hangs on portals with keep-alive connections.
        page.goto(self.report_url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_selector(f"{self.table_selector} tbody tr", timeout=45_000)

    def extract_rows(self, page) -> list[dict]:
        return page.evaluate(
            """(selector) => {
                const table = document.querySelector(selector);
                if (!table) return [];
                const rows = [...table.querySelectorAll('tr')];
                if (rows.length < 2) return [];
                const headers = [...rows[0].querySelectorAll('th,td')].map(c => c.innerText.trim());
                return rows.slice(1).map(tr => {
                    const cells = [...tr.querySelectorAll('td')].map(c => c.innerText.trim());
                    const rec = {};
                    headers.forEach((h, i) => { rec[h] = cells[i] ?? null; });
                    return rec;
                }).filter(rec => Object.values(rec).some(v => v));
            }""",
            self.table_selector,
        )
