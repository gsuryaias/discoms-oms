"""Config-driven normalizer: raw DISCOM rows -> canonical records.

No DISCOM-specific logic lives here. Everything that differs between portals
(column names, category codes, date formats) is expressed in the per-DISCOM
YAML config, so a column rename on a portal is a config edit, not a code change.
"""

from __future__ import annotations

import datetime as dt
import hashlib

from dateutil import parser as dateparser
from dateutil import tz

import schema

IST = tz.gettz("Asia/Kolkata")


def _now_ist() -> str:
    return dt.datetime.now(tz=IST).replace(microsecond=0).isoformat()


def _to_ist_iso(value, dayfirst: bool) -> str | None:
    """Parse a portal date string into an IST ISO8601 string, or None."""
    if value in (None, "", "-"):
        return None
    if isinstance(value, (int, float)):
        # epoch seconds or millis
        ts = value / 1000 if value > 1e11 else value
        return dt.datetime.fromtimestamp(ts, tz=IST).replace(microsecond=0).isoformat()
    try:
        parsed = dateparser.parse(str(value), dayfirst=dayfirst)
    except (ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed.astimezone(IST).replace(microsecond=0).isoformat()


def _map_value(value, mapping: dict | None):
    """Map a raw categorical value through value_map; pass through if unmapped."""
    if not mapping or value is None:
        return value
    key = str(value).strip()
    return mapping.get(key, mapping.get(key.lower(), value))


def _stable_id(discom: str, raw: dict, scraped_day: str) -> str:
    digest = hashlib.sha1(repr(sorted(raw.items())).encode()).hexdigest()[:8]
    return f"{discom}-{scraped_day}-{digest}"


def normalize(raw_rows: list[dict], config: dict, centroids: dict) -> list[dict]:
    discom = config["discom"]
    field_map = config.get("field_map", {})
    value_map = config.get("value_map", {})
    dayfirst = config.get("date_dayfirst", True)  # Indian portals: DD-MM-YYYY
    scraped_at = _now_ist()
    scraped_day = scraped_at[:10].replace("-", "")

    out: list[dict] = []
    for raw in raw_rows:
        rec = schema.blank_record()
        # apply field_map: canonical_field -> raw_key
        for canon, raw_key in field_map.items():
            if canon in schema.FIELDS:
                rec[canon] = raw.get(raw_key)

        rec["discom"] = discom
        rec["scraped_at"] = scraped_at

        # categorical normalization
        rec["outage_type"] = _map_value(rec["outage_type"], value_map.get("outage_type"))
        rec["status"] = _map_value(rec["status"], value_map.get("status")) or "unknown"
        rec["voltage_class"] = _map_value(rec["voltage_class"], value_map.get("voltage_class"))

        # dates -> IST ISO
        for date_field in ("outage_start", "expected_restoration", "restored_at"):
            rec[date_field] = _to_ist_iso(rec[date_field], dayfirst)

        # villages: split a delimited string into a list
        villages = rec["affected_villages"]
        if isinstance(villages, str):
            rec["affected_villages"] = [v.strip() for v in villages.replace(";", ",").split(",") if v.strip()]

        # geo fallback: if the portal gives no point, use district centroid
        if rec["lat"] is None or rec["lng"] is None:
            c = centroids.get((rec.get("district") or "").strip().lower())
            if c:
                rec["lat"], rec["lng"] = c["lat"], c["lng"]

        # id: prefer the portal's id, else derive a stable one
        if not rec["outage_id"]:
            rec["outage_id"] = _stable_id(discom, raw, scraped_day)
        else:
            rec["outage_id"] = f"{discom}-{rec['outage_id']}"

        rec = schema.coerce(rec)
        if schema.is_valid(rec):
            out.append(rec)
    return out
