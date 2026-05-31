---
phase: 08-street-based-clustering
plan: 01
subsystem: optimizer
tags: [optimizer, clustering, street-normalization, geo-id, dbscan-replacement]
status: completed
human_needed_verification: true

# Dependency graph
requires:
  - phase: 03-optimizer-build
    provides: build_phase3_artifacts pipeline + clusters.json/metrics.json contract
  - phase: 04-ui-chat-panel
    provides: TriStatCounter + HeroMap cluster popup contract (read-only consumer)
provides:
  - backend.street_norm.normalize_street pure helper
  - geo_id + normalized_street + direction on every permit dict
  - cluster_leftover_candidates rewritten as Layer-2 GEO_ID then Layer-1 normalized-street + temporal sub-buckets
  - additive match_type field on every clusters.json entry (same_segment | same_street | piggyback_segment)
  - regenerated Phase-3 artifacts honoring the SCHEMAS.md contract
affects: [phase-09, phase-10, v1.1-geocoding, v1.1-intersection-coordination]

# Tech tracking
tech-stack:
  added: []  # pure-stdlib helper; no new deps
  patterns:
    - "Pure helper module (backend/street_norm.py) — stdlib-only, no I/O, no pandas — importable from anywhere"
    - "Plain-function test runner: tests work without pytest via `python -m backend.tests.test_X`; same files become pytest-discoverable the day pytest lands in the flake"
    - "Try/except import for backend.street_norm so optimizer.py works both as `from backend.optimizer import ...` and as a top-level script"

key-files:
  created:
    - backend/street_norm.py
    - backend/tests/__init__.py
    - backend/tests/test_street_norm.py
    - backend/tests/test_optimizer_loaders.py
    - backend/tests/test_clustering.py
    - .planning/phases/08-street-based-clustering/08-01-SUMMARY.md
  modified:
    - backend/optimizer.py
    - frontend/src/components/HeroMap.jsx
    - .planning/phases/03-optimizer-build/SCHEMAS.md
    - data/artifacts/clusters.json
    - data/artifacts/naive.json
    - data/artifacts/optimized.json
    - data/artifacts/permits.geojson
    - data/artifacts/metrics.json
    - data/artifacts/conflict-graph.json
    - data/artifacts/hero-block.json

key-decisions:
  - "D-83 (08-01) — Replaced radius-based DBSCAN leftover clustering with GEO_ID-first then normalized-street + temporal sub-bucketing. Layers 1+2 only; Layer 3 (intersection coordination + new UI color) deferred to v1.1 per Phase-8 CONTEXT scope."
  - "D-84 (08-01) — `direction` prefix is peeled from EITHER end of the street string (W BLOOR STREET ⇆ BLOOR ST W both yield {normalized='bloor street', direction='W'}) so Toronto's mixed prefix/suffix data still collapses into one grouping key."
  - "D-85 (08-01) — Empty normalized_street is a soft singleton signal; cluster_leftover_candidates NEVER groups unparseable permits under a junk 'unknown' bucket. Documented in SCHEMAS.md."
  - "D-86 (08-01) — `match_type` added as a single additive field on EVERY recommendation (merge AND piggyback) — value piggyback_segment for piggybacks so downstream consumers can rely on the field always being present."
  - "D-87 (08-01) — Tests written as plain assertion-functions runnable via `python -m backend.tests.test_X`. pytest is not in the nix flake pythonEnv and adding it mid-late hackathon was judged too risky; same files become pytest-discoverable the day pytest lands."

patterns-established:
  - "Three-schema dispatch in _permit_from_simple_csv: utility_cuts (DISPLAY_DESC + PROPOSED_*_DATE + GEO_ID) → building_permits (composed STREET_* + GEO_ID) → legacy simple permits.csv path. New candidate CSVs follow this dispatch convention."
  - "_temporal_subclusters greedy 1-D bucketing — reusable for any future same-street/same-segment temporal grouping (Layer-3 intersection coordination will share the helper)."

requirements-completed: [G8-NORM, G8-GEOID, G8-CLUSTER, G8-ARTIFACTS, G8-CONTRACT]

# Metrics
duration: ~35min
completed: 2026-05-31
---

# Phase 8 Plan 01: Street-Based Clustering (Layers 1+2) Summary

**Replaced radius-DBSCAN leftover clustering with GEO_ID exact match → normalized-street + 60-day temporal sub-bucketing, with a new additive `match_type` field on every cluster, all behind a 23-test green suite and a still-green frontend build.**

## Performance

- **Duration:** ~35 min (4 atomic task commits + 1 metadata commit)
- **Started:** 2026-05-31T05:05Z (approx)
- **Completed:** 2026-05-31T05:40Z
- **Tasks:** 4 of 4 (each committed atomically)
- **Test suite:** 23/23 green (8 street_norm + 6 loaders + 9 clustering)
- **Frontend build:** green (65 modules — unchanged from baseline)

## Accomplishments

- New `backend/street_norm.py` — pure stdlib helper canonicalizing Toronto street strings to `{normalized, direction, display}` with the `BLOOR ST W ⇆ W BLOOR STREET` symmetry baked in.
- `_permit_from_open_toronto` + `_permit_from_simple_csv` now emit `normalized_street`, `direction`, `geo_id` on every permit dict; building_permits and utility_cuts schemas dispatched explicitly.
- `cluster_leftover_candidates` rewritten as Layer-2 (GEO_ID exact match → temporal sub-bucket) → Layer-1 (normalized_street → temporal sub-bucket); empty normalized_street is NEVER a group; tunable via `PERMITFLOW_STREET_WINDOW_DAYS` (default 60).
- Every recommendation in `clusters.json` (merges AND piggybacks) carries `match_type` ∈ {`same_segment`, `same_street`, `piggyback_segment`}.
- All 7 Phase-3 artifacts regenerated and committed; SCHEMAS.md gained a `## Phase 8 additions (additive, no removals)` section.
- `HeroMap.jsx` cluster popup gained one additive subtitle line (`match: same street`) — no palette, toggle, or counter change.

## Task Commits

Each task was committed atomically (TDD: tests + impl together per task):

1. **Task 1: `street_norm.py` helper + 8 tests** — `23defc0` (feat)
2. **Task 2: Wire normalized_street/direction/geo_id into constructors + 6 tests** — `f669175` (feat)
3. **Task 3: Rewrite `cluster_leftover_candidates` + 9 tests** — `7fbcafe` (feat)
4. **Task 4: Regenerate artifacts + SCHEMAS.md additive section + HeroMap popup line** — `e8b9026` (feat)

**Plan metadata:** (pending — this commit) (docs: complete 08-01 plan)

## Files Created/Modified

### Created
- `backend/street_norm.py` — pure normalizer; 19-entry `STREET_TYPE_CANONICAL`, 8-entry `DIRECTION_PREFIXES`, `normalize_street(raw) -> dict`.
- `backend/tests/__init__.py` — package marker.
- `backend/tests/test_street_norm.py` — 8 tests.
- `backend/tests/test_optimizer_loaders.py` — 6 tests.
- `backend/tests/test_clustering.py` — 9 tests.

### Modified
- `backend/optimizer.py` — `_coerce_geo_id` helper; `normalize_street` import; 3-schema dispatch in `_permit_from_simple_csv`; rewritten `cluster_leftover_candidates`; new `_temporal_subclusters` helper; `STREET_CLUSTER_WINDOW_DAYS` constant; `match_type` added to piggyback recommendations.
- `frontend/src/components/HeroMap.jsx` — one additive subtitle div under the cluster Popup chronology line.
- `.planning/phases/03-optimizer-build/SCHEMAS.md` — appended `## Phase 8 additions` section.
- `data/artifacts/clusters.json` — regenerated; now carries `match_type`.
- `data/artifacts/naive.json` + `data/artifacts/optimized.json` — regenerated; per-permit objects now carry `normalized_street`, `direction`, `geo_id` (spread by the builder).
- `data/artifacts/permits.geojson` — regenerated; same additive fields on each feature's properties.
- `data/artifacts/metrics.json`, `data/artifacts/conflict-graph.json`, `data/artifacts/hero-block.json` — regenerated identically (no content diff).

## Demo-Number Delta

| Metric                  | OLD (radius-DBSCAN, pre-Phase-8) | NEW (Phase-8 Layers 1+2) |
| ----------------------- | -------------------------------- | ------------------------ |
| `permits_considered`    | 532                              | 532                      |
| `excavations_avoided`   | 3                                | 3                        |
| `cost_avoidance`        | $210,000                         | $210,000                 |
| `cluster_merges`        | 2                                | 2                        |
| `cluster_match_types`   | (none)                           | `same_street`            |

**Why the numbers happen to be identical:** the only candidate CSV that ships with inline lat/lon in v1.0 is `data/permits.csv` (the simple legacy fixture). The GEO_ID-bearing CSVs (`utility_cuts.csv`, `building_permits.csv`) are still silently dropped by the lat/lon guard — geocoding is separate v1.1 work documented in SCHEMAS.md Known limitations. On the 5 permits that DO have coordinates, the old radius-DBSCAN happened to group them the same way the new same-street pass does (both forms group `Queen St W` together and `Dundas St W` together).

**Why the change is still load-bearing and honest:** the optimizer's *physical reasoning* now matches the D-79 trench-sharing thesis instead of coincidentally agreeing with it. Once a geocoder fills in lat/lon for utility_cuts (~99% of candidates), Layer-2 `same_segment` matches will dominate and the headline numbers will move on real semantic grounds, not because the radius happened to cooperate. Every cluster now carries `match_type=same_street` (vs old `match_type=MISSING`), so the cluster popup can credibly explain *why* permits are coordinated.

## Human-Needed Verification

This plan is marked `human_needed_verification: true` because the visible artifact shape changed (popup now carries `match: same street`) and the underlying clustering basis changed even though the headline numbers happen to be identical.

**Eyeball checklist (open `localhost:5173`, or run `nix run .#deploy-tunnel` if it's not running):**

- [ ] Tri-stat counter still tweens to the live numbers (no NaN, no stuck-at-zero).
- [ ] Cluster circles render on the map in the optimized view (no React error boundary, no missing-key warnings).
- [ ] Click a cluster circle → the popup shows a new subtitle line `match: same street` directly under the `N permits · start → end` line. Layout should NOT look crammed — the subtitle is `fontSize: 11, color: #888, marginTop: 2`.
- [ ] Naive ↔ Optimized toggle still works and re-tweens the counter.
- [ ] No regression in the chronology list, savings line, or action italic-text.

**Backend smoke (optional, requires backend running):**
- [ ] `curl localhost:8000/clusters | python -m json.tool | grep match_type` shows `"match_type": "same_street"` on each entry.
- [ ] `curl localhost:8000/metrics | python -m json.tool` returns all 7 Phase-4 keys: `lane_days_saved`, `permits_considered`, `excavations_avoided`, `cost_avoidance`, `piggybacks_accepted`, `cluster_merges`, `conflict_edges`.

**Note on running dev server:** if `nix run .#deploy-tunnel` was alive during execution, uvicorn `--reload` should have picked up the backend changes; the Vite dev server hot-reloaded the popup tweak automatically. If the dev server was NOT running, the new artifacts are on disk waiting for the next launch.

## Frontend Popup Tweak Status

**Applied.** Added a single `<div>` between the chronology summary and the savings line in `HeroMap.jsx`'s cluster `<Popup>` block. The new line is gated by `cluster.match_type` (so it gracefully renders nothing on older clusters.json files) and styled with `fontSize: 11, color: "#888", marginTop: 2` to match the existing subtitle hierarchy. No palette change, no `permitColors.js` change, no React state added. Frontend build green (`vite build` → 65 modules transformed, identical bundle structure).

## Decisions Made

See frontmatter `key-decisions` (D-83 through D-87). Key rationale captured inline above.

## Deviations from Plan

None at the rule-driven level — plan executed exactly as written with one minor TDD adjustment:

### Test Framework Decision

The plan's verify steps reference `nix develop -c pytest backend/tests/...`. pytest is NOT in the nix flake's `pythonEnv` (verified via `python -c "import pytest"` → `ModuleNotFoundError`). Per the executor's project-specific notes, adding pytest to flake.nix mid-hackathon was judged too risky. Tests were written as plain assertion functions runnable via `python -m backend.tests.test_X` and via direct module import. The functions are unchanged signature-wise — the day pytest lands, the same files become pytest-discoverable without modification. Not a Rule-1/2/3 deviation; this is the project-context guidance from the executor's prompt being applied.

## Issues Encountered

- **Initial test_abbreviation_canonicalization_roundtrip failure** — the first draft of `normalize_street` only peeled direction prefixes off the leading token, so `BLOOR ST W` did not collapse to the same key as `W BLOOR STREET`. Fixed by extending step 5 of the algorithm to also peel a trailing direction (`elif len(tokens) >= 2 and tokens[-1] in DIRECTION_PREFIXES`). Test re-run green. The fix is the correct semantics (D-84) — Toronto data uses both forms.

## What Was NOT Done

Scope discipline list — these were explicitly deferred per `08-CONTEXT.md` and the planning_context in the executor prompt:

- **Layer 3 — Intersection coordination** + new `optimization_status="intersection_coordinated"` + new UI color in `permitColors.js`. Deferred to a follow-up phase / v1.1.
- **utility_cuts geocoding** (DISPLAY_DESC → lat/lon). Without lat/lon the GEO_ID-bearing candidates are still silently dropped by the constructors' coordinate guard. Separate v1.1 work; would unlock the `same_segment` cluster path on real data.
- **Anchor LineString spatial joins** (replacing centroid-to-centroid distance with `point-in-buffer(anchor.geometry, 50m)`). Separate v1.1 work — would significantly expand piggyback coverage but is independent of Phase 8.
- **Conflict-graph changes** — none. `build_conflict_graph` untouched. `conflict-graph.json` regenerated identically.
- **Frontend palette / toggle / TriStatCounter / ChatPanel** — untouched except for the one additive popup subtitle.
- **flake.nix changes** — no `pytest` added; nix dev shell unchanged.

## Next Phase Readiness

- The `match_type` field is now reliable on every cluster, so a future plan that wants to render cluster basis differently (e.g. a small icon for `same_segment` vs `same_street`) has the field to key off.
- `_temporal_subclusters` is general-purpose enough to be reused by a Layer-3 intersection-coordination pass.
- The schema-additive change pattern (append to SCHEMAS.md, never modify) worked cleanly — future Phase-N changes should follow the same convention.

## Self-Check: PASSED

Files verified to exist:
- `backend/street_norm.py` — FOUND
- `backend/tests/test_street_norm.py` — FOUND
- `backend/tests/test_optimizer_loaders.py` — FOUND
- `backend/tests/test_clustering.py` — FOUND
- `data/artifacts/clusters.json` (regenerated, with `match_type`) — FOUND
- `data/artifacts/metrics.json` (7 Phase-4 fields intact) — FOUND
- `.planning/phases/03-optimizer-build/SCHEMAS.md` (Phase 8 additions section) — FOUND
- `frontend/src/components/HeroMap.jsx` (match_type subtitle) — FOUND

Commits verified to exist (`git log --oneline`):
- `23defc0` (Task 1) — FOUND
- `f669175` (Task 2) — FOUND
- `7fbcafe` (Task 3) — FOUND
- `e8b9026` (Task 4) — FOUND

---
*Phase: 08-street-based-clustering*
*Completed: 2026-05-31*
