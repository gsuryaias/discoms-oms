"""Canonical outage schema shared by every DISCOM.

The whole point of this project is that each DISCOM portal speaks a different
dialect (different column names, district hierarchies, category codes). Nothing
downstream — frontend, map, stats — should ever see those differences. The
normalizer maps every raw record onto the single schema defined here.
"""

from __future__ import annotations

# Canonical fields, in display order. `None` is a valid value for every field
# except the ones in REQUIRED.
FIELDS = [
    "outage_id",          # stable id, "<DISCOM>-<YYYYMMDD>-<seq>"
    "discom",             # APSPDCL | APEPDCL | APCPDCL
    "district",
    "division",
    "subdivision",
    "section",
    "feeder_name",
    "feeder_id",
    "voltage_class",      # 11kV | 33kV | 132kV | LT ...
    "outage_type",        # planned | unplanned
    "cause",
    "affected_consumers", # int
    "affected_villages",  # list[str]
    "lat",                # float | None  (point or district centroid)
    "lng",                # float | None
    "outage_start",       # ISO8601 +05:30
    "expected_restoration",
    "restored_at",
    "status",             # ongoing | restored | unknown
    "scraped_at",         # ISO8601 +05:30, when this record was pulled
]

REQUIRED = ["outage_id", "discom", "status"]

# Allowed normalized vocabularies. value_map in each config funnels raw codes
# into these. Anything unrecognised is kept verbatim so we never lose data.
OUTAGE_TYPES = {"planned", "unplanned"}
STATUSES = {"ongoing", "restored", "unknown"}


def blank_record() -> dict:
    """An empty canonical record with every field present."""
    rec = {f: None for f in FIELDS}
    rec["affected_villages"] = []
    return rec


def coerce(rec: dict) -> dict:
    """Force a record into the canonical shape: all fields present, right types."""
    out = blank_record()
    out.update({k: v for k, v in rec.items() if k in FIELDS})

    # type coercions that the frontend depends on
    if out["affected_consumers"] is not None:
        try:
            out["affected_consumers"] = int(out["affected_consumers"])
        except (TypeError, ValueError):
            out["affected_consumers"] = None
    if not isinstance(out["affected_villages"], list):
        out["affected_villages"] = (
            [out["affected_villages"]] if out["affected_villages"] else []
        )
    for axis in ("lat", "lng"):
        if out[axis] is not None:
            try:
                out[axis] = float(out[axis])
            except (TypeError, ValueError):
                out[axis] = None
    if out["status"] not in STATUSES:
        out["status"] = out["status"] or "unknown"
    return out


def is_valid(rec: dict) -> bool:
    return all(rec.get(f) not in (None, "") for f in REQUIRED)
