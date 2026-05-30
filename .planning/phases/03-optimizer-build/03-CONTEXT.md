# Phase 3: Optimizer Build - Context

**Gathered:** 2026-05-30
**Status:** Partial implementation; biggest remaining gap per HEALTHCHECK

> ⚠ **Reality-check (2026-05-31):** the optimizer thesis pivoted during execution.
> - **D-79 — trench-sharing (anchor + piggyback).** Utility-cut-permits are *candidates*. Road-reconstruction / resurfacing / sidewalk programs are *anchor windows*. Two-pass DBSCAN matches candidates to anchors. See body §"D-79".
> - **Routing engine is Valhalla, not OSRM** (D-75). `/whatif` should call Valhalla `POST /route` with `exclude_polygons` for closure simulation.
> - **Current code (`backend/optimizer.py`):** single-pass DBSCAN only — no trench-sharing, no Valhalla call. `/whatif` is the hardcoded delay-week stub. This is the work remaining in Phase 3.

<domain>
## Phase Boundary

Build the geospatial optimizer: DBSCAN space-time clustering of planned permits, Valhalla-driven conflict graph for the hero block, greedy interval scheduling, and the `/whatif` API. Output the two timelines (naive vs optimized) and headline metrics that drive the demo's savings counter.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**5 success criteria are locked.** See `03-SPEC.md` for algorithm definitions, output schemas, subsystems A/B/C, and risk table.

**In scope (from SPEC.md):** DBSCAN clustering · Valhalla conflict graph · interval scheduler · `/whatif` endpoint
**Out of scope:** UI integration (Phase 4) · chat reasoning (Phase 4) · evaluation (Phase 5)

</spec_lock>

<decisions>
## Implementation Decisions

### Optimizer Time Scope — **PIVOT FROM PROJECT.md**
- **D-20:** Optimizer runs on the **future window only** (next 3 months of planned permits / road restrictions). Not retrospective replay of 2023–2025.
- **D-21:** **Demo arc changes.** PROJECT.md's "watch one block over 18 months" historical time-lapse is replaced with: *"Here are 80 permits planned for the next quarter on this neighbourhood. Watch what we save."* PROJECT.md must be updated in Phase 6 polish to reflect this — flagged.
- **D-22:** Data source for "planned future permits" = **Road Restrictions v3** dataset (which contains future planned closures) + **Utility Cut Permits** with `start_date` in the future. Cross-reference against Building Permits for site disruption flag.
- **D-23:** "Naive" timeline = future permits as currently applied/scheduled (one event per permit, no coordination). "Optimized" timeline = post-scheduler (merged + conflict-deferred). Same scrubber UX, just operating on Q3 2026 not 2023.

### Conflict Graph Scope
- **D-24:** **Hero-block only.** ~50 candidate permits inside the locked 1 km² neighbourhood. Precompute the full conflict adjacency once at Phase 3 end (~30 min Valhalla time on GX10). Cache to `conflict-graph.json`.
- **D-25:** Chat panel `/whatif` queries are **constrained to streets inside the hero block** — surface a graceful "out of scope for this demo, but production system handles any street" message for off-hero asks. Pitch slide notes citywide is roadmap.

### Cost-Avoidance Number
- **D-26:** **Toronto Congestion Management Plan** is the source. Phase 6 (Polish) must find the published per-lane-day disruption cost figure. If unavailable on demo day, fall back to a generic industry figure with secondary citation — but TCMP is the priority.
- **D-27:** Counter displays **lane-days saved · permits considered · $ cost avoidance** in that order. The dollar number is computed at runtime from `lane_days_saved × per_lane_day_cost`.

### Trench-Sharing Reframe — Anchor Windows + Piggyback Candidates (mid-execution amendment, 2026-05-30)
- **D-79:** **Optimizer pivots from pure utility-cut clustering to anchor-and-piggyback.**
  - **Reframe:** the city has *already-planned* road openings (reconstruction, resurfacing, sidewalk work). When the road is open anyway, utility cuts nearby in space+time should piggyback into that window for zero extra disruption. This is **trench sharing** / joint utility excavation — a real municipal coordination tactic (NYC DOT has a formal program).
  - **Two-tier optimizer:**
    1. **Anchor windows** (city's planned openings, fixed dates): Road Reconstruction Program · Road Resurfacing Program · Sidewalk Construction Program.
    2. **Piggyback candidates** (flexible-date utility work): Utility Cut Permits · Building Permits (site-disruption subset).
    3. For each candidate, find nearest anchor in (space, time). If within tolerance → recommend shift to coincide. If no anchor reachable → fall back to candidate↔candidate clustering (original DBSCAN logic).
  - **Datasets (CKAN):**
    - Anchors: `road-reconstruction-program`, `road-resurfacing-program`, `sidewalk-construction-program`
    - Candidates: `utility-cut-permits`, `building-permits-active` (filtered)
    - Context overlays: `watermain-breaks` (shows historical coordination failures), `road-restrictions` (current active closures)
  - **Headline metric shift:** `excavations_avoided` is now *piggybacks accepted* + *cluster merges* combined. The pitch line becomes: *"Toronto plans to open N streets next quarter. M utility permits could piggyback for zero extra disruption."* Stronger than pure utility clustering because the city is already paying the disruption cost.
  - **Permitflow repo impact:** `optimizer.py:cluster_permits` becomes two-pass (anchor-match first, then cluster the leftovers). `recommend_consolidations` distinguishes "piggyback" vs "merge" recommendations.

### Singleton Cluster Handling
- **D-28:** Singletons (clusters of size 1) count toward **"permits considered"** in the counter but **NOT** toward "excavations avoided" or "lane-days saved." The counter has two metrics:
  - `permits_considered` — total count of permits the optimizer ran over (includes singletons). Headline number, biggest font.
  - `excavations_avoided` — count of merges that collapsed N permits into 1. Honest savings number.
- **D-29:** Singletons rendered visually as **neutral-color polygons** in the optimized view — distinct from merged (amber) and conflict-deferred (red→shifted-amber). User sees "we considered this one but couldn't improve it" rather than fake savings.

### Claude's Discretion
- DBSCAN `eps` and `min_samples` starting values (tactical tuning at execution); screenline intersection selection method (manual list curated during Phase 3 by OR is fine); volume-data gap fallback (use median Toronto arterial volume as backfill); FastAPI project layout.

</decisions>

<canonical_refs>
## Canonical References

### Phase 3
- `.planning/phases/03-optimizer-build/03-SPEC.md` — **Locked requirements.** Read first.

### Project-level
- `.planning/PROJECT.md` — **needs update in Phase 6** to reflect D-21 (future-only demo arc)
- `.planning/phases/01-parallel-kickoff/01-CONTEXT.md` — D-07/D-08 hero block selection (the geography we operate on here)

### Data sources (Toronto Open Data)
- Road Restrictions v3 — future-planned closures, primary input for D-22
- Utility Cut Permits — secondary input (future-dated only)
- Building Permits Active — site disruption signal
- Traffic Volumes — Midblock — conflict-graph edge weights

### External docs
- Valhalla API — `valhalla.github.io/valhalla/api/turn-by-turn/api-reference/` (route, exclude_polygons, exclude_locations)
- Valhalla on Docker (gisops) — `github.com/gis-ops/docker-valhalla`
- scikit-learn DBSCAN — `scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html`
- Toronto Congestion Management Plan — search city website in Phase 6 for the per-lane-day disruption figure

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 produces `permits.geojson` (hero block scope) and the running Valhalla `:5000` endpoint. Phase 3 reads these and writes new artifacts.

### Established Patterns
- DuckDB is the data layer. Geo work goes through DuckDB's spatial extension, not a separate PostGIS.
- FastAPI hosts `/whatif`; the same backend will serve Phase 4's `/chat`. Single Python process keeps deployment simple on GX10.

### Integration Points
- Phase 4 reads `clusters.json`, `conflict-graph.json`, `naive.json`, `optimized.json`, `metrics.json` from disk. Tight contract between Phase 3 and 4 — JSON schemas should be committed at the end of Phase 3.

</code_context>

<specifics>
## Specific Ideas

- User pivoted to **future-only**. This means the demo's "wow" must come from *prospective* savings on planned work, not retrospective shame on past disruptions. The pitch shifts from "Toronto has been wasteful" to "Toronto can save this much next quarter." Frame matters — Phase 6 pitch script needs to reflect this.
- User accepted **inflated counter for singletons** — but D-28's two-metric structure preserves honesty. Pitch should lead with `permits_considered` for headline but cite `excavations_avoided` immediately after.

</specifics>

<deferred>
## Deferred Ideas

- **Citywide conflict graph** — too expensive for hackathon. Show as roadmap item ("v2 expands to all 25 wards").
- **Predictive optimizer over historical data** — i.e., "if we had run PermitFlow in 2023, what would we have saved?" Compelling but adds scope. Defer to post-hackathon.
- **Demand-responsive scheduling** (delay permits to off-peak times of year) — adds another optimization dimension. Defer.
- **Update PROJECT.md demo arc** — must happen during Phase 6 polish (or earlier if there's slack). Critical so the deck matches what the system actually shows.

</deferred>

---

*Phase: 3-Optimizer Build*
*Context gathered: 2026-05-30*
