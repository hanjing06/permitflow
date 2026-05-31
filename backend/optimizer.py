"""
Phase 3 optimizer for PermitFlow.

The offline artifact builder uses this module to:
  - normalize mixed Toronto Open Data feeds into one permit schema
  - match flexible candidate permits to fixed city anchor windows
  - cluster leftover candidates with space/time DBSCAN
  - synthesize naive and optimized timelines
  - compute headline metrics for the Phase 4 UI

FastAPI still imports the legacy helpers at the bottom of this file. They now
delegate to the same canonical model so the current frontend keeps working.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from sklearn.cluster import DBSCAN as SklearnDBSCAN
except Exception:  # pragma: no cover - exercised on machines without sklearn
    SklearnDBSCAN = None

try:
    from .street_norm import normalize_street
except ImportError:  # pragma: no cover - exercised when optimizer.py is run as a script
    from street_norm import normalize_street  # type: ignore[no-redef]


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
ARTIFACT_DIR = DATA_DIR / "artifacts"

TORONTO_LAT_REF = 43.7
LAT_M_PER_DEG = 111_320.0
LON_M_PER_DEG = LAT_M_PER_DEG * math.cos(math.radians(TORONTO_LAT_REF))

TODAY = date.fromisoformat(os.getenv("PERMITFLOW_TODAY", "2026-05-30"))
WINDOW_DAYS = int(os.getenv("PERMITFLOW_WINDOW_DAYS", "90"))
ANCHOR_MATCH_METERS = float(os.getenv("PERMITFLOW_ANCHOR_MATCH_M", "250"))
ANCHOR_MATCH_DAYS = int(os.getenv("PERMITFLOW_ANCHOR_MATCH_DAYS", "35"))
DBSCAN_EPS_METERS = float(os.getenv("PERMITFLOW_EPS_M", "220"))
DBSCAN_TIME_M_PER_DAY = float(os.getenv("PERMITFLOW_TIME_M_PER_DAY", "9"))
DBSCAN_MIN_SAMPLES = int(os.getenv("PERMITFLOW_MIN_SAMPLES", "2"))
CONFLICT_DISTANCE_METERS = float(os.getenv("PERMITFLOW_CONFLICT_M", "500"))
CONFLICT_THRESHOLD = float(os.getenv("PERMITFLOW_CONFLICT_THRESHOLD", "0.15"))
LANE_DAY_COST = int(os.getenv("PERMITFLOW_LANE_DAY_COST", "15000"))
# Per-mobilization savings used by anchor_program clusters. Same-street city road
# permits that get coordinated don't save a full trench (the work happens anyway)
# — they save crew dispatch / mobilization overhead. $5K is the conservative end
# of the $5K-25K range for municipal road-crew mobilization.
MOBILIZATION_SAVINGS = int(os.getenv("PERMITFLOW_MOBILIZATION_SAVINGS", "5000"))
STREET_CLUSTER_WINDOW_DAYS = int(os.getenv("PERMITFLOW_STREET_WINDOW_DAYS", "60"))

ANCHOR_FILES = {
    "road_reconstruction": "road_reconstruction.csv",
    "road_resurfacing": "road_resurfacing.csv",
    "sidewalk_construction": "sidewalk_construction.csv",
}
CANDIDATE_FILES = {
    "utility_cut": "utility_cuts.csv",
    "building_permit": "building_permits.csv",
}


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def clean_text(value, fallback=""):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return fallback
    return str(value).replace("&lt;br&gt;", " | ").strip() or fallback


def parse_date(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def parse_year_window(row):
    year = pd.to_numeric(row.get("START_YEAR"), errors="coerce")
    if pd.isna(year):
        return None, None
    start = date(int(year), 6, 1)
    duration_text = str(row.get("DURATION/ Construction Timeline", ""))
    end = date(int(year), 10, 31)
    if "Q1" in duration_text:
        start = date(int(year), 1, 1)
    elif "Q2" in duration_text:
        start = date(int(year), 4, 1)
    elif "Q3" in duration_text:
        start = date(int(year), 7, 1)
    elif "Q4" in duration_text:
        start = date(int(year), 10, 1)
    if "Q1" in duration_text.split("-")[-1]:
        end = date(int(year), 3, 31)
    elif "Q2" in duration_text.split("-")[-1]:
        end = date(int(year), 6, 30)
    elif "Q3" in duration_text.split("-")[-1]:
        end = date(int(year), 9, 30)
    elif "Q4" in duration_text.split("-")[-1]:
        end = date(int(year), 12, 31)
    return start, end


def extract_lat_lon(geometry_str):
    try:
        geo = json.loads(geometry_str)
        coords = geo["coordinates"]
        if not coords:
            return None, None
        midpoint = coords[len(coords) // 2]
        return float(midpoint[1]), float(midpoint[0])
    except Exception:
        return None, None


def permit_geometry(permit):
    half = 0.00045
    lon = permit["lon"]
    lat = permit["lat"]
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon - half, lat - half],
            [lon + half, lat - half],
            [lon + half, lat + half],
            [lon - half, lat + half],
            [lon - half, lat - half],
        ]],
    }


def distance_m(a, b):
    dx = (float(a["lon"]) - float(b["lon"])) * LON_M_PER_DEG
    dy = (float(a["lat"]) - float(b["lat"])) * LAT_M_PER_DEG
    return math.hypot(dx, dy)


def date_gap_days(a, b):
    if a["end_date"] < b["start_date"]:
        return (b["start_date"] - a["end_date"]).days
    if b["end_date"] < a["start_date"]:
        return (a["start_date"] - b["end_date"]).days
    return 0


def lane_days(start_date, end_date):
    return max((end_date - start_date).days + 1, 1)


def serialize_date(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def serialize_permit(permit):
    out = dict(permit)
    out["start_date"] = serialize_date(out["start_date"])
    out["end_date"] = serialize_date(out["end_date"])
    return out


def artifact_path(name):
    return ARTIFACT_DIR / name


def _coerce_geo_id(value):
    """Stringify Toronto centerline GEO_ID, dropping the trailing '.0' pandas attaches.

    Returns None for missing / NaN / empty values. Used for Phase-8 Layer-2
    GEO_ID exact-match clustering.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    try:
        return str(int(float(text)))
    except (TypeError, ValueError):
        return text


def _permit_from_open_toronto(row, source="road_reconstruction", role="anchor"):
    lat, lon = extract_lat_lon(row.get("geometry"))
    if lat is None or lon is None:
        return None
    start, end = parse_year_window(row)
    if start is None or end is None:
        return None
    raw_location = row.get("LOCATION")
    norm = normalize_street(clean_text(raw_location) if raw_location is not None else None)
    return {
        "permit_id": f"{source}:{row.get('_id')}",
        "source": source,
        "role": role,
        "street_name": clean_text(raw_location, "Unknown location"),
        "work_type": clean_text(row.get("PROJECT"), "Road work"),
        "status": clean_text(row.get("STATUS"), "Unknown"),
        "start_date": start,
        "end_date": end,
        "lane_days": lane_days(start, end),
        "lat": float(lat),
        "lon": float(lon),
        "normalized_street": norm["normalized"],
        "direction": norm["direction"],
        "geo_id": _coerce_geo_id(row.get("GEO_ID")),
    }


def _permit_from_simple_csv(row, source="utility_cut", role="candidate"):
    """Build a permit dict from one of three candidate schemas.

    1. utility_cuts.csv  → GEO_ID + DISPLAY_DESC + PROPOSED_FROM_DATE/PROPOSED_TO_DATE.
       No inline lat/lon (silently dropped today; documented limitation).
    2. building_permits.csv → GEO_ID + STREET_NAME/STREET_TYPE/STREET_DIRECTION.
       No inline lat/lon either.
    3. permits.csv (legacy simple) → street_name + lat + lon + start_date/end_date.

    All three now emit `normalized_street`, `direction`, and `geo_id` for the
    Phase-8 clustering pass. Schemas 1 and 2 still return None because lat/lon
    are absent — the optimizer's downstream stages need coordinates today
    (geocoding is a separate v1.1 task — see SCHEMAS.md Known limitations).
    """
    # Schema 1: utility_cuts.csv (PROPOSED_FROM_DATE + DISPLAY_DESC + GEO_ID)
    if row.get("DISPLAY_DESC") is not None and "PROPOSED_FROM_DATE" in row:
        start = parse_date(row.get("PROPOSED_FROM_DATE"))
        end = parse_date(row.get("PROPOSED_TO_DATE")) or start
        raw_street = clean_text(row.get("DISPLAY_DESC"))
        norm = normalize_street(raw_street)
        lat = pd.to_numeric(row.get("lat"), errors="coerce") if "lat" in row else float("nan")
        lon = pd.to_numeric(row.get("lon"), errors="coerce") if "lon" in row else float("nan")
        base = {
            "permit_id": f"{source}:{row.get('_id') if row.get('_id') is not None else row.get('PERMIT_NUMBER')}",
            "source": source,
            "role": role,
            "street_name": raw_street or "Unknown location",
            "work_type": clean_text(row.get("INSTALLATION_TYPE_DESC"), "Utility work"),
            "status": clean_text(row.get("PERMIT_STATUS"), "Planned"),
            "start_date": start,
            "end_date": end,
            "normalized_street": norm["normalized"],
            "direction": norm["direction"],
            "geo_id": _coerce_geo_id(row.get("GEO_ID")),
        }
        if start is None or end is None or pd.isna(lat) or pd.isna(lon):
            # Lat/lon absent (the v1.0 reality for utility_cuts). Return None to
            # preserve the existing silent-drop behaviour for downstream stages,
            # which still require coordinates. The Phase-8 fields above would
            # only matter once a geocoder fills in lat/lon.
            return None
        base["lane_days"] = lane_days(start, end)
        base["lat"] = float(lat)
        base["lon"] = float(lon)
        return base

    # Schema 2: building_permits.csv (STREET_NAME + STREET_TYPE + GEO_ID)
    if row.get("STREET_NAME") is not None and "STREET_TYPE" in row:
        street_dir = clean_text(row.get("STREET_DIRECTION"))
        street_name = clean_text(row.get("STREET_NAME"))
        street_type = clean_text(row.get("STREET_TYPE"))
        raw_street = " ".join(p for p in (street_dir, street_name, street_type) if p).strip()
        norm = normalize_street(raw_street)
        start = parse_date(row.get("ISSUED_DATE")) or parse_date(row.get("APPLICATION_DATE"))
        end = parse_date(row.get("COMPLETED_DATE")) or start
        lat = pd.to_numeric(row.get("lat"), errors="coerce") if "lat" in row else float("nan")
        lon = pd.to_numeric(row.get("lon"), errors="coerce") if "lon" in row else float("nan")
        base = {
            "permit_id": f"{source}:{row.get('_id') if row.get('_id') is not None else row.get('PERMIT_NUM')}",
            "source": source,
            "role": role,
            "street_name": raw_street or "Unknown location",
            "work_type": clean_text(row.get("WORK"), "Building work"),
            "status": clean_text(row.get("STATUS"), "Planned"),
            "start_date": start,
            "end_date": end,
            "normalized_street": norm["normalized"],
            "direction": norm["direction"],
            "geo_id": _coerce_geo_id(row.get("GEO_ID")),
        }
        if start is None or end is None or pd.isna(lat) or pd.isna(lon):
            return None
        base["lane_days"] = lane_days(start, end)
        base["lat"] = float(lat)
        base["lon"] = float(lon)
        return base

    # Schema 3: legacy simple permits.csv
    start = parse_date(row.get("start_date"))
    end = parse_date(row.get("end_date")) or start
    lat = pd.to_numeric(row.get("lat"), errors="coerce")
    lon = pd.to_numeric(row.get("lon"), errors="coerce")
    if start is None or end is None or pd.isna(lat) or pd.isna(lon):
        return None
    raw_street = clean_text(row.get("street_name"))
    norm = normalize_street(raw_street)
    return {
        "permit_id": f"{source}:{row.get('permit_id')}",
        "source": source,
        "role": role,
        "street_name": raw_street or "Unknown location",
        "work_type": clean_text(row.get("work_type"), "Utility work"),
        "status": clean_text(row.get("status"), "Planned"),
        "start_date": start,
        "end_date": end,
        "lane_days": lane_days(start, end),
        "lat": float(lat),
        "lon": float(lon),
        "normalized_street": norm["normalized"],
        "direction": norm["direction"],
        "geo_id": _coerce_geo_id(row.get("GEO_ID")),
    }


def load_canonical_permits(include_all_future=False):
    permits = []

    open_toronto = DATA_DIR / "open_toronto_permits.csv"
    if open_toronto.exists():
        df = pd.read_csv(open_toronto)
        for _, row in df.iterrows():
            permit = _permit_from_open_toronto(row, "road_reconstruction", "anchor")
            if permit:
                permits.append(permit)

    for source, filename in ANCHOR_FILES.items():
        path = DATA_DIR / filename
        if not path.exists():
            continue
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            permit = _permit_from_open_toronto(row, source, "anchor")
            if permit:
                permits.append(permit)

    simple = DATA_DIR / "permits.csv"
    if simple.exists():
        df = pd.read_csv(simple)
        for _, row in df.iterrows():
            permit = _permit_from_simple_csv(row, "utility_cut", "candidate")
            if permit:
                permits.append(permit)

    for source, filename in CANDIDATE_FILES.items():
        path = DATA_DIR / filename
        if not path.exists():
            continue
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            permit = _permit_from_simple_csv(row, source, "candidate")
            if permit:
                permits.append(permit)

    if include_all_future:
        return [p for p in permits if p["end_date"] >= TODAY]

    window_end = TODAY + timedelta(days=WINDOW_DAYS)
    scoped = [
        p for p in permits
        if p["end_date"] >= TODAY and p["start_date"] <= window_end
    ]
    return scoped or [p for p in permits if p["end_date"] >= TODAY]


def hero_block_from_permits(permits, padding=0.0045):
    if not permits:
        return {
            "name": "Toronto demo block",
            "bbox": [-79.43, 43.64, -79.36, 43.70],
        }
    top = max(permits, key=lambda p: sum(1 for q in permits if distance_m(p, q) <= 1000))
    return {
        "name": f"Hero block near {top['street_name'].split(' | ')[0]}",
        "center": [top["lat"], top["lon"]],
        "bbox": [
            top["lon"] - padding,
            top["lat"] - padding,
            top["lon"] + padding,
            top["lat"] + padding,
        ],
    }


def filter_to_hero_block(permits, hero_block):
    min_lon, min_lat, max_lon, max_lat = hero_block["bbox"]
    scoped = [
        p for p in permits
        if min_lat <= p["lat"] <= max_lat and min_lon <= p["lon"] <= max_lon
    ]
    return scoped or permits


def _feature_matrix(permits):
    lon_mean = np.mean([p["lon"] for p in permits])
    lat_mean = np.mean([p["lat"] for p in permits])
    day_mean = np.mean([p["start_date"].toordinal() for p in permits])
    rows = []
    for permit in permits:
        x_m = (permit["lon"] - lon_mean) * LON_M_PER_DEG
        y_m = (permit["lat"] - lat_mean) * LAT_M_PER_DEG
        t_m = (permit["start_date"].toordinal() - day_mean) * DBSCAN_TIME_M_PER_DAY
        rows.append([x_m, y_m, t_m])
    return np.array(rows)


def _fallback_dbscan(features, eps, min_samples):
    labels = [-1] * len(features)
    cluster_id = 0

    def neighbours(index):
        delta = features - features[index]
        distances = np.sqrt((delta * delta).sum(axis=1))
        return [int(i) for i in np.where(distances <= eps)[0]]

    for index in range(len(features)):
        if labels[index] != -1:
            continue
        seeds = neighbours(index)
        if len(seeds) < min_samples:
            continue
        labels[index] = cluster_id
        queue = list(seeds)
        while queue:
            current = queue.pop(0)
            if labels[current] == -1:
                labels[current] = cluster_id
            current_neighbours = neighbours(current)
            if len(current_neighbours) >= min_samples:
                for candidate in current_neighbours:
                    if labels[candidate] == -1:
                        queue.append(candidate)
        cluster_id += 1
    return labels


def dbscan_labels(permits):
    if not permits:
        return []
    features = _feature_matrix(permits)
    if SklearnDBSCAN is not None:
        return SklearnDBSCAN(eps=DBSCAN_EPS_METERS, min_samples=DBSCAN_MIN_SAMPLES).fit(features).labels_.tolist()
    return _fallback_dbscan(features, DBSCAN_EPS_METERS, DBSCAN_MIN_SAMPLES)


def match_piggybacks(permits):
    anchors = [p for p in permits if p["role"] == "anchor"]
    candidates = [p for p in permits if p["role"] == "candidate"]
    used = set()
    recommendations = []

    for candidate in candidates:
        best = None
        best_score = float("inf")
        for anchor in anchors:
            dist = distance_m(candidate, anchor)
            gap = date_gap_days(candidate, anchor)
            if dist > ANCHOR_MATCH_METERS or gap > ANCHOR_MATCH_DAYS:
                continue
            score = dist + gap * 8
            if score < best_score:
                best = anchor
                best_score = score
        if not best:
            continue
        used.add(candidate["permit_id"])
        saved = candidate["lane_days"]
        recommendations.append({
            "type": "piggyback",
            "cluster_id": f"piggyback:{len(recommendations)}",
            "anchor_id": best["permit_id"],
            "candidate_id": candidate["permit_id"],
            "member_permit_ids": [best["permit_id"], candidate["permit_id"]],
            "merged_window": {
                "start": serialize_date(best["start_date"]),
                "end": serialize_date(best["end_date"]),
            },
            "distance_m": round(distance_m(candidate, best), 1),
            "date_shift_days": abs((best["start_date"] - candidate["start_date"]).days),
            "savings_lane_days": int(saved),
            "lane_days_saved": int(saved),
            "excavations_avoided": 1,
            "permit_count": 2,
            "road_openings_saved": 1,
            "estimated_savings": int(saved * LANE_DAY_COST),
            "priority": "High" if saved >= 10 else "Medium",
            "locations": [best["street_name"], candidate["street_name"]],
            "projects": [best["work_type"], candidate["work_type"]],
            "statuses": [best["status"], candidate["status"]],
            "action": "Piggyback flexible utility work into an already-planned city opening.",
            "reason": "The candidate is close enough in space and time to share the anchor closure window.",
            "match_type": "piggyback_segment",
        })
    return recommendations, used


def _temporal_subclusters(group, window_days):
    """Greedy 1-D temporal bucketing within a same-street / same-segment group.

    Sort by start_date; start a new bucket whenever the next permit's start_date
    is more than `window_days` after the running bucket's max end_date.
    Returns list[list[permit]] (each inner list is one temporal sub-cluster).
    """
    if not group:
        return []
    sorted_group = sorted(group, key=lambda p: p["start_date"])
    buckets = [[sorted_group[0]]]
    for permit in sorted_group[1:]:
        current_end = max(q["end_date"] for q in buckets[-1])
        if (permit["start_date"] - current_end).days <= window_days:
            buckets[-1].append(permit)
        else:
            buckets.append([permit])
    return buckets


def cluster_leftover_candidates(permits, used_candidate_ids):
    """Phase-8 street-aware grouping (Layers 1 + 2).

    Layer 2 — GEO_ID exact match (gold-standard city centerline segment IDs):
      Candidates with the same geo_id are grouped, then sub-bucketed by
      temporal proximity. Multi-permit buckets become "same_segment" clusters;
      singletons fall through to Layer 1 along with no-geo candidates.

    Layer 1 — Same normalized street + temporal sub-bucketing:
      Remaining candidates are grouped by `normalized_street` (empty key is
      NEVER a group — those permits stay as singletons). Each street group is
      sub-bucketed by `STREET_CLUSTER_WINDOW_DAYS` (default 60d). Multi-permit
      buckets become "same_street" clusters.

    Returns: list of recommendation dicts, each carrying a `match_type` field
    in {"same_segment", "same_street"}. The shape is otherwise identical to
    the previous DBSCAN-based output (clusters.json contract preserved).
    """
    candidates = [
        p for p in permits
        if p["role"] == "candidate" and p["permit_id"] not in used_candidate_ids
    ]
    if not candidates:
        return []

    # --- Layer 2: GEO_ID exact match (preferred when present) ---
    geo_groups: dict[str, list] = defaultdict(list)
    no_geo: list = []
    for permit in candidates:
        gid = permit.get("geo_id")
        if gid:
            geo_groups[gid].append(permit)
        else:
            no_geo.append(permit)

    clusters: list[tuple[str, list]] = []  # (match_type, [permits])
    for gid, group in geo_groups.items():
        if len(group) < 2:
            no_geo.extend(group)
            continue
        for sub in _temporal_subclusters(group, STREET_CLUSTER_WINDOW_DAYS):
            if len(sub) >= 2:
                clusters.append(("same_segment", sub))
            else:
                # Singletons within a GEO_ID fall through to Layer 1.
                no_geo.extend(sub)

    # --- Layer 1: Same normalized street + temporal sub-bucketing ---
    street_groups: dict[str, list] = defaultdict(list)
    for permit in no_geo:
        key = permit.get("normalized_street", "") or ""
        if not key:
            # Empty normalized_street is a soft singleton signal — NEVER group
            # all "unknown" permits together (would create a giant junk cluster).
            continue
        street_groups[key].append(permit)

    for key, group in street_groups.items():
        if len(group) < 2:
            continue
        for sub in _temporal_subclusters(group, STREET_CLUSTER_WINDOW_DAYS):
            if len(sub) >= 2:
                clusters.append(("same_street", sub))

    # --- Convert to recommendation dicts (preserves clusters.json contract) ---
    recommendations = []
    for label, (match_type, group) in enumerate(clusters):
        start = min(p["start_date"] for p in group)
        end = max(p["end_date"] for p in group)
        saved = sum(p["lane_days"] for p in group) - max(p["lane_days"] for p in group)
        recommendations.append({
            "type": "merge",
            "cluster_id": f"merge:{label}",
            "match_type": match_type,
            "member_permit_ids": [p["permit_id"] for p in group],
            "merged_window": {
                "start": serialize_date(start),
                "end": serialize_date(end),
            },
            "savings_lane_days": int(saved),
            "lane_days_saved": int(saved),
            "excavations_avoided": len(group) - 1,
            "permit_count": len(group),
            "road_openings_saved": len(group) - 1,
            "estimated_savings": int(saved * LANE_DAY_COST),
            "priority": "High" if saved >= 20 else "Medium",
            "locations": sorted({p["street_name"] for p in group})[:8],
            "projects": sorted({p["work_type"] for p in group})[:5],
            "statuses": sorted({p["status"] for p in group}),
            "action": (
                "Merge same-segment utility work into one coordinated opening."
                if match_type == "same_segment"
                else "Coordinate same-street permits into one trench-sharing window."
            ),
            "reason": (
                "These permits share the city's GEO_ID (same road segment) and "
                "fall within a single coordination window."
                if match_type == "same_segment"
                else "These permits are on the same physical road within a "
                "single coordination window."
            ),
        })
    return recommendations


def cluster_anchor_program(permits, used_anchor_ids):
    """Phase-8b — cluster anchor (city road-program) permits on the same street.

    The original D-79 framing treated anchors as fixed windows that *candidates*
    piggyback onto. But when the city itself has multiple anchor permits on the
    same street (observed: 6 separate BRIDGMAN AVE road jobs in the demo data),
    those are a coordination opportunity too — they should be one street program
    cluster, not 6 singletons.

    Mirrors `cluster_leftover_candidates`:
      Layer 2 — GEO_ID exact match (rarely fires; anchor CSVs don't carry one).
      Layer 1 — normalized_street + temporal sub-bucketing.

    Excludes anchors already absorbed into a piggyback recommendation so we
    don't double-claim the same window.
    """
    anchors = [
        p for p in permits
        if p["role"] == "anchor" and p["permit_id"] not in used_anchor_ids
    ]
    if not anchors:
        return []

    clusters: list[tuple[str, list]] = []

    # Layer 2 — GEO_ID
    geo_groups: dict[str, list] = defaultdict(list)
    no_geo: list = []
    for permit in anchors:
        gid = permit.get("geo_id")
        if gid:
            geo_groups[gid].append(permit)
        else:
            no_geo.append(permit)

    for gid, group in geo_groups.items():
        if len(group) < 2:
            no_geo.extend(group)
            continue
        for sub in _temporal_subclusters(group, STREET_CLUSTER_WINDOW_DAYS):
            if len(sub) >= 2:
                clusters.append(("same_segment", sub))
            else:
                no_geo.extend(sub)

    # Layer 1 — normalized street
    street_groups: dict[str, list] = defaultdict(list)
    for permit in no_geo:
        key = permit.get("normalized_street", "") or ""
        if not key:
            continue
        street_groups[key].append(permit)

    for key, group in street_groups.items():
        if len(group) < 2:
            continue
        for sub in _temporal_subclusters(group, STREET_CLUSTER_WINDOW_DAYS):
            if len(sub) >= 2:
                clusters.append(("anchor_program", sub))

    # Convert to recommendation dicts. Anchor-program savings are MOBILIZATION-
    # based (not trench-share): the road work itself still happens. We save crew
    # dispatch overhead per merged permit, NOT lane-days.
    recommendations = []
    for label, (match_type, group) in enumerate(clusters):
        start = min(p["start_date"] for p in group)
        end = max(p["end_date"] for p in group)
        mobilizations_saved = len(group) - 1
        dollar_savings = mobilizations_saved * MOBILIZATION_SAVINGS
        recommendations.append({
            "type": "merge",
            "cluster_id": f"program:{label}",
            "match_type": match_type if match_type == "same_segment" else "anchor_program",
            "member_permit_ids": [p["permit_id"] for p in group],
            "merged_window": {
                "start": serialize_date(start),
                "end": serialize_date(end),
            },
            # Lane-days NOT saved — the road work happens regardless.
            "savings_lane_days": 0,
            "lane_days_saved": 0,
            # Excavations IS the right unit: each merged permit is one
            # mobilization (crew + equipment dispatch) we don't re-pay for.
            "excavations_avoided": mobilizations_saved,
            "mobilizations_saved": mobilizations_saved,
            "permit_count": len(group),
            "road_openings_saved": mobilizations_saved,
            "estimated_savings": int(dollar_savings),
            "priority": "High" if mobilizations_saved >= 4 else "Medium",
            "locations": sorted({p["street_name"] for p in group})[:8],
            "projects": sorted({p["work_type"] for p in group})[:5],
            "statuses": sorted({p["status"] for p in group}),
            "action": (
                "Merge city road-program permits on the same street into one "
                "coordinated program. Saves crew mobilization per merged permit."
            ),
            "reason": (
                f"{len(group)} city road-work permits on the same street within "
                f"a single coordination window — combining them saves "
                f"{mobilizations_saved} mobilization{'s' if mobilizations_saved != 1 else ''} "
                f"at ~${MOBILIZATION_SAVINGS:,} each."
            ),
        })
    return recommendations


def build_naive_timeline(permits):
    return [
        {
            **serialize_permit(permit),
            "timeline_id": permit["permit_id"],
            "optimization_status": "naive",
            "cluster_id": None,
            "geometry": permit_geometry(permit),
        }
        for permit in permits
    ]


def build_optimized_timeline(permits, recommendations, conflict_edges=None):
    by_id = {p["permit_id"]: dict(p) for p in permits}
    assignments = {}

    for rec in recommendations:
        if rec["type"] == "piggyback":
            candidate = by_id.get(rec["candidate_id"])
            anchor = by_id.get(rec["anchor_id"])
            if candidate and anchor:
                candidate["start_date"] = anchor["start_date"]
                candidate["end_date"] = anchor["end_date"]
                candidate["lane_days"] = anchor["lane_days"]
                assignments[candidate["permit_id"]] = rec["cluster_id"]
        elif rec["type"] == "merge":
            start = date.fromisoformat(rec["merged_window"]["start"])
            end = date.fromisoformat(rec["merged_window"]["end"])
            for permit_id in rec["member_permit_ids"]:
                if permit_id in by_id:
                    by_id[permit_id]["start_date"] = start
                    by_id[permit_id]["end_date"] = end
                    by_id[permit_id]["lane_days"] = lane_days(start, end)
                    assignments[permit_id] = rec["cluster_id"]

    conflict_lookup = defaultdict(set)
    for edge in conflict_edges or []:
        if edge.get("conflict_score", 0) >= CONFLICT_THRESHOLD:
            conflict_lookup[edge["permit_a"]].add(edge["permit_b"])
            conflict_lookup[edge["permit_b"]].add(edge["permit_a"])

    scheduled = []
    for permit in sorted(by_id.values(), key=lambda p: (p["start_date"], p["permit_id"])):
        duration = lane_days(permit["start_date"], permit["end_date"])
        deferred = False
        while any(
            other["permit_id"] in conflict_lookup[permit["permit_id"]]
            and not (permit["end_date"] < other["start_date"] or permit["start_date"] > other["end_date"])
            for other in scheduled
        ):
            permit["start_date"] += timedelta(days=7)
            permit["end_date"] = permit["start_date"] + timedelta(days=duration - 1)
            deferred = True
        scheduled.append(permit)
        assignments.setdefault(permit["permit_id"], "singleton")
        permit["optimization_status"] = "conflict_deferred" if deferred else (
            "coordinated" if assignments[permit["permit_id"]] != "singleton" else "singleton"
        )

    return [
        {
            **serialize_permit(permit),
            "timeline_id": permit["permit_id"],
            "cluster_id": assignments.get(permit["permit_id"], "singleton"),
            "geometry": permit_geometry(permit),
        }
        for permit in scheduled
    ]


def build_conflict_graph(permits):
    edges = []
    for i, a in enumerate(permits):
        for b in permits[i + 1:]:
            dist = distance_m(a, b)
            if dist > CONFLICT_DISTANCE_METERS:
                continue
            overlap_days = max(
                0,
                (min(a["end_date"], b["end_date"]) - max(a["start_date"], b["start_date"])).days + 1,
            )
            time_score = overlap_days / max(min(a["lane_days"], b["lane_days"]), 1)
            distance_score = max(0, 1 - dist / CONFLICT_DISTANCE_METERS)
            score = round(max(distance_score * 0.7, distance_score * time_score), 3)
            if score < CONFLICT_THRESHOLD:
                continue
            edges.append({
                "permit_a": a["permit_id"],
                "permit_b": b["permit_id"],
                "shared_streets": sorted({a["street_name"].split(" | ")[0], b["street_name"].split(" | ")[0]}),
                "conflict_score": score,
                "method": "spacetime_proxy",
            })
    return edges


def max_concurrent(timeline):
    events = []
    for item in timeline:
        events.append((date.fromisoformat(item["start_date"]), 1))
        events.append((date.fromisoformat(item["end_date"]) + timedelta(days=1), -1))
    active = 0
    max_active = 0
    for _, delta in sorted(events):
        active += delta
        max_active = max(max_active, active)
    return max_active


def permits_geojson(permits):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": permit_geometry(permit),
                "properties": {
                    key: serialize_date(value)
                    for key, value in permit.items()
                    if key not in ("lat", "lon")
                } | {"lat": permit["lat"], "lon": permit["lon"]},
            }
            for permit in permits
        ],
    }


def build_metrics(permits, recommendations, naive, optimized, conflict_graph):
    lane_days_saved = sum(r.get("lane_days_saved", 0) for r in recommendations)
    excavations_avoided = sum(r.get("excavations_avoided", 0) for r in recommendations)
    mobilizations_saved = sum(r.get("mobilizations_saved", 0) for r in recommendations)
    # cost_avoidance now sums each recommendation's own estimated_savings so that
    # trench-share (lane-days × $/lane-day) and anchor-program (mobilizations ×
    # $/mob) contribute on their own honest scales rather than being conflated.
    cost_avoidance = sum(int(r.get("estimated_savings", 0)) for r in recommendations)
    clusters = [r for r in recommendations if r["type"] == "merge"]
    piggybacks = [r for r in recommendations if r["type"] == "piggyback"]
    return {
        "lane_days_saved": int(lane_days_saved),
        "permits_considered": int(len(permits)),
        "cost_avoidance": int(cost_avoidance),
        "per_lane_day_cost": int(LANE_DAY_COST),
        "per_mobilization_savings": int(MOBILIZATION_SAVINGS),
        "mobilizations_saved": int(mobilizations_saved),
        "excavations_avoided": int(excavations_avoided),
        "piggybacks_accepted": int(len(piggybacks)),
        "cluster_merges": int(len(clusters)),
        "conflict_edges": int(len(conflict_graph)),
        "naive_max_concurrent_closures": int(max_concurrent(naive)),
        "optimized_max_concurrent_closures": int(max_concurrent(optimized)),
        "total_projects": int(len(permits)),
        "clustered_projects": int(sum(r["permit_count"] for r in recommendations)),
        "consolidation_opportunities": int(len(recommendations)),
        "largest_cluster": int(max((r["permit_count"] for r in recommendations), default=0)),
        "road_openings_saved": int(excavations_avoided),
        "estimated_savings": int(cost_avoidance),
    }


def build_phase3_artifacts():
    permits = load_canonical_permits()
    hero_block = read_json(artifact_path("hero-block.json")) or hero_block_from_permits(permits)
    permits = filter_to_hero_block(permits, hero_block)

    piggybacks, used_candidates = match_piggybacks(permits)
    used_anchors = {r["anchor_id"] for r in piggybacks}
    merges = cluster_leftover_candidates(permits, used_candidates)
    programs = cluster_anchor_program(permits, used_anchors)
    recommendations = sorted(
        piggybacks + merges + programs,
        key=lambda r: (r.get("lane_days_saved", 0), r.get("permit_count", 0)),
        reverse=True,
    )
    conflict_graph = build_conflict_graph(permits)
    naive = build_naive_timeline(permits)
    optimized = build_optimized_timeline(permits, recommendations, conflict_graph)
    metrics = build_metrics(permits, recommendations, naive, optimized, conflict_graph)

    write_json(artifact_path("hero-block.json"), hero_block)
    write_json(artifact_path("permits.geojson"), permits_geojson(permits))
    write_json(artifact_path("clusters.json"), recommendations)
    write_json(artifact_path("conflict-graph.json"), conflict_graph)
    write_json(artifact_path("naive.json"), naive)
    write_json(artifact_path("optimized.json"), optimized)
    write_json(artifact_path("metrics.json"), metrics)

    return {
        "hero_block": hero_block,
        "permits": permits,
        "recommendations": recommendations,
        "conflict_graph": conflict_graph,
        "naive": naive,
        "optimized": optimized,
        "metrics": metrics,
    }


def load_artifact_or_build(name):
    path = artifact_path(name)
    if not path.exists():
        build_phase3_artifacts()
    return read_json(path)


def what_if_by_street(street, query_date=None):
    normalized = street.lower().strip()
    if not normalized:
        return {"error": "street is required"}

    permits = load_artifact_or_build("optimized.json")
    matches = [p for p in permits if normalized in p["street_name"].lower()]
    if not matches:
        hero = load_artifact_or_build("hero-block.json")
        return {
            "impact": "Out of scope",
            "reason": f"{street} is not inside the {hero['name']} Phase 3 hero block.",
            "recommendation": "Use a street from the current demo area or expand the citywide graph in v2.",
        }

    graph = load_artifact_or_build("conflict-graph.json")
    matched_ids = {p["permit_id"] for p in matches}
    conflicts = [
        e for e in graph
        if e["permit_a"] in matched_ids or e["permit_b"] in matched_ids
    ]
    score = max((e["conflict_score"] for e in conflicts), default=0)
    if score >= 0.45:
        impact = "High"
    elif score >= 0.2:
        impact = "Medium"
    else:
        impact = "Low"
    return {
        "street": street,
        "date": query_date,
        "impact": impact,
        "matching_permits": matches[:5],
        "conflicts": conflicts[:5],
        "reason": "Impact is estimated from the cached hero-block conflict graph.",
        "recommendation": "Coordinate this closure with the listed nearby permits before issuing.",
    }


# Legacy API compatibility -------------------------------------------------

def load_permits(csv_path=None):
    if csv_path:
        df = pd.read_csv(csv_path)
        if {"lat", "lon", "start_date", "end_date"}.issubset(df.columns):
            rows = []
            for _, row in df.iterrows():
                permit = _permit_from_simple_csv(row)
                if permit:
                    rows.append(permit)
            return pd.DataFrame(rows)
    return pd.DataFrame(load_canonical_permits(include_all_future=True))


def cluster_permits(df):
    if df.empty:
        df = load_permits()
    records = df.to_dict(orient="records")
    for item in records:
        if isinstance(item.get("start_date"), str):
            item["start_date"] = date.fromisoformat(item["start_date"])
        if isinstance(item.get("end_date"), str):
            item["end_date"] = date.fromisoformat(item["end_date"])
    labels = dbscan_labels(records)
    out = pd.DataFrame(records)
    out["cluster_id"] = labels
    out["start_year"] = out["start_date"].apply(lambda d: d.year)
    return out


def calculate_cluster_metrics(group):
    permit_count = len(group)
    road_openings_saved = max(permit_count - 1, 0)
    unique_locations = group["street_name"].nunique()
    unique_projects = group["work_type"].nunique()
    lane_days_saved = int(group["lane_days"].sum() - group["lane_days"].max())
    disruption_score = permit_count * 10 + unique_locations * 4 + unique_projects * 3
    return {
        "permit_count": int(permit_count),
        "road_openings_saved": int(road_openings_saved),
        "unique_locations": int(unique_locations),
        "unique_projects": int(unique_projects),
        "disruption_score": int(disruption_score),
        "lane_days_saved": int(max(lane_days_saved, 0)),
        "estimated_savings": int(max(lane_days_saved, 0) * LANE_DAY_COST),
    }


def get_priority(score):
    if score >= 100:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def recommend_consolidations(df=None):
    artifacts = load_artifact_or_build("clusters.json")
    return artifacts


def get_metrics(df=None):
    return load_artifact_or_build("metrics.json")


def what_if_analysis(df=None, cluster_id=None, delay_weeks=2):
    recommendations = load_artifact_or_build("clusters.json")
    cluster = next((r for r in recommendations if str(r["cluster_id"]) == str(cluster_id)), None)
    if not cluster:
        return {"error": "Cluster not found"}
    if delay_weeks <= 2:
        impact = "Low"
    elif delay_weeks <= 6:
        impact = "Medium"
    else:
        impact = "High"
    return {
        "cluster_id": cluster_id,
        "delay_weeks": int(delay_weeks),
        "impact": impact,
        "cluster": cluster,
        "reason": "Delay impact is estimated against the Phase 3 optimized window.",
        "recommendation": "Review anchor windows and conflict edges before approving the delay.",
    }
