# Phase 4 — UI & Chat Panel

**Window:** Hour 14–22
**Owners:** FE + Fullstack
**Gate:** G2 — End-to-end skeleton at hour 22

## Goal

Wire the optimizer outputs and the Nemotron Super chat into a single screen that tells the demo story without narration. Even with placeholder text in the chat, a judge should already understand the project from the map alone.

## Subsystem A — Map + timeline

- [ ] Load `permits.geojson`, `naive.json`, `optimized.json` into Leaflet
- [ ] Permit polygons rendered with `lane_days` driving opacity/intensity
- [ ] Timeline scrubber (bottom of screen) covers the full historical window
  - Scrubbing animates polygons appearing/disappearing as their windows enter/exit the cursor
  - Play/pause button; default 6× real-time speed
- [ ] Toggle: Naive ↔ Optimized
  - Same scrubber, same speed, but the polygon set differs
  - Smooth crossfade between modes, not a hard cut
- [ ] Savings counter widget — live-updates as scrubber moves: "X excavations avoided · Y lane-days saved · ~$Z cost avoidance"
- [ ] Hero-block focus: map auto-centres on the hero block on load, with a subtle "click to zoom out" affordance

## Subsystem B — Chat panel

- [ ] Right-docked chat UI: input box + streamed response area + small "running on GX10" badge
- [ ] Backend pipeline `/chat`:
  1. Embed query via `nv-embedqa-e5-v5` on `:8003`
  2. Retrieve top-5 relevant permits from DuckDB (cosine sim over a precomputed permit embedding index)
  3. Look up conflict-graph entries for any streets mentioned
  4. Call `/whatif` if query is hypothetical
  5. Compose context block; call Nemotron Super `:8002` with streaming
  6. Stream tokens back to UI via SSE
- [ ] Three canned scenarios with cached responses (for demo safety):
  1. "What if I issue a watermain permit on [hero block street] next month?"
  2. "Which permits in [hero neighbourhood] should I have batched together in 2024?"
  3. "Why can't I issue both [permit A] and [permit B] concurrently?"
- [ ] System prompt embeds the hero-block metrics so even a vague question gets a grounded answer

## Subsystem C — Traffic camera flourish

- [ ] On hover over an active closure, show a small popout of the nearest Traffic Camera (live feed from Toronto Open Data)
- [ ] Cheap, high-impact, judges love it

## Exit criteria (G2)

By end of hour 22:

1. Timeline scrubber plays through the historical window, polygons animate correctly
2. Naive ↔ Optimized toggle works and counter updates
3. Chat panel returns a streamed response from Nemotron Super for at least one live question
4. All three canned scenarios run end-to-end
5. The full 90-second demo loop is *executable* even if some pieces are shallow

## Risks

| Risk | Mitigation |
|---|---|
| Streaming SSE flaky from NIM | Fall back to full-response polling; visually fake the stream client-side |
| Chat takes too long per response | Cap context size aggressively; pre-warm Super by sending a dummy request at app start |
| Toggle crossfade looks ugly | Cut the crossfade, use a hard switch with a 200ms flash overlay |
| Counter feels arbitrary | Source cost-avoidance number from a published City of Toronto figure (per-lane-day cost of construction disruption); cite it on the slide |

## Deliverables to Phase 5

- Fully working UI, end-to-end, even if the LLM model in use is still raw Nemotron Nano
- Three canned chat scenarios cached and replayable
