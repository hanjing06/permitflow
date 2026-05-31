---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
stopped_at: Plan 04-02 complete — frontend rewritten as component-based UI (HeroMap + ToggleSwitch + TriStatCounter + ChatPanel). Build green. Browser UAT required for visual centring/colors/tween/SSE per D-32/D-33/D-34/D-55/D-41.
last_updated: "2026-05-31T00:58:04.382Z"
last_activity: 2026-05-31
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 9
  completed_plans: 4
  percent: 44
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-30) · .planning/HEALTHCHECK.md (mid-execution gap snapshot)

**Core value:** Cut redundant Toronto road excavations via trench-sharing (anchor-and-piggyback) and Valhalla conflict-aware scheduling, narrated by Ollama-served Nemotron-3 Super 123B running locally on a GX10.

**Current focus:** Phase 04 — ui-chat-panel (both plans shipped; awaiting browser UAT)

## Current Position

Phase: 04 (ui-chat-panel) — READY FOR VERIFICATION (browser UAT)
Plan: 2 of 2 ✅ (both 04-01 backend SSE + 04-02 frontend rewrite complete)
Phases done: 1, 2 (closed), 3, 4 (code-complete), 5 (reduced)
Phases remaining: 6, 7
Last activity: 2026-05-31

Progress: [████░░░░░░] 44%

See `.planning/HEALTHCHECK.md` for the per-phase delta — Phase 3 rows flip ❌ → ✅; Phase 4 D-32 / D-33 / D-34 / D-55 / D-41 wired (visual UAT pending).

## Accumulated Context

### Decisions (latest 5)

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

Last session: 2026-05-31T00:58:04.350Z
Stopped at: Plan 04-02 complete — frontend rewritten as component-based UI (HeroMap + ToggleSwitch + TriStatCounter + ChatPanel). Build green. Browser UAT required for visual centring/colors/tween/SSE per D-32/D-33/D-34/D-55/D-41.
Resume file: None
