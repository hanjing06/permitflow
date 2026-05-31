---
phase: 04-ui-chat-panel
plan: 02
subsystem: ui
tags: [react, react-leaflet, leaflet, vite, sse, streaming, components, dark-theme]

# Dependency graph
requires:
  - phase: 04-ui-chat-panel
    provides: "POST /chat (SSE), POST /retrieve, GET /chat/scenarios from 04-01"
  - phase: 03-optimizer-build
    provides: "GET /hero-block, GET /naive, GET /optimized, GET /metrics — the data the new UI renders"
provides:
  - "frontend/src/App.jsx — 37-line orchestrator wiring HeroMap + ToggleSwitch + TriStatCounter + ChatPanel"
  - "frontend/src/components/HeroMap.jsx — Leaflet map that auto-centres on /hero-block bbox and renders /naive or /optimized polygons coloured by optimization_status"
  - "frontend/src/components/ToggleSwitch.jsx — Naive ↔ Optimized hard-cut switch (D-32)"
  - "frontend/src/components/TriStatCounter.jsx — three equal-weight metrics each animated by useCountUp(2000ms) (D-33 / D-34)"
  - "frontend/src/components/ChatPanel.jsx — right-docked SSE consumer (POST /chat + ReadableStream getReader()) with 3 canned-scenario buttons (D-37 / D-38)"
  - "frontend/src/lib/permitColors.js — STATUS_COLOR / STATUS_FILL_OPACITY / colorFor / fillOpacityFor"
  - "frontend/src/lib/useCountUp.js — React hook (ease-out cubic) for 2-second number tweens"
  - "frontend/src/App.css — dark-themed two-row + three-cell + right-dock layout with the GSD-aware palette"
affects: [polish, demo, pitch-prep]

# Tech tracking
tech-stack:
  added: []  # No new npm dependencies — react-leaflet 5 useMap + native fetch ReadableStream were sufficient.
  patterns:
    - "Thin App.jsx orchestrator: state + 1 effect, all rendering delegated to ./components/*"
    - "FitToHeroBlock micro-component: child of MapContainer using react-leaflet's useMap() hook to imperatively call map.fitBounds() from a /hero-block fetch result"
    - "SSE client parser: response.body.getReader() + TextDecoder + manual 'data: ...\\n\\n' frame splitting; treats 'data: [DONE]' as terminator, unescapes '\\n' back to literal newlines for display"
    - "useCountUp hook called unconditionally at top level (rules of hooks) before any conditional early return"

key-files:
  created:
    - "frontend/src/components/HeroMap.jsx"
    - "frontend/src/components/ToggleSwitch.jsx"
    - "frontend/src/components/TriStatCounter.jsx"
    - "frontend/src/components/ChatPanel.jsx"
    - "frontend/src/lib/permitColors.js"
    - "frontend/src/lib/useCountUp.js"
    - ".planning/phases/04-ui-chat-panel/04-02-SUMMARY.md"
  modified:
    - "frontend/src/App.jsx — rewritten from 203-line CircleMarker viewer to 37-line component orchestrator"
    - "frontend/src/App.css — rewritten from 2-column sidebar layout to topbar + tristat + (map + chat-panel) dark layout"
    - ".gitignore — anchored `lib/` and `lib64/` to repo root (was matching frontend/src/lib unintentionally)"

key-decisions:
  - "Default view is 'optimized' on first load so the demo opens on the win surface, not the noise baseline"
  - "Vite dev-server check uses IPv6 localhost (Vite binds to [::1] only by default); curl 127.0.0.1 fails but curl localhost succeeds — left default binding alone, this is a smoke-test detail not a runtime issue"
  - "Anchored Python virtualenv patterns in .gitignore (`/lib/`, `/lib64/`) so nested `frontend/src/lib/` stops being silently ignored"

patterns-established:
  - "Components live under src/components/ with PascalCase filenames; pure helpers and hooks live under src/lib/"
  - "Components fetch their own data; App.jsx owns only cross-component state (current view + metrics)"
  - "Palette is centralised in src/lib/permitColors.js — single source of truth for any future map/legend additions"
  - "Vite dev binds [::1] only — use `curl localhost:PORT` (not 127.0.0.1) for executor smoke checks"

requirements-completed: [G4-HERO, G4-TOGGLE, G4-COUNTER, G4-CHAT]

# Metrics
duration: 6min
completed: 2026-05-31
---

# Phase 4 Plan 02: Frontend Component Rewrite Summary

**Component-based SPA — HeroMap auto-centres on Greektown via /hero-block bbox, ToggleSwitch hard-cuts Naive↔Optimized with GSD-palette polygon recolour, TriStatCounter tweens three metrics over 2s, and a right-docked ChatPanel streams /chat SSE frames with three canned-scenario buttons.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-31T00:47:34Z
- **Completed:** 2026-05-31T00:53:29Z
- **Tasks:** 4 (3 code commits + 1 build/serve verification)
- **Files modified:** 9 (6 created components/lib, 2 rewritten App.{jsx,css}, 1 .gitignore tweak)

## Accomplishments
- `App.jsx` shrank from 203 lines (CircleMarker viewer with cluster sidebar) to **37 lines** of pure orchestration — well under the <50-line success-criterion ceiling.
- All four CONTEXT decisions (D-32 hard cut, D-33 tri-stat, D-34 2-second tween, D-55 hero auto-centre) are wired in code and verified at the build/transform level.
- ChatPanel parses SSE frames natively via `response.body.getReader()` — no `EventSource`, which keeps the contract compatible with the POST + JSON-body interface 04-01 shipped (`EventSource` only supports GET).
- `vite build` produces a clean bundle (`dist/index-NISfiIKB.js` 350 kB / 107 kB gzipped, `dist/index-0TYvu_qN.css` 19.6 kB / 7.8 kB gzipped) in 395 ms with zero errors / zero warnings.
- Dev server serves the SPA shell and transforms every new module on demand (App.jsx, HeroMap.jsx, ChatPanel.jsx, useCountUp.js all returned 200 with non-empty bodies through `vite dev`).
- No new npm dependencies added — the existing `react@19`, `react-leaflet@5`, `leaflet@1.9` stack carries everything (react-leaflet's `useMap()` + native `fetch` ReadableStream).

## Task Commits

1. **Task 1: Add color palette + count-up hook libraries** — `708e893` (feat)
2. **Task 2: Create HeroMap, ToggleSwitch, TriStatCounter, ChatPanel components** — `d341427` (feat)
3. **Task 3: Rewrite App.jsx as orchestrator + extend App.css with new layout/palette** — `394b0a1` (feat)
4. **Task 4: Build the frontend and confirm it bundles + serves** — no commit (runtime verification only)

**Plan metadata:** *(this SUMMARY commit)*

## Component Tree

```
App
├─ .topbar
│  ├─ .brand (PermitFlow / Toronto · Greektown corridor)
│  └─ ToggleSwitch (Naive | Optimized)
├─ TriStatCounter
│  ├─ permits considered     (tween: useCountUp(n, 2000))
│  ├─ excavations avoided    (tween)
│  └─ $ cost avoidance       (tween, $-formatted)
└─ .main
   ├─ HeroMap
   │  ├─ MapContainer
   │  ├─ TileLayer (OSM)
   │  ├─ FitToHeroBlock (useMap → map.fitBounds(bbox))
   │  └─ Polygon × N        (coloured by optimization_status)
   └─ ChatPanel
      ├─ .chat-header (Ask PermitFlow + "running on GX10" badge)
      ├─ .chat-canned (3 quick-prompt buttons → POST /chat)
      ├─ .chat-response (streamed text accumulator)
      └─ .chat-input-row (textarea + Send → POST /chat)
```

## Palette (per D-32 discretion — GSD-aware red/amber/neutral)

| Optimization status | Hex       | Role                                           | Fill opacity |
|---------------------|-----------|------------------------------------------------|--------------|
| `coordinated`       | `#f59e0b` | Amber — merged cluster (the "win" surface)     | 0.55         |
| `conflict_deferred` | `#dc2626` | Shifted red — visible cost of not coordinating | 0.55         |
| `singleton`         | `#9ca3af` | Neutral grey — singleton (no opinion)          | 0.35         |
| `naive`             | `#6b7280` | Slate — pre-optimization baseline              | 0.40         |
| *unknown / default* | `#6b7280` | Fallback                                       | 0.40         |

UI surface palette: background `#0b0f17`, panel `#111827`, divider `#1f2937`, primary text `#f9fafb`, secondary text `#9ca3af`, accent (toggle-active, focus ring, send button) `#f59e0b` — keeping the amber accent in the same family as the `coordinated` polygons so the active-state colour reads as "this is the optimised view".

## Build Output (Task 4)

```
vite v8.0.14 building client environment for production...
✓ 65 modules transformed.
dist/index.html                   0.45 kB │ gzip:   0.29 kB
dist/assets/index-0TYvu_qN.css   19.64 kB │ gzip:   7.77 kB
dist/assets/index-NISfiIKB.js   350.06 kB │ gzip: 106.60 kB
✓ built in 395ms
```

No warnings (no chunk-size warning either — react-leaflet 5 + leaflet 1.9 + the new components together stay well under Vite's 500 kB default warning threshold). No "error", "rollup failed", or "build failed" lines in the build log.

Dev-server smoke check (via `npx vite --port 5179 --strictPort` inside `nix develop`):
- `curl localhost:5179/` → 200, returns SPA shell with `<div id="root"></div>` and `<script type="module" src="/src/main.jsx">`.
- `curl localhost:5179/src/App.jsx` → 200, 6934 bytes (Vite JSX transform succeeded).
- `curl localhost:5179/src/components/HeroMap.jsx` → 200, 12 076 bytes.
- `curl localhost:5179/src/components/ChatPanel.jsx` → 200, 13 432 bytes.
- `curl localhost:5179/src/lib/useCountUp.js` → 200, 4211 bytes.

## Decisions Made
- **Default view = `optimized`.** Demo should open on the value-prop surface, not the baseline. A judge glancing at the screen for one second should see the amber clusters, not the slate naive permits.
- **`useCountUp` is called unconditionally before the loading early-return** in TriStatCounter — rules of hooks. The hook handles a `null`/`NaN` target by no-op'ing inside its effect, so passing `metrics?.permits_considered ?? 0` keeps the hook count stable across the loading→loaded transition.
- **SSE parser keeps `acc` in a local variable, not state.** `setResponse(acc)` is called on every frame so React renders incrementally, but `acc` is local — avoids stale-closure issues when frames arrive faster than React commits.
- **`extract` of newlines (`\\n` → `\n`)** happens client-side in ChatPanel to mirror the 04-01 backend's escape — the backend escapes for SSE-line safety, the frontend un-escapes for display.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Anchored `.gitignore` Python virtualenv patterns**
- **Found during:** Task 1 (first `git add` after creating `frontend/src/lib/`)
- **Issue:** `.gitignore` lines 17–18 had unanchored `lib/` and `lib64/` (the standard Python virtualenv pattern). Unanchored globs match at any depth — `frontend/src/lib/permitColors.js` was silently ignored. `git add` failed with `paths are ignored by one of your .gitignore files`.
- **Fix:** Changed `lib/` → `/lib/` and `lib64/` → `/lib64/` so the patterns only match repo-root virtualenv directories. The frontend lib dir is now visible to git; the original Python-venv intent is preserved.
- **Files modified:** `.gitignore`
- **Verification:** `git check-ignore -v frontend/src/lib/permitColors.js` → no match.
- **Committed in:** `708e893` (folded into Task 1's commit since Task 1 couldn't land without it).

**2. [Rule 3 — Blocking] Used IPv6 localhost for the Task 4 dev-server smoke check**
- **Found during:** Task 4
- **Issue:** Vite 8 binds to `[::1]` (IPv6 loopback) only by default; the plan's `curl http://127.0.0.1:5173/ ...` line returned ECONNREFUSED even though `ss` showed Vite listening. Plan-as-written would have falsely failed Task 4 verification.
- **Fix:** Switched the smoke check to `curl http://localhost:5179/` (which resolves to `::1` and connects). Also used `--strictPort` on Vite so we don't hop to 5174 silently when 5173 is already in use by an unrelated long-running dev server on this host (`pid 179786`).
- **Files modified:** none (executor-side test plumbing)
- **Verification:** `curl localhost:5179/` returned the SPA shell with `<div id="root">`; four module endpoints also returned 200.
- **Committed in:** n/a (Task 4 is verification-only).

**3. [Rule 1 — Bug, retroactive] Removed a CRLF `\r` artefact from `/tmp/permitflow-04-02-start.txt` capture**
- Not a code change — only mentioned because the duration computation used `grep -oE '[0-9]+$'` to skip the leading `START: ...` prefix, not because of an actual bug in committed code.

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking). Plan body was correct on substance; both fixes were environment plumbing.
**Impact on plan:** Zero scope creep. The `.gitignore` change is permanent and benign (it preserves the original Python-venv intent while unblocking the entire `frontend/src/lib/` tree for git).

## Issues Encountered
- `npm` and `node` are not on the host PATH — only inside `nix develop` (same situation as 04-01). All build / dev-server commands were wrapped with `nix develop /home/shmul95/Repositories/permitflow --command bash -c "..."`.
- The first dev-server smoke attempt died because the spawned `vite` process was tied to a nix-develop subshell that exited at the end of the wrapper command. Switched to the `run_in_background` harness so the process owner stayed alive long enough to curl the shell, then `pkill -f "vite --port 5179"` torn it down.

## Observed External State During Smoke Test
- Backend (`POST /chat`, `GET /metrics`, etc. from 04-01) was **not** running during this plan's verification — the executor only verified that the frontend bundles and the dev server serves the shell. Live request behaviour (graceful-degradation badges, streaming text, hero-block auto-fit) was **not** exercised. That's the human-UAT scope below.

## ⚠ Browser-Level UAT Required (D-32, D-33, D-34, D-55, D-41 visual confirmation)

**The executor verified ONLY that the bundle builds and the components mount.** The following must be confirmed by a human in a real browser before this plan is considered complete by the demo:

| Item | Decision | How to verify |
|------|----------|---------------|
| Map opens centred on the Greektown corridor (zoom ~15, not citywide zoom 11) | D-55 | Backend up. Visit `http://localhost:5173/`. Expect Danforth Ave to fill ~70 % of the map; the OSM Toronto basemap should NOT be visible at the citywide scale. |
| Optimized view shows amber (coordinated) + red (conflict_deferred) + grey (singleton) polygons; Naive view shows uniform slate polygons | D-32 | Backend up. Click `Naive` and `Optimized` repeatedly. Polygons should hard-cut between the two palette sets — no fade. |
| Tri-stat counter shows three numbers at equal visual weight; numbers tween from previous value to new value over ~2 seconds when the toggle flips | D-33 / D-34 | Watch the three numbers when you click the toggle. They should count up/down smoothly, not snap. |
| Chat panel streams response token-by-token from `/chat`; three canned-scenario buttons each fire a request | D-37 / D-38 / D-41 | Click one of the three canned buttons. Text should appear progressively, not all at once. Or type a question and hit Enter / Send. |
| Backend graceful-degradation surfaces visibly (chat shows the fallback `[chat unavailable — Ollama is offline…]` text when Ollama is down) | n/a (verifies 04-01 contract) | Take Ollama down (close the SSH tunnel) and re-fire a chat. Expect the fallback string + `[DONE]`; UI should NOT crash. |

The plan frontmatter flags `human_needed_verification: true` — this section is the explicit handoff. The orchestrator MUST route to UAT (`/gsd-verify-work`) before marking the phase complete.

## User Setup Required
None for this plan in isolation. For end-to-end UAT, the user needs:
1. The FastAPI backend from 04-01 running on `localhost:8000`. From the repo root: `nix develop --command bash -c "cd backend && uvicorn main:app --host 127.0.0.1 --port 8000"`.
2. The frontend dev server running on `localhost:5173`. From the repo root: `nix develop --command bash -c "cd frontend && npm run dev"`.
3. (Optional, for live chat) The GX10 SSH tunnel up so Ollama on `:11434` and NIM embedder on `:8003` are reachable. Without the tunnel, the chat panel still works — it just shows the 04-01 fallback string.

## Next Phase Readiness
- Frontend now consumes every endpoint Phase 4 (both plans) ships: `/hero-block`, `/naive`, `/optimized`, `/metrics`, `/chat`, and the canned-scenario plumbing.
- Phase 6 polish can edit any single component file (`HeroMap`, `ToggleSwitch`, `TriStatCounter`, `ChatPanel`) without touching the others — clean component isolation.
- The amber/red/neutral palette is centralised in `frontend/src/lib/permitColors.js`; Phase 6 colour tweaks live there.
- **Open polish items for Phase 6** (deliberately deferred per 04-CONTEXT D-31 and the plan's note on `index.css`):
  - `frontend/src/index.css` still ships Vite's `#root { width: 1126px; max-width: 1280px; ... }` starter constraint. App.css overrides it via the `.app` flex layout, but if the viewport feels constrained on a hi-DPI projector it's an `index.css` cleanup.
  - Timeline scrubber animation (D-31) — only if Phase 6 has time.
  - Crossfade toggle transitions — explicitly out for MVP per D-32.

## Self-Check: PASSED

- `frontend/src/App.jsx` — FOUND
- `frontend/src/App.css` — FOUND
- `frontend/src/lib/permitColors.js` — FOUND
- `frontend/src/lib/useCountUp.js` — FOUND
- `frontend/src/components/HeroMap.jsx` — FOUND
- `frontend/src/components/ToggleSwitch.jsx` — FOUND
- `frontend/src/components/TriStatCounter.jsx` — FOUND
- `frontend/src/components/ChatPanel.jsx` — FOUND
- `.planning/phases/04-ui-chat-panel/04-02-SUMMARY.md` — FOUND
- `frontend/dist/index.html` — FOUND
- Commit `708e893` (Task 1: palette + useCountUp + .gitignore unblock) — FOUND
- Commit `d341427` (Task 2: HeroMap / ToggleSwitch / TriStatCounter / ChatPanel) — FOUND
- Commit `394b0a1` (Task 3: App.jsx rewrite + App.css) — FOUND

---
*Phase: 04-ui-chat-panel*
*Completed: 2026-05-31*
