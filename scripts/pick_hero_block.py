#!/usr/bin/env python3
"""
pick_hero_block.py — data-driven hero block selection for PermitFlow Phase 1.

Per Phase 01 plan 01-02 (D-07/D-08/D-09):
- Combine disruption events from Toronto Open Data CKAN feeds landed by Plan 01-01.
- Rank ~100 m equirectangular grid cells by event count in 2023-2025.
- If the top cell has < 5 events, widen the window to 2020-2025 (D-09).
- Take the enclosing 1 km^2 bbox of the winning cell as the hero block.
- Write `hero-block.json` and `permits.geojson` to .planning/phases/01-parallel-kickoff/.

Geometry reality (per 01-01 SUMMARY):
- utility_cuts.csv and building_permits.csv ship with GEO_ID + DISPLAY_DESC only
  (street-address text) and NO inline geometry. They cannot be ranked or rendered
  directly. The D-07 site-disturbance building-permit filter is still recorded in
  selection.building_permit_filter for auditability, and a count of address-name
  matches against streets inside the chosen bbox is reported as a bonus.
- The geometry-bearing program datasets (road_resurfacing, sidewalk_construction,
  open_toronto_permits = road_reconstruction-program) carry GeoJSON LineStrings
  and drive both the bbox ranking and the permits.geojson output.

Re-running with the same CSV snapshot is deterministic (ranking ties broken by
lat_bucket asc, lon_bucket asc).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb


# Toronto sits near 43.7 deg N.
# 1 deg lat ~= 111,320 m; 1 deg lon ~= 80,400 m at this latitude.
# 100 m ~= 0.000898 deg lat, 0.001244 deg lon.
LAT_STEP_100M = 0.000898
LON_STEP_100M = 0.001244

# 1 km^2 ~= 1000 m x 1000 m -> half-extents ~ 500 m
LAT_HALF_KM = 0.00449
LON_HALF_KM = 0.00622

# Crude Toronto bbox sanity filter
TORONTO_LON_MIN = -79.65
TORONTO_LON_MAX = -79.10
TORONTO_LAT_MIN = 43.58
TORONTO_LAT_MAX = 43.86

# Geometry-bearing program datasets, with the source slug emitted in outputs.
# All three share the same CKAN road-program schema (PROJECT/LOCATION/STATUS/
# START_YEAR/geometry).
PROGRAM_DATASETS = [
    {
        "source": "road_resurfacing",
        "prefix": "rr",
        "filename": "road_resurfacing.csv",
    },
    {
        "source": "sidewalk_construction",
        "prefix": "sw",
        "filename": "sidewalk_construction.csv",
    },
    {
        "source": "road_reconstruction",
        "prefix": "rc",
        "filename": "open_toronto_permits.csv",  # CKAN: road-reconstruction-program
    },
]

# D-07 site-disturbance filter for building_permits.csv. Recorded into the
# output JSON for auditability; applied to the bonus address-overlap count
# inside the chosen bbox (not to ranking — these rows have no geometry).
BUILDING_PERMIT_FILTER_SQL = (
    "PERMIT_TYPE IN ("
    "'New Building','Demolition Folder (DM)','Building Additions/Alterations',"
    "'New Houses','Non-Residential Building Permit','Designated Structures',"
    "'Drain and Site Service'"
    ")"
)


def open_duckdb() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    # spatial ships preinstalled in newer DuckDBs; install is idempotent.
    try:
        con.execute("INSTALL spatial;")
    except Exception:
        pass
    con.execute("LOAD spatial;")
    return con


def load_program_dataset(con: duckdb.DuckDBPyConnection, data_dir: Path, dataset: dict) -> int:
    """Load one road-program CSV into a per-source staging table.

    Returns the number of rows loaded (rows with non-null geometry only).
    """
    path = data_dir / dataset["filename"]
    if not path.exists():
        print(f"  - {dataset['source']}: SKIP (missing {path})")
        return 0

    table = f"_raw_{dataset['source']}"
    con.execute(f"DROP TABLE IF EXISTS {table}")
    con.execute(
        f"""
        CREATE TABLE {table} AS
        SELECT
          '{dataset['source']}'                              AS source,
          CAST(_id AS VARCHAR)                               AS row_id,
          CAST(LOCATION AS VARCHAR)                          AS street,
          CAST(PROJECT AS VARCHAR)                           AS work_type,
          CAST(STATUS AS VARCHAR)                            AS status,
          TRY_CAST(START_YEAR AS INTEGER)                    AS start_year,
          CAST(geometry AS VARCHAR)                          AS geometry_json
        FROM read_csv_auto('{path.as_posix()}', SAMPLE_SIZE=-1, ALL_VARCHAR=true)
        WHERE geometry IS NOT NULL AND geometry <> '';
        """
    )
    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  - {dataset['source']}: loaded {n} rows from {path}")
    return n


def build_disruption_events(con: duckdb.DuckDBPyConnection, data_dir: Path) -> int:
    """UNION ALL the per-source tables into a single `disruption_events` table
    with a parsed GEOMETRY column + representative point + lat/lon scalars.

    Returns the total row count after geometry parsing.
    """
    loaded = []
    for ds in PROGRAM_DATASETS:
        n = load_program_dataset(con, data_dir, ds)
        if n > 0:
            loaded.append(ds["source"])

    if not loaded:
        raise SystemExit("No program datasets could be loaded; cannot rank.")

    union_sql = "\nUNION ALL\n".join(
        f"SELECT * FROM _raw_{name}" for name in loaded
    )
    con.execute("DROP TABLE IF EXISTS disruption_events")
    con.execute(f"CREATE TABLE disruption_events AS {union_sql}")

    # Parse GeoJSON -> GEOMETRY; drop unparseable rows.
    con.execute("ALTER TABLE disruption_events ADD COLUMN geom GEOMETRY")
    con.execute(
        "UPDATE disruption_events SET geom = ST_GeomFromGeoJSON(geometry_json)"
    )
    before = con.execute("SELECT COUNT(*) FROM disruption_events").fetchone()[0]
    con.execute("DELETE FROM disruption_events WHERE geom IS NULL")
    after = con.execute("SELECT COUNT(*) FROM disruption_events").fetchone()[0]
    if before != after:
        print(f"  - dropped {before - after} rows with unparseable geometry")

    # Representative point + scalar lat/lon for cheap bucketing.
    con.execute("ALTER TABLE disruption_events ADD COLUMN rep_point GEOMETRY")
    con.execute(
        "UPDATE disruption_events SET rep_point = ST_Centroid(geom)"
    )
    con.execute("ALTER TABLE disruption_events ADD COLUMN lon DOUBLE")
    con.execute("ALTER TABLE disruption_events ADD COLUMN lat DOUBLE")
    con.execute(
        "UPDATE disruption_events SET lon = ST_X(rep_point), lat = ST_Y(rep_point)"
    )
    return after


def rank_segments(
    con: duckdb.DuckDBPyConnection,
    year_lo: int,
    year_hi: int,
    limit: int = 25,
):
    """Return top `limit` (lat_bucket, lon_bucket, event_count, center_lat,
    center_lon) tuples for the given year window. Deterministic ordering."""
    sql = f"""
        SELECT
          FLOOR(lat / {LAT_STEP_100M}) AS lat_bucket,
          FLOOR(lon / {LON_STEP_100M}) AS lon_bucket,
          COUNT(*)                     AS event_count,
          AVG(lat)                     AS center_lat,
          AVG(lon)                     AS center_lon
        FROM disruption_events
        WHERE start_year BETWEEN {year_lo} AND {year_hi}
          AND lat BETWEEN {TORONTO_LAT_MIN} AND {TORONTO_LAT_MAX}
          AND lon BETWEEN {TORONTO_LON_MIN} AND {TORONTO_LON_MAX}
        GROUP BY lat_bucket, lon_bucket
        ORDER BY event_count DESC, lat_bucket ASC, lon_bucket ASC
        LIMIT {limit}
    """
    return con.execute(sql).fetchall()


def per_source_breakdown(con, west, south, east, north, year_lo, year_hi):
    sql = f"""
        SELECT source, COUNT(*) AS n
        FROM disruption_events
        WHERE start_year BETWEEN {year_lo} AND {year_hi}
          AND ST_Intersects(
            geom,
            ST_MakeEnvelope({west}, {south}, {east}, {north})
          )
        GROUP BY source
        ORDER BY n DESC
    """
    return dict(con.execute(sql).fetchall())


def bbox_features(con, west, south, east, north):
    """Return all disruption_events whose geometry intersects the bbox,
    regardless of year (Leaflet needs to render the full slice)."""
    sql = f"""
        SELECT source, row_id, street, work_type, status, start_year,
               ST_AsGeoJSON(geom) AS geom_json
        FROM disruption_events
        WHERE ST_Intersects(
          geom,
          ST_MakeEnvelope({west}, {south}, {east}, {north})
        )
        ORDER BY source, row_id
    """
    return con.execute(sql).fetchall()


def bonus_address_overlap_count(
    data_dir: Path,
    west: float,
    south: float,
    east: float,
    north: float,
    streets_in_bbox: set[str],
) -> dict:
    """Bonus disruption density signal: count utility_cuts + filtered
    building_permits whose street-address text mentions a street name that
    appears in the bbox's geometry-bearing features. This is a name-overlap
    heuristic, not a true geocode — flagged as such in the output JSON."""
    out = {"utility_cuts": 0, "building_permits_filtered": 0}
    if not streets_in_bbox:
        return out

    # Normalize the bbox street set: split each LOCATION string into tokens
    # like 'HARBORD', 'SPADINA' so we can do a cheap UPPER substring match
    # against DISPLAY_DESC / STREET_NAME.
    name_tokens: set[str] = set()
    for s in streets_in_bbox:
        if not s:
            continue
        # split on the CKAN <br>, From:, To:, commas, ampersands, etc.
        cleaned = (
            s.upper()
            .replace("&LT;BR&GT;", " ")
            .replace("<BR>", " ")
            .replace(":", " ")
            .replace(",", " ")
            .replace("&", " ")
            .replace("[", " ")
            .replace("]", " ")
        )
        for tok in cleaned.split():
            if len(tok) >= 4 and tok.isalpha():
                name_tokens.add(tok)
    if not name_tokens:
        return out

    # Build one regex pattern in DuckDB for cheap matching.
    pattern = "|".join(sorted(name_tokens))
    con = duckdb.connect(":memory:")

    uc_path = data_dir / "utility_cuts.csv"
    if uc_path.exists():
        try:
            n = con.execute(
                f"""
                SELECT COUNT(*) FROM read_csv_auto(
                  '{uc_path.as_posix()}', SAMPLE_SIZE=-1, ALL_VARCHAR=true
                )
                WHERE regexp_matches(UPPER(COALESCE(DISPLAY_DESC, '')), '{pattern}')
                """
            ).fetchone()[0]
            out["utility_cuts"] = int(n)
        except Exception as e:
            print(f"  - bonus utility_cuts count failed: {e}")

    bp_path = data_dir / "building_permits.csv"
    if bp_path.exists():
        try:
            n = con.execute(
                f"""
                SELECT COUNT(*) FROM read_csv_auto(
                  '{bp_path.as_posix()}', SAMPLE_SIZE=-1, ALL_VARCHAR=true
                )
                WHERE {BUILDING_PERMIT_FILTER_SQL}
                  AND regexp_matches(UPPER(COALESCE(STREET_NAME, '')), '{pattern}')
                """
            ).fetchone()[0]
            out["building_permits_filtered"] = int(n)
        except Exception as e:
            print(f"  - bonus building_permits count failed: {e}")

    con.close()
    return out


def make_feature(row, source_prefix_map: dict) -> dict:
    source, row_id, street, work_type, status, start_year, geom_json = row
    prefix = source_prefix_map.get(source, source[:2])
    feat_id = f"{prefix}-{row_id}"
    desc = (
        f"{(work_type or 'Permit').strip()} on "
        f"{(street or 'unknown street').strip()} "
        f"({int(start_year) if start_year is not None else '—'})"
    )
    return {
        "type": "Feature",
        "id": feat_id,
        "geometry": json.loads(geom_json) if geom_json else None,
        "properties": {
            "permit_id": str(row_id),
            "source": source,
            "street": street,
            "work_type": work_type,
            "status": status,
            "start_year": int(start_year) if start_year is not None else None,
            "description": desc,
        },
    }


def pick_hero_block(
    data_dir: Path,
    out_dir: Path,
    dry_run: bool,
) -> int:
    print("Loading DuckDB + spatial extension...")
    con = open_duckdb()

    print("Loading geometry-bearing program datasets:")
    total_rows = build_disruption_events(con, data_dir)
    print(f"  total disruption_events rows (with parsed geometry): {total_rows}")

    # D-08 first pass: 2023-2025
    year_lo, year_hi = 2023, 2025
    top = rank_segments(con, year_lo, year_hi, limit=5)
    method_window = [year_lo, year_hi]
    warning = None

    if not top or top[0][2] < 5:
        # D-09 widening
        print(
            "  top segment has <5 events in 2023-2025 — widening to 2020-2025 (D-09)"
        )
        year_lo, year_hi = 2020, 2025
        top = rank_segments(con, year_lo, year_hi, limit=5)
        method_window = [year_lo, year_hi]
        if not top:
            raise SystemExit(
                "No segments found even with the widened 2020-2025 window."
            )
        if top[0][2] < 3:
            warning = (
                "sparse data — top segment has <3 events even with widened window"
            )

    print(f"\nTop 5 candidate segments (window {year_lo}-{year_hi}):")
    for i, row in enumerate(top, 1):
        lat_b, lon_b, n, c_lat, c_lon = row
        print(
            f"  {i}. bucket=({int(lat_b)},{int(lon_b)}) "
            f"events={int(n)} center=({c_lat:.5f}, {c_lon:.5f})"
        )

    winning = top[0]
    lat_b, lon_b, event_count, c_lat, c_lon = winning
    winning_segment_id = (
        f"segment-{int(lat_b):07d}-{int(lon_b):07d}"
    )

    west = c_lon - LON_HALF_KM
    east = c_lon + LON_HALF_KM
    south = c_lat - LAT_HALF_KM
    north = c_lat + LAT_HALF_KM

    breakdown = per_source_breakdown(con, west, south, east, north, year_lo, year_hi)
    features_raw = bbox_features(con, west, south, east, north)
    source_prefix_map = {d["source"]: d["prefix"] for d in PROGRAM_DATASETS}
    features = [make_feature(r, source_prefix_map) for r in features_raw]

    # Bonus: count address-overlap utility_cuts / filtered building_permits.
    streets_in_bbox = {f["properties"]["street"] for f in features}
    bonus = bonus_address_overlap_count(
        data_dir, west, south, east, north, streets_in_bbox
    )

    slug_lat = int(round(abs(c_lat) * 1000))
    slug_lon = int(round(abs(c_lon) * 1000))
    hero_id = f"segment-{slug_lat:05d}-{slug_lon:05d}"
    name = f"Hero block — {round(c_lat, 4)}, {round(c_lon, 4)}"

    hero_block = {
        "bbox": {
            "west": round(west, 6),
            "south": round(south, 6),
            "east": round(east, 6),
            "north": round(north, 6),
        },
        "center": {"lat": round(c_lat, 6), "lon": round(c_lon, 6)},
        "id": hero_id,
        "name": name,
        "neighbourhood": "unknown",
        "selected_by": "disruption events 2023-2025 per 100m segment (D-08)",
        "selection": {
            "window_years": method_window,
            "winning_segment_id": winning_segment_id,
            "winning_event_count": int(event_count),
            "datasets_counted": [d["source"] for d in PROGRAM_DATASETS],
            "per_source_in_bbox_window": breakdown,
            "all_year_feature_count_in_bbox": len(features),
            "building_permit_filter": BUILDING_PERMIT_FILTER_SQL,
            "bonus_address_overlap_in_bbox": bonus,
            "method_notes": (
                "Segments are equirectangular ~100m grid cells (lat_step="
                f"{LAT_STEP_100M}, lon_step={LON_STEP_100M}), not real road "
                "segments. Ranking uses only the three geometry-bearing program "
                "datasets (road_resurfacing, sidewalk_construction, "
                "road_reconstruction) because utility_cuts.csv and "
                "building_permits.csv ship without inline geometry (GEO_ID + "
                "DISPLAY_DESC only, per 01-01 SUMMARY). The site-disturbance "
                "building_permit_filter is recorded for auditability and is "
                "applied to the bonus_address_overlap_in_bbox count via "
                "street-name token matching against features inside the bbox "
                "(heuristic, not a true geocode)."
            ),
        },
    }
    if warning:
        hero_block["selection"]["warning"] = warning

    permits_geojson = {"type": "FeatureCollection", "features": features}

    print("")
    print(f"Hero block: {hero_id}")
    print(f"  window: {year_lo}-{year_hi}")
    breakdown_str = ", ".join(f"{k}: {v}" for k, v in breakdown.items()) or "(none in window)"
    print(f"  events: {int(event_count)} ({breakdown_str})")
    print(
        f"  bbox:   W {west:.4f}  S {south:.4f}  E {east:.4f}  N {north:.4f}"
    )
    print(f"  center: {c_lat:.4f}, {c_lon:.4f}")
    print(
        f"  bonus address-overlap: utility_cuts={bonus['utility_cuts']} "
        f"building_permits_filtered={bonus['building_permits_filtered']}"
    )

    if dry_run:
        print("\n[--dry-run] not writing output files.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    hero_path = out_dir / "hero-block.json"
    permits_path = out_dir / "permits.geojson"

    with hero_path.open("w") as f:
        json.dump(hero_block, f, indent=2, sort_keys=True)
        f.write("\n")
    with permits_path.open("w") as f:
        json.dump(permits_geojson, f, indent=2)
        f.write("\n")

    print(f"\nWrote:")
    print(f"  {hero_path}")
    print(f"  {permits_path} ({len(features)} features)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        default="data",
        type=Path,
        help="Directory containing the CKAN CSVs (default: data/)",
    )
    parser.add_argument(
        "--out-dir",
        default=".planning/phases/01-parallel-kickoff",
        type=Path,
        help="Directory to write hero-block.json + permits.geojson",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the top 5 candidate segments and would-be summary, write nothing.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    data_dir = args.data_dir if args.data_dir.is_absolute() else (repo_root / args.data_dir)
    out_dir = args.out_dir if args.out_dir.is_absolute() else (repo_root / args.out_dir)

    if not data_dir.exists():
        print(f"ERROR: data dir not found: {data_dir}", file=sys.stderr)
        return 2

    return pick_hero_block(data_dir, out_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
