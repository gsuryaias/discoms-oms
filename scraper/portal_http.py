"""Shared HTTP helpers for the AP OMS portals.

All three DISCOMs run the same Java OMS app: a live-interruptions screen whose
table is filled by a POST that returns an HTML fragment. The portals also share
two quirks this module handles centrally:

  * broken TLS chain (missing intermediate CA) — strict verify fails where a
    browser succeeds; we fall back to unverified TLS. Safe here: public,
    read-only outage data, no credentials sent.
  * flaky handshakes under load — retried with exponential backoff.

Parsing and the feeder-name cleanup are shared too, so each DISCOM module only
declares its endpoint, params and column dialect.
"""

from __future__ import annotations

import re
import time

import requests
import urllib3
from bs4 import BeautifulSoup

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def headers(referer: str) -> dict:
    return {
        "User-Agent": _UA,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": referer,
        "Content-Type": "application/x-www-form-urlencoded",
    }


def post_html(url: str, data: dict, referer: str, attempts: int = 5) -> str:
    """POST and return response text, tolerating the portals' broken TLS chain
    and transient drops. Raises after `attempts` so the DISCOM is marked
    'unreachable' (keeping last good data) rather than wiping to empty."""
    verify, last = True, None
    hdrs = headers(referer)
    for i in range(attempts):
        try:
            resp = requests.post(url, data=data, headers=hdrs, timeout=30, verify=verify)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.SSLError as exc:
            last = exc
            if verify:                       # incomplete chain → retry insecure
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                verify = False
                continue
            time.sleep(1.5 * (2 ** i))
        except requests.exceptions.RequestException as exc:
            last = exc
            time.sleep(1.5 * (2 ** i))
    raise RuntimeError(f"{url} unreachable after {attempts} tries: {last!r}")


def parse_table(html: str, selector: str = "table.dashboard-table") -> list[dict]:
    """First matching table → list of {header: cell}, whitespace-normalized.
    Scripts inside cells (the live duration ticker) are stripped first."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one(selector)
    if not table:
        return []
    for s in table.select("script"):
        s.decompose()
    norm = lambda el: " ".join(el.get_text(" ").split())
    hdrs = [norm(th) for th in table.select("thead th")]
    rows = []
    for tr in table.select("tbody tr"):
        cells = [norm(td) for td in tr.find_all("td")]
        if not any(cells):
            continue
        rows.append({hdrs[i]: cells[i] for i in range(min(len(hdrs), len(cells)))})
    return rows


def split_feeder(s: str) -> tuple[str, str | None, str | None]:
    """'11KV TERALA [ 302211340303 ] [ RURAL ]' -> ('11KV TERALA', '302211340303', '11kV')."""
    s = (s or "").strip()
    up = s.upper()
    volt = "33kV" if up.startswith("33") else "11kV" if up.startswith("11") else None
    name = s.split("[")[0].strip() or s
    m = re.search(r"\[([^\]]+)\]", s)
    fid = m.group(1).strip() if m else None
    return name, fid, volt


def strip_brackets(s: str) -> str:
    """'SD-MACHERLA [ 9440812279 ]' -> 'SD-MACHERLA'."""
    return (s or "").split("[")[0].strip()
