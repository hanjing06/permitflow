---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in-progress
stopped_at: Plan 08-01 complete — radius-DBSCAN leftover clustering replaced with GEO_ID + normalized-street + 60-day temporal sub-buckets; 23/23 tests green; all 7 Phase-3 artifacts regenerated; SCHEMAS.md gained Phase 8 additive section; HeroMap popup got one match_type subtitle. Frontend build green. Numbers unchanged (geocoding gap is the blocker for Layer-2 lift). human_needed_verification: true — see 08-01-SUMMARY.md.
last_updated: "2026-05-31T05:40:00.000Z"
last_activity: 2026-05-31
progress:
  total_phases: 8
  completed_phases: 2
  total_plans: 11
  completed_plans: 6
  percent: 55
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-30) · .planning/HEALTHCHECK.md (mid-execution gap snapshot)

**Core value:** Cut redundant Toronto road excavations via trench-sharing (anchor-and-piggyback) and Valhalla conflict-aware scheduling, narrated by Ollama-served Nemotron-3 Super 123B running locally on a GX10.

**Current focus:** Phase 06 — demo-polish (06-01 code-only polish shipped; awaiting browser eyeball pass + pitch-lead deliverables)

## Current Position

Phase: 08 (street-based clustering) — Plan 01 COMPLETE; awaiting browser eyeball
Plan: 1 of 1 ✅ (08-01 GEO_ID + same-street + temporal sub-buckets; match_type field; 23/23 tests; artifacts regenerated; SCHEMAS.md updated; popup subtitle)
Phases done: 1, 2 (closed), 3, 4 (code-complete), 5 (reduced), 6 (code-complete), 8 (code-complete)
Phases remaining: 6 (pitch-lead deliverables only), 7
Last activity: 2026-05-31

Progress: [██████░░░░] 55%

See `.planning/HEALTHCHECK.md` for the per-phase delta — Phase 3 rows flip ❌ → ✅; Phase 4 D-32 / D-33 / D-34 / D-55 / D-41 wired (visual UAT pending); Phase 8 Layers 1+2 shipped.

## Accumulated Context

### Decisions (latest)

- **D-87 (08-01)** — Tests written as plain assertion-functions runnable via `python -m backend.tests.test_X`. pytest is not in the nix flake's pythonEnv; adding it mid-late hackathon judged too risky. Same files become pytest-discoverable the day pytest lands without modification.
- **D-86 (08-01)** — `match_type` added as a single additive field on EVERY recommendation in clusters.json (merge AND piggyback). Piggybacks tagged `piggyback_segment` for consistency so downstream consumers can rely on the field always being present.
- **D-85 (08-01)** — Empty normalized_street is a soft singleton signal — `cluster_leftover_candidates` NEVER groups unparseable permits under a junk 'unknown' bucket. Documented in SCHEMAS.md.
- **D-84 (08-01)** — `direction` prefix peeled from EITHER end of the street string (`W BLOOR STREET` ⇆ `BLOOR ST W` both yield `{normalized='bloor street', direction='W'}`) so Toronto's mixed prefix/suffix data collapses into one key.
- **D-83 (08-01)** — Replaced radius-based DBSCAN leftover clustering with GEO_ID-first then normalized-street + temporal sub-bucketing. Layers 1+2 only; Layer 3 (intersection coordination + new UI color) deferred to v1.1 per Phase-8 CONTEXT scope.
- **D-82 (06-01)** — Counter retween bug was App.jsx wiring (single fetched `metrics` object passed to both views), not the `useCountUp` hook (hook was already correctly keyed on `[target, durationMs]`). Fix derives `naiveMetrics` (savings zeroed) and `displayMetrics = view === "naive" ? naiveMetrics : metrics` client-side so toggling hands TriStatCounter a different object reference, retargeting the tween cleanly. Mono badge fallback chain pinned to ui-monospace/SF Mono/Menlo/Consolas/monospace (no remote fonts — preserves WiFi-off behaviour for Phase 7). GX10 status dot deliberately static (no pulse) per plan acceptance criteria.
- **D-81 (04-02)** — Frontend default view = `optimized` so the demo opens on the value-prop surface (amber merged clusters), not the slate naive baseline. Vite dev binds `[::1]` only — executor smoke-checks use `curl localhost:PORT`, not `127.0.0.1`. `.gitignore` Python virtualenv patterns anchored to repo root (`/lib/`, `/lib64/`) so nested `frontend/src/lib/` is no longer silently ignored.
- **D-80** — Hero block selection takes path (c): rank only geometry-bearing program datasets (road_resurfacing, sidewalk_construction, road_reconstruction); carry utility_cuts + filtered building_permits as bonus address-overlap counts in selection metadata. Decided in Plan 01-02 because the candidate CSVs ship without inline geometry (per 01-01 SUMMARY deviation 3). D-07 building-permit filter recorded into `hero-block.json:selection.building_permit_filter` for audit.
- **D-79** — Optimizer reframes to trench-sharing (anchor + piggyback) using utility-cut-permits as candidates and road-reconstruction / resurfacing / sidewalk programs as anchor windows.
- **D-78** — Phase 5 reduced to verification + screenshots (no fine-tune to eval).
- **D-77** — Phase 2 fine-tune skipped; Phase 5 D-44 fallback narrative is the new anchor.
- **D-76** — Inference engine swapped from NIM to Ollama (`nemotron-3-super:latest` 123B on `:11434`).
- **D-75** — Routing engine swapped from OSRM to Valhalla (arm64-native, port `:5000` preserved).

Full decision log lives in per-phase CONTEXT files.

### Blockers / Concerns

- Phase 3 known limitations (carried into Phase 6 polish):
  - `utility_cuts.csv` ships without inline geometry → 0 piggybacks in demo data. Geocoding the DISPLAY_DESC strings is Phase 4/6 work.
  - Conflict graph is a space-time **proxy**, not a Valhalla `exclude_polygons` precompute (intentional design pivot in c6100d0 — keeps demo offline-runnable). `backend/valhalla.py` is ready for live `/whatif-street` to call if Valhalla is reachable.
  - `per_lane_day_cost` is a $15K placeholder per D-26 — Phase 6 replaces from Toronto Congestion Management Plan.
- Phase 4: ~~hero-centre auto-zoom (D-55) not wired~~ ✅ resolved in 04-02 (`FitToHeroBlock` → `map.fitBounds(bbox)`). Browser UAT still required to confirm visual centring / palette colors / 2s tween / SSE chunking on the live stack — see 04-02-SUMMARY.md handoff table.
- Phase 5 (REDUCED per D-78): `nvidia-smi` screenshot + one live chat round-trip latency screenshot still ❌. Both are 2-minute capture tasks.

## Session Continuity

Last session: 2026-05-31T05:40:00.000Z
Stopped at: Plan 08-01 complete — radius-DBSCAN leftover clustering replaced with Layer-2 (GEO_ID exact match → temporal sub-bucket) then Layer-1 (normalized-street → temporal sub-bucket) in `backend/optimizer.py:cluster_leftover_candidates`; new `backend/street_norm.py` helper (8 tests); `_permit_from_*` constructors emit `normalized_street`/`direction`/`geo_id` (6 loader tests); every recommendation in clusters.json carries additive `match_type` ∈ {same_segment, same_street, piggyback_segment} (9 clustering tests). All 7 Phase-3 artifacts regenerated; SCHEMAS.md gained `## Phase 8 additions` section; HeroMap popup got one additive `match: ...` subtitle. Frontend `vite build` green (65 modules unchanged). Headline numbers unchanged (532 / 3 / $210K) because the GEO_ID-bearing CSVs still lack lat/lon — geocoding is the next blocker for visible lift. human_needed_verification: true.
Resume file: None
