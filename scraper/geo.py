"""Geo enrichment: attach coordinates so the map can pin outages.

The portals give feeder *names*, almost never lat/lng. So we keep a lookup we
build and maintain ourselves:

  geo/feeder_coords.csv   precise feeder/substation points  -> a real map pin
  geo/centroids.json      circle/district centroids (fallback) -> a coarse pin

Resolution order per outage: feeder coord -> district centroid -> none. We tag
each record with geo_precision so the frontend can render a precise pin vs a
"somewhere in this district" marker honestly. Unmapped feeders are logged so the
CSV is easy to grow over time — that lookup is the project's real moat.
"""

from __future__ import annotations

import csv
import json
import pathlib

GEO_DIR = pathlib.Path(__file__).parent / "geo"


def _norm(s) -> str:
    return (s or "").strip().lower()


def load_feeder_coords() -> dict[tuple[str, str], dict]:
    """(discom, feeder_name) -> {lat, lng}. Keyed case-insensitively."""
    path = GEO_DIR / "feeder_coords.csv"
    coords: dict[tuple[str, str], dict] = {}
    if not path.exists():
        return coords
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                coords[(_norm(row["discom"]), _norm(row["feeder_name"]))] = {
                    "lat": float(row["lat"]),
                    "lng": float(row["lng"]),
                }
            except (KeyError, ValueError):
                continue
    return coords


def load_centroids() -> dict[str, dict]:
    """district(lowercase) -> {lat, lng}."""
    path = GEO_DIR / "centroids.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return {_norm(k): v for k, v in json.load(fh).items()}


def enrich(records: list[dict], feeder_coords: dict, centroids: dict) -> list[dict]:
    unmapped: set[str] = set()
    for rec in records:
        key = (_norm(rec.get("discom")), _norm(rec.get("feeder_name")))
        if key in feeder_coords:
            rec["lat"], rec["lng"] = feeder_coords[key]["lat"], feeder_coords[key]["lng"]
            rec["geo_precision"] = "feeder"
            continue
        centroid = centroids.get(_norm(rec.get("district")))
        if centroid:
            rec["lat"], rec["lng"] = centroid["lat"], centroid["lng"]
            rec["geo_precision"] = "district"
            if rec.get("feeder_name"):
                unmapped.add(f"{rec['discom']} | {rec['district']} | {rec['feeder_name']}")
        else:
            rec["lat"], rec["lng"] = None, None
            rec["geo_precision"] = "none"
    if unmapped:
        print(f"[geo] {len(unmapped)} feeders fell back to district centroid "
              f"(add to feeder_coords.csv for precise pins):")
        for u in sorted(unmapped):
            print(f"       - {u}")
    return records
