# Phase 3 — Optimizer Build

**Window:** Hour 6–14
**Owners:** Data + OR
**Runs while:** Phase 2 fine-tune cooks in the background

## Goal

Produce the two timelines that drive the demo: `naive.json` (permits as historically issued) and `optimized.json` (permits after clustering + conflict-aware scheduling). Plus the conflict graph that powers the chat panel's "what if I close X" answers.

This is the geospatial spine. Without it, the demo is just a chatbot.

## Subsystem A — Clustering (Data)

- [ ] Feature engineer per permit: `(lon, lat, start_doy, end_doy)` where doy = day-of-year normalized across the historical window
- [ ] Apply DBSCAN with `eps` tuned so that a single typical city block + a 4-week date overlap forms one cluster
- [ ] For each cluster of size ≥ 2:
  - Compute merge savings = `sum(lane_days) − max(lane_days)` (one coordinated closure replaces N independent ones)
  - Generate a single "merged permit" record with a window covering all members
- [ ] Write `clusters.json`: `[{cluster_id, member_permit_ids, merged_window, savings_lane_days}, ...]`
- [ ] Sanity check on hero block: at least 1 cluster of size ≥ 3 must exist or the demo doesn't land — if not, widen `eps` or expand window

## Subsystem B — Conflict graph (OR)

- [ ] Build a "screenline" set: ~20 key intersections in the hero neighbourhood that capture most through-traffic
- [ ] For each candidate permit (or merged cluster), simulate by closing its road segment(s) via Valhalla `exclude_polygons`
  - For each origin–destination pair across the hero block, compute baseline route and post-closure route
  - Weight each O-D by traffic volume from the Midblock Counts dataset
  - Sum incremental volume on each non-closed edge → that's the "redirected load" attributable to closing this permit
- [ ] Build adjacency: edge `(A, B)` exists if closing A pushes ≥ X% of A's redirected volume onto streets that B also affects (X tuned empirically, start at 15%)
- [ ] Write `conflict-graph.json`: `[{permit_a, permit_b, shared_streets: [...], conflict_score: 0–1}, ...]`

## Subsystem C — Schedule synthesis

- [ ] Greedy interval scheduling over the historical window:
  - At each time step, eligible-to-issue set = permits whose window starts here AND have no conflict-edge to a currently-active permit (conflict_score > threshold)
  - Conflicting permits get deferred to the earliest non-conflicting slot
- [ ] Produce `optimized.json`: same permits as historical, with adjusted start/end dates and cluster assignments
- [ ] Produce metrics: total redundant excavations avoided, total lane-days saved, naive vs optimized concurrent-closure count

## Exit criteria

By end of hour 14:

1. `clusters.json` exists with at least 5 multi-permit clusters in the hero neighbourhood across the historical window
2. `conflict-graph.json` exists with non-zero edges
3. `naive.json` and `optimized.json` exist and differ visibly when overlaid
4. Headline metrics are computed: e.g. "11 redundant excavations avoided · 38 lane-days saved"

## Risks

| Risk | Mitigation |
|---|---|
| DBSCAN finds no meaningful clusters | Switch to HDBSCAN, or relax the time component, or change hero block |
| Valhalla all-pairs takes too long | Cache per-edge betweenness once, use as a proxy instead of full O-D simulation |
| Conflict-graph noisy / unconvincing | Hand-tune the X% threshold against 3 known examples (e.g. Bathurst/Spadina parallel arterials) |
| Headline numbers underwhelming | Extend historical window from 2 years to 5; pick a different hero block |

## Deliverables to Phase 4

- `clusters.json`
- `conflict-graph.json`
- `naive.json` and `optimized.json` timelines
- `metrics.json` with the headline numbers
- A FastAPI endpoint `/whatif?street=X&date=Y` that runs the simulator on demand for the chat panel
