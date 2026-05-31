# Phase 3 → Phase 4 Data Contract

**Source of truth:** `backend/optimizer.py` (helpers `load_artifact_or_build`, `build_phase3_artifacts`). All artifacts live under `data/artifacts/` and are served via FastAPI from `backend/main.py`.

All artifacts are produced by a single offline builder run (`python -c "from optimizer import build_phase3_artifacts; build_phase3_artifacts()"`). Lazy-build kicks in on first endpoint hit if files are absent.

---

## hero-block.json — `GET /hero-block`

```json
{
  "name": "Greektown corridor (Danforth, 43.6657 / -79.3642)",
  "id": "segment-43666-79364",
  "bbox": [-79.370383, 43.661222, -79.357943, 43.670202],
  "center": [43.665712, -79.364163],
  "source": ".planning/phases/01-parallel-kickoff/hero-block.json",
  "selected_by": "disruption events 2023-2025 per 100m segment (D-08)"
}
```

`bbox` order is `[min_lon, min_lat, max_lon, max_lat]` (Leaflet `LngLatBoundsLike`-compatible).
`center` order is `[lat, lon]` (Leaflet `LatLngTuple`-compatible).

---

## permits.geojson — *(internal, consumed by other artifacts)*

Standard GeoJSON `FeatureCollection`. Properties on each feature include `permit_id`, `source`, `role` (`anchor` | `candidate`), `street_name`, `work_type`, `status`, `start_date`, `end_date`, `lane_days`. Geometry is a small `Polygon` buffer (≈45 m half-side) around the permit's centroid.

---

## clusters.json — `GET /clusters`

Array of recommendation objects, sorted by `lane_days_saved` descending.

```json
[
  {
    "type": "piggyback" | "merge",
    "cluster_id": "piggyback:0" | "merge:3",
    "member_permit_ids": ["road_resurfacing:123", "utility_cut:9001"],
    "merged_window": { "start": "2026-07-10", "end": "2026-08-04" },
    "savings_lane_days": 14,
    "lane_days_saved": 14,
    "excavations_avoided": 1,
    "permit_count": 2,
    "road_openings_saved": 1,
    "estimated_savings": 210000,
    "priority": "High" | "Medium",
    "locations": ["DANFORTH AVE", "..."],
    "projects": ["Road Resurfacing", "Utility Cut"],
    "statuses": ["Planned"],
    "action": "...",
    "reason": "..."
  }
]
```

Piggyback recommendations also carry `anchor_id`, `candidate_id`, `distance_m`, `date_shift_days`.

`is_singleton` is NOT emitted here — singletons appear only in `optimized.json` with `cluster_id = "singleton"`.

---

## conflict-graph.json — `GET /conflict-graph`

Array of pairwise conflict edges (space-time proxy, NOT a Valhalla `exclude_polygons` precompute — see D-79 commentary in `03-CONTEXT.md`).

```json
[
  {
    "permit_a": "road_resurfacing:123",
    "permit_b": "utility_cut:9001",
    "shared_streets": ["DANFORTH AVE", "PAPE AVE"],
    "conflict_score": 0.42,
    "method": "spacetime_proxy"
  }
]
```

`conflict_score` is `max(distance_score * 0.7, distance_score * time_overlap_score)`, range `[0, 1]`. Edges with score `< CONFLICT_THRESHOLD` (default 0.15) are filtered out at build time.

---

## naive.json — `GET /naive`

Array of permit-events in their as-applied schedule (one event per permit, no coordination).

```json
[
  {
    "permit_id": "road_resurfacing:123",
    "source": "road_resurfacing",
    "role": "anchor",
    "street_name": "DANFORTH AVE",
    "work_type": "Road Resurfacing",
    "status": "Planned",
    "start_date": "2026-07-10",
    "end_date": "2026-08-04",
    "lane_days": 26,
    "lat": 43.6657,
    "lon": -79.3642,
    "timeline_id": "road_resurfacing:123",
    "optimization_status": "naive",
    "cluster_id": null,
    "geometry": { "type": "Polygon", "coordinates": [[ ... ]] }
  }
]
```

---

## optimized.json — `GET /optimized`

Same shape as `naive.json` but with cluster windows applied (piggybacks shifted to anchor dates, merges collapsed) and conflict-aware greedy scheduling (defer overlapping permits in 7-day steps).

`optimization_status` values:
- `"coordinated"` — permit was assigned to a cluster (`cluster_id` ≠ `"singleton"`)
- `"conflict_deferred"` — permit was shifted to avoid an active conflict edge
- `"singleton"` — permit ran solo, no coordination opportunity (D-29 — UI should render in neutral color)

---

## metrics.json — `GET /metrics`

Headline counter per D-27. Two-metric design per D-28 — `permits_considered` is the big-font number, `excavations_avoided` is the honest savings.

```json
{
  "lane_days_saved": 14,
  "permits_considered": 532,
  "cost_avoidance": 210000,
  "per_lane_day_cost": 15000,
  "excavations_avoided": 3,
  "piggybacks_accepted": 0,
  "cluster_merges": 2,
  "conflict_edges": 1228,
  "naive_max_concurrent_closures": 8,
  "optimized_max_concurrent_closures": 5,
  "total_projects": 532,
  "clustered_projects": 5,
  "consolidation_opportunities": 2,
  "largest_cluster": 3,
  "road_openings_saved": 3,
  "estimated_savings": 210000
}
```

`per_lane_day_cost` is a $15,000 placeholder per D-26 — Phase 6 polish replaces it with the Toronto Congestion Management Plan figure.

---

## Endpoint inventory

| Path | Returns | Source |
|------|---------|--------|
| `GET /hero-block` | hero-block.json | artifact |
| `GET /permits` | legacy DataFrame slice | live DBSCAN |
| `GET /clusters` | clusters.json | artifact |
| `GET /conflict-graph` | conflict-graph.json | artifact |
| `GET /naive` | naive.json | artifact |
| `GET /optimized` | optimized.json | artifact |
| `GET /metrics` | metrics.json | artifact (wrapped by `get_metrics()`) |
| `GET /recommendations` | clusters.json | artifact (wrapped by `recommend_consolidations()`) |
| `GET /whatif?cluster_id=N&delay_weeks=N` | legacy delay-bucket impact | wrapped — kept for backward compat |
| `GET /whatif-street?street=NAME&date=YYYY-MM-DD` | street-scoped impact + conflicts | new |
| `GET /explain?cluster_id=N` | Ollama-generated cluster narrative | Phase 4-adjacent |

---

## Known limitations (Phase 6 / Phase 4 to address)

- `utility_cuts.csv` ships without inline geometry (GEO_ID + DISPLAY_DESC only — per Plan 01-01 SUMMARY). The optimizer's `_permit_from_simple_csv` requires `lat`/`lon` columns, so utility_cut permits are silently dropped from the candidate set. Result: `piggybacks_accepted` is currently 0 in the demo data. Geocoding the DISPLAY_DESC strings is Phase 4 / Phase 6 work.
- Conflict graph is a **space-time proxy**, not a Valhalla `exclude_polygons` precompute (intentional — keeps the demo offline-runnable). `backend/valhalla.py` has a live route client ready for `/whatif-street` to use if Valhalla is reachable at `:5000`.
- `per_lane_day_cost` is a $15K placeholder — Phase 6 replaces from Toronto Congestion Management Plan per D-26.

---

## Phase 8 additions (additive, no removals)

### Permit dicts (in-memory + naive.json / optimized.json)

Three new fields on every permit dict produced by `_permit_from_open_toronto` and `_permit_from_simple_csv`:

- `normalized_street` (str) — lowercased canonical street key (e.g. `"danforth avenue"`). Empty string for permits whose street text could not be parsed. Used by `cluster_leftover_candidates` Layer-1 grouping. Empty values are NEVER grouped together — they fall through as singletons.
- `direction` (str) — single-letter compass prefix (`"E"`, `"W"`, `"N"`, `"S"`, `"NE"`/`"NW"`/`"SE"`/`"SW"`, or `""` if absent). Stored separately so "Yonge St E" and "Yonge St W" do not collapse into one cluster.
- `geo_id` (str | None) — Toronto centerline segment ID, stringified from the CSV's `GEO_ID` column with trailing `.0` stripped. `None` for anchor sources (`road_resurfacing`, `road_reconstruction`, `sidewalk_construction`) whose CSVs do not carry a GEO_ID column.

These fields are emitted into `naive.json` and `optimized.json` per-permit objects automatically (the existing builders spread the full permit dict). Adding them does not break any existing consumer.

### clusters.json — `match_type` field

Every recommendation object now carries a `match_type` field:

- `"same_segment"` — Layer-2 GEO_ID exact match (city's own centerline segment ID + temporal sub-bucket).
- `"same_street"` — Layer-1 normalized-street grouping with temporal sub-bucketing.
- `"piggyback_segment"` — anchor↔candidate piggyback (no algorithmic change in Phase 8 — the field is added for consistency so every cluster has a basis tag).

This is an additive field; the existing 17 fields (`type`, `cluster_id`, `member_permit_ids`, …) are unchanged.

### Removed: radius-based DBSCAN for leftover clustering

`cluster_leftover_candidates` no longer calls `dbscan_labels`. The `dbscan_labels` function itself is retained for the legacy `cluster_permits` DataFrame API (used by the old `/permits` endpoint and `recommend_consolidations` fallback). Layer-1+2 grouping is implemented in `_temporal_subclusters` + dict-keyed groupbys.

Tunable: `PERMITFLOW_STREET_WINDOW_DAYS` env var (default `60`) controls the temporal sub-cluster gap within a street or segment group.

### Layer-2 GEO_ID match — current data reality

`piggybacks_accepted` and `same_segment` cluster counts will both stay at zero in the v1.0 demo data because the GEO_ID-carrying CSVs (`utility_cuts.csv`, `building_permits.csv`) ship without inline lat/lon and are still silently dropped by the constructors' coordinate guard. Once a geocoder fills in lat/lon (separate v1.1 work — see "Known limitations" above), `same_segment` clusters become viable without further optimizer changes.

