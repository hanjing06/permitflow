# Phase 6 — Demo Polish

**Window:** Hour 28–34
**Owners:** All (split: pitch, UI polish, deck)
**Gate:** G3 — Offline demo at hour 34

## Goal

Convert a working system into a 90-second presentation that wins. From here on, no new features — only the ones already built getting sharper, faster, and more legible to someone who has never seen the project before.

## The 90-second arc (lock this first, polish to fit)

```
0:00 ─ "Toronto issues 30,000 utility-cut permits a year. Watch one block."
0:10 ─ [Scrubber plays Naive timeline on hero block → 6 red flashes over 18 months]
0:25 ─ "Six teardowns. Three of those could have been one."
0:30 ─ [Toggle to Optimized — same block, 2 closures, counter ticks up]
0:45 ─ "11 redundant excavations avoided. 38 lane-days saved. ~$X cost avoidance."
0:55 ─ "And it understands the city. Watch."
1:00 ─ [Judge or pitch person types canned question into chat panel]
1:10 ─ [Nemotron Super streams response, citing specific permits and traffic impact]
1:25 ─ "All running on this box. Nemotron Nano fine-tuned on Toronto permits in 3 hours overnight."
1:30 ─ [End on the "running on GX10" badge + lift number]
```

## Subsystem A — UI polish

- [ ] Hero block centred and zoomed on load; no manual setup needed
- [ ] Polygon styling: closures are saturated red; merged closures are amber with a thicker outline (visually distinct)
- [ ] Scrubber playhead has a date label that updates smoothly
- [ ] Savings counter animates (number tween, not jump) — small detail, large impact
- [ ] Toggle button has prominent label "Naive | Optimized" with a clear active state
- [ ] Chat panel has a visible "Powered by Nemotron Super 49B · running on GX10" footer
- [ ] Fix the 3 worst visual jank moments — anything that distracts in the recorded run
- [ ] Add the one-line headline metric to the top bar so it's always on screen

## Subsystem B — Pitch + deck

- [ ] Three slides, no more:
  1. Problem: "Toronto torn up 30,000 times a year. Same blocks repeatedly."
  2. System: the architecture diagram from PROJECT.md
  3. Results: the side-by-side raw vs tuned + headline savings
- [ ] Pitch script written out word-for-word and timed
- [ ] Pitch person rehearses to under 90 seconds three times in a row
- [ ] One backup line for each of the 5 likeliest "what went wrong" moments

## Subsystem C — Cost-avoidance number

- [ ] Find a published City of Toronto figure for per-lane-day cost of construction disruption (their congestion management strategy reports cite this)
- [ ] Multiply by the optimizer's saved lane-days for a defensible dollar number
- [ ] Cite the source on the slide (judges respect this; competitors won't bother)

## Subsystem D — Live camera flourish

- [ ] On the hero closure that's about to "happen" in the scrubber, the relevant Traffic Camera live feed appears in a small panel
- [ ] If the camera is offline at demo time, swap to a still image — don't show a dead frame

## Exit criteria (G3)

By end of hour 34:

1. The full 90-second arc runs cleanly, end-to-end, with WiFi *off*
2. All canned chat scenarios return cached responses within 1.5 seconds
3. Pitch script is timed to ≤ 90 seconds
4. Three-slide deck is finished
5. No unfixed UI jank in the recorded path

## Risks

| Risk | Mitigation |
|---|---|
| Cost-avoidance source can't be found | Use a generic figure ("industry estimate: $X per lane-day") and cite a reputable secondary source |
| Live camera feed flakes on demo wifi | Pre-record a 10-second loop of the feed and fall through to that |
| Pitch person freezes | Whoever stands beside them has the script open on their phone |
| Polish creep eats into Phase 7 | Hard stop at hour 34 — even if jank remains, move on; rehearsal matters more |

## Deliverables to Phase 7

- A frozen, polished build
- A finished deck
- A rehearsed pitch script
