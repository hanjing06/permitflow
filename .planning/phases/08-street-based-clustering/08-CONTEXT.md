# Phase 8: Street-Based Clustering — Context

**Captured:** 2026-05-31 (during v1.0 hackathon, post-Phase-7)
**Status:** Deferred to v1.1 milestone. Not in v1.0 scope.
**Origin:** User observation that radius-based DBSCAN clusters don't match the physical trench-sharing thesis.

<domain>
## Phase Boundary

Replace the current radius-based DBSCAN leftover-clustering pass in `backend/optimizer.py:cluster_leftover_candidates` with street-aware grouping. Goal: make the optimizer's "merged cluster" recommendations correspond to physical reality (one opened road, shared crew, shared traffic-management plan) instead of geometric proximity.

In scope:
- Replace `cluster_leftover_candidates` with a street-first grouping pass
- Add GEO_ID exact-match grouping where the data supports it
- Add a tertiary intersection-coordination tag for cross-street near-pairs

Out of scope:
- Geocoding utility_cuts DISPLAY_DESC (separate v1.1 work; benefits piggyback matcher more)
- Anchor-LineString spatial join (separate v1.1 work; nice complement)
- Changing the conflict graph (v1.x — Valhalla-validated graph is a different roadmap item)
- Changing the UI (cluster circles render the same regardless of how members were grouped)

</domain>

<decisions>
## Implementation Decisions

### Three-layer approach (incremental, each shippable independently)

**Layer 1 — Same-street clustering (cheapest, ~2 hrs):**
- Normalize `street_name` by:
  - Stripping `" | From: X | To: Y"` suffixes
  - Canonicalizing abbreviations: `AVE` ⇆ `AVENUE`, `ST` ⇆ `STREET`, `RD` ⇆ `ROAD`, `BLVD`, `CRES`, etc.
  - Stripping direction prefixes (`E `, `W `, `N `, `S `) — or preserving them as a separate `direction` field if the city distinguishes "Yonge St E" from "Yonge St W"
  - Lowercasing for comparison
- Group permits by normalized street name
- Within each group, sub-cluster by temporal proximity (same `DBSCAN_TIME_M_PER_DAY` logic but 1-D on dates only)
- Replaces `cluster_leftover_candidates` entirely

**Layer 2 — Same-segment GEO_ID match (~1 hr, depends on data availability):**
- `utility_cuts.csv` ships a `GEO_ID` column per Plan 01-01 SUMMARY
- Confirm road program CSVs (`road_reconstruction`, `road_resurfacing`, `sidewalk_construction`) also carry GEO_ID
- Group permits by exact `GEO_ID` match before layer-1 falls through
- This is the gold-standard match (city's own segment IDs)

**Layer 3 — Intersection coordination (~3-4 hrs):**
- After layers 1+2, look at unmatched permits
- Permits within ~50 m of each other AND on DIFFERENT normalized streets → likely same intersection
- Tag with a NEW `optimization_status` value: `"intersection_coordinated"` (signage / traffic-control benefit, no trench-sharing)
- UI gets a fourth color in the palette (e.g., teal) — distinct from amber (same-trench coordination)

### Suggested data model changes

- Add `normalized_street` field to permit dicts during canonical load
- Add `geo_id` field where available (read from CSV)
- Cluster recommendation dict gains a `match_type` field: `"same_segment"` (GEO_ID), `"same_street"` (normalized name), `"intersection"` (cross-street near-pair)
- Frontend can show the match_type in cluster popups for transparency

### Tooling
- Street-name normalization: `rapidfuzz` for fuzzy matching, OR a hand-curated lookup dict for the top-50 Toronto streets. Don't aim for perfection.
- No new heavy deps; pandas + a small `street_norm.py` module is enough.

</decisions>

<rationale>
## Why this matters

**Current radius-DBSCAN failure modes:**

1. **False positive — parallel streets:** A permit on Danforth Ave and one on Mortimer Ave (~100 m apart) cluster together at `eps=220m`. But you'd have to open two separate trenches, two crews, two sets of cones — there's no piggyback benefit. The optimizer says "merged" but reality says "still two excavations." This inflates `excavations_avoided` dishonestly.

2. **False negative — same street, far apart:** Two utility cuts on Danforth, 350 m apart, don't cluster (over `eps`). But they're literally the same trench — one crew, one mobilization, one traffic plan. That's the textbook trench-sharing case and the current model misses it. This deflates `excavations_avoided`.

Street-based clustering fixes both. The whole D-79 "trench-sharing" framing is *physically* about sharing the same opened road, not "things that happen to be near each other on the map."

**Expected demo-number lift:** roughly 2x–5x more clusters detected once Layers 1+2 ship, with the same input data. Honest improvement, not gaming.

</rationale>

<dependencies>
## Dependencies

- **v1.0 milestone must close first.** Phase 8 belongs in v1.1, not v1.0. Do not start during the hackathon — no commits after hour 35 per D-74.
- Reads the same CSVs Phase 1 lands. No new ingestion needed.
- Touches `backend/optimizer.py` only (specifically `cluster_leftover_candidates` and its callers). Frontend rendering already handles whatever cluster shape the backend produces.
- If Layer 3 ships, frontend `permitColors.js` gains one new status color.

</dependencies>

<deferred>
## Deferred Ideas (related, separate work)

- **Geocoding utility_cuts DISPLAY_DESC** — would let the piggyback matcher (Phase 3) actually find anchor↔candidate matches. Currently returns 0. Big lift on its own. Independent of Phase 8.
- **Anchor LineString spatial join** — instead of comparing candidate centroid to anchor centroid, do `point-in-buffer(anchor.geometry, 50m)`. Combined with Phase 8, would catch trench-sharing for the geometry-bearing subset of candidates.
- **Real Valhalla-validated conflict graph** — replace the current space-time proxy with `exclude_polygons` precompute. Heavy compute (~30 min Valhalla time per Phase 3 D-24) but qualitatively stronger evidence for the demo claim.

</deferred>

---

*Phase: 8-Street-Based Clustering*
*Captured: 2026-05-31 (post-Phase-7, v1.0 frozen)*
