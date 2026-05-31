---
phase: 06-demo-polish
plan: 01
subsystem: frontend-polish
status:
  human_needed_verification: true
tags:
  - frontend
  - polish
  - react
  - hackathon-demo
requirements_satisfied:
  - G6-COUNTER
  - G6-PROJECT-MD
  - G6-BADGE
  - G6-TOGGLE
  - G6-TYPOGRAPHY
dependency_graph:
  requires:
    - 04-02 (frontend rewrite — TriStatCounter + ToggleSwitch + ChatPanel components exist)
    - 03-* (live /metrics endpoint returning permits_considered / excavations_avoided / cost_avoidance)
  provides:
    - "Counter retween behaviour: toggling view hands TriStatCounter a new object reference, which retargets useCountUp."
    - "Polished tri-stat typography (44px, -1.5px tracking, brighter labels)."
    - "Toggle with explicit active-state + 'Naive | Optimized' context caption."
    - "Stable RUNNING ON GX10 · NEMOTRON-3 SUPER 123B badge in chat header."
    - "PROJECT.md demo arc rewritten to future-only framing (D-21 closed)."
  affects:
    - frontend/src/App.jsx (only orchestrator — derives view-matched metrics)
tech-stack:
  added: []
  patterns:
    - "View-derived prop sets to force hook retarget (instead of new useEffect / key on the component)."
decisions:
  - "Mono font fallback chain for the GX10 badge: ui-monospace -> SF Mono -> Menlo -> Consolas -> monospace. Covers macOS, Linux, Windows demo laptops with zero remote-font requests."
  - "Inactive toggle button opacity 0.55 (not 0.4 / 0.6) — keeps the label legible while making the active vs inactive distinction unambiguous at 1m viewing distance."
  - "Green status dot fixed at #10b981 with a 6px halo glow (no pulse). Keeps the 'live' read without competing with the streaming text for attention."
  - "Did NOT span-wrap the $ in fmtMoney. tabular-nums + Inter/system-ui already give a balanced glyph weight; injecting a span would risk per-frame layout jank during the tween."
key-files:
  modified:
    - frontend/src/App.jsx
    - frontend/src/App.css
    - frontend/src/components/ToggleSwitch.jsx
    - frontend/src/components/ChatPanel.jsx
    - .planning/PROJECT.md
  created: []
metrics:
  duration: ~12 minutes
  tasks_completed: 3
  files_changed: 5
  build_status: green (vite v8.0.14, 65 modules, 447ms first build / 431ms second)
  completed_date: 2026-05-31
---

# Phase 6 Plan 01: Demo Polish (counter retween + typography + toggle + badge + PROJECT.md) Summary

Code-only polish pass that closes the gap between "the optimizer works" and "the
demo lands." Fixed the counter retween (root cause was App.jsx wiring, NOT the
hook), bumped tri-stat typography for back-of-room legibility, punched up the
toggle's active state with a context caption, swapped the chat panel's badge to
the period-accurate "RUNNING ON GX10 · NEMOTRON-3 SUPER 123B" anchor line, and
rewrote PROJECT.md's 90-second arc to the future-only framing per D-21.

## What Changed

### Task 1 — Counter retween + tri-stat typography (G6-COUNTER, G6-TYPOGRAPHY)

**Root cause of the retween bug:** the `useCountUp` hook was already correct
(its `useEffect` deps included `[target, durationMs]`, so it retargets cleanly
on prop change). The bug lived in `App.jsx`: `/metrics` was fetched once on
mount and the same `metrics` object was passed to `TriStatCounter` regardless of
view. Both views saw the same target → the hook saw no change → no tween.

**Fix (`frontend/src/App.jsx`):**
```jsx
const naiveMetrics = metrics && {
  permits_considered: metrics.permits_considered,
  excavations_avoided: 0,
  cost_avoidance: 0,
};
const displayMetrics = view === "naive" ? naiveMetrics : metrics;
// ...
<TriStatCounter metrics={displayMetrics} />
```

Permits-considered is the same population in both views (it's the input set,
not an outcome). Naive = no coordination = zero avoided excavations and zero
dollars saved. Toggling now produces three distinct tweens:
- `permits considered`: 532 → 532 (no visible change — that's correct)
- `excavations avoided`: 0 ↔ 3
- `cost avoidance`: $0 ↔ $210,000

**Typography (`App.css`):**
- `.tristat-value`: 32px → 44px, letter-spacing -0.5px → -1.5px (kept
  tabular-nums + weight 700).
- `.tristat-label`: 11px → 12px, color #9ca3af → #cbd5e1 (more contrast on the
  #0f172a strip), margin-top 4px → 8px.
- `.tristat-cell`: padding 16px → 22px so the cells breathe around the larger
  numbers.

**`TriStatCounter.jsx` and `useCountUp.js` are untouched** — typography is pure
CSS and the hook already worked.

Commit: `8ab2e58`

### Task 2 — Toggle active-state + GX10 badge (G6-TOGGLE, G6-BADGE)

**Toggle (`ToggleSwitch.jsx`, `App.css`):** wrapped the existing `.toggle` div
in a `.toggle-wrap` column with a `.toggle-context` caption reading "Naive |
Optimized" above the buttons — so a first-time judge knows what's being
switched. Active button now has:
- font-size 14px → 15px (larger than inactive)
- font-weight 700 (heavier than inactive's 600)
- amber box-shadow glow: `0 0 0 1px #fbbf24, 0 2px 6px rgba(245, 158, 11, 0.35)`

Inactive button gets `opacity: 0.55` so it's clearly muted. 120ms ease-out
transition keeps the swap feeling snappy without distracting from the counter
tween.

**Chat badge (`ChatPanel.jsx`, `App.css`):** replaced the lowercase "running on
GX10" span with a structured badge:

```jsx
<span className="chat-badge gx10-badge">
  <span className="gx10-dot" />
  RUNNING ON GX10 · NEMOTRON-3 SUPER 123B
</span>
```

The `.gx10-badge` is mono (ui-monospace fallback chain), uppercase, with a
1px amber border. The `.gx10-dot` is a 7px green static circle with a soft
glow — read as "alive" without any pulse animation (deliberately stable per
plan acceptance criteria).

ChatPanel's streaming / SSE / canned-scenario logic is untouched.

Commit: `87f3063`

### Task 3 — PROJECT.md demo-arc rewrite (G6-PROJECT-MD, D-21)

Replaced the historical-replay arc bullet ("Time-lapse on the hero block — 6
separate red closures over 18 months") with the future-only version mandated by
D-21 (Phase 3 pivot to next-quarter window):

> Hero block, next quarter: ~530 utility-cut permits already planned for this
> ~1 km² of Toronto over the coming 90 days. Map opens on the block,
> auto-zoomed, each permit a static polygon coloured by week.

Also flipped success criterion 3's "historical window" → "next-quarter window"
so the measured-by column matches the arc. Architecture diagram, memory budget,
risks/cut-list, and all other sections untouched.

Commit: `5dfe515`

## Deviations from Plan

**None.** All three tasks executed exactly as specified in the plan. No Rule
1/2/3 auto-fixes were needed — the codebase was clean, the hook was already
correct (as the plan's `<interfaces>` block predicted), and there were no
pre-existing build warnings to navigate around.

## Verification

| Check | Result |
|-------|--------|
| `npm run build` (after Task 1) | exit 0, 447ms |
| `npm run build` (after Task 2) | exit 0, 431ms |
| Task 1 grep checks (`naiveMetrics`, `displayMetrics`, `44px`) | PASS |
| Task 2 grep checks (`toggle-wrap`, `toggle-context`, `NEMOTRON-3 SUPER 123B`, `gx10-badge`, `gx10-dot`) | PASS |
| Task 3 grep checks (`next quarter`, `next-quarter window`, no `Time-lapse`, no `historical window`) | PASS |
| Dev server still serves on localhost:5173 | HTTP 200 |
| All phase-level checks | PASS |

## Human-Needed Verification (eyeball pass — `human_needed_verification: true`)

The polish targets here are visual; the build green and grep matches do not
prove the demo lands. Run the local stack (`nix run` or whatever's already on
:5173) and verify the following at 1m viewing distance, projector-grade:

1. **App opens on Optimized.** Counter tweens 0 → 532 / 3 / $210,000 over ~2s
   on first load (existing behaviour preserved).
2. **Click Naive.** Counter visibly counts DOWN over ~2s:
   - permits considered: 532 → 532 (stays put — same population)
   - excavations avoided: 3 → 0
   - cost avoidance: $210,000 → $0
3. **Click Optimized.** Counter visibly counts UP over ~2s back to 532 / 3 /
   $210,000.
4. **Tri-stat typography.** Numbers feel large (44px), tabular-aligned. The
   `$` glyph in "$210,000" should not look heavier than the digits. Labels
   ("permits considered", "excavations avoided", "cost avoidance") are
   readable against the slate strip.
5. **Toggle.** A small "NAIVE | OPTIMIZED" caption sits above the buttons.
   The active button is visibly larger / heavier / has an amber glow. The
   inactive button is clearly dimmed (~55% opacity) — no ambiguity about
   which one is selected.
6. **GX10 badge.** Chat header reads exactly
   `● RUNNING ON GX10 · NEMOTRON-3 SUPER 123B` in monospace, with a small
   green dot on the left. **Must not blink, pulse, or animate.** Static dot
   only.
7. **PROJECT.md.** Open `.planning/PROJECT.md` § "Hackathon constraints"
   → "Demo arc (90 seconds)". Must read as future-only ("next quarter / next
   90 days"). No "Time-lapse" / "18 months" / "historical" wording anywhere
   in the file.

If any of the above fails, the resume signal back to the executor should name
the specific item (e.g., "badge text is wrong" / "counter snaps instead of
tweening" / "active toggle still ambiguous").

## Handoff to Phase 7 (Dry Runs & Backup)

- **No remote fonts or assets were introduced.** The mono fallback chain is
  100% system-installed (ui-monospace / SF Mono / Menlo / Consolas /
  monospace), the green dot is CSS (no SVG fetch), the amber palette is hex.
  Phase 7's WiFi-off test should still pass without changes.
- **No new dependencies in `package.json`.**
- **No backend / optimizer / data-layer changes.** Phase 7 can record the
  backup video against the same stack that Phase 4 verified.
- **Demo timing implication:** the bigger counter font + brighter labels make
  the tri-stat visible from further away, so the pitch lead can let the
  toggle tween breathe (~2s) without the audience losing the numbers
  mid-animation.

## Known Stubs

None. The naive-view metrics are derived deterministically from the optimized
metrics (zero out the savings fields) — this is the correct domain semantics,
not a placeholder.

## Self-Check: PASSED

- File `.planning/phases/06-demo-polish/06-01-SUMMARY.md` — FOUND (this file)
- Commit `8ab2e58` (Task 1) — FOUND in git log
- Commit `87f3063` (Task 2) — FOUND in git log
- Commit `5dfe515` (Task 3) — FOUND in git log
- All five files in `key-files.modified` exist and were committed.
