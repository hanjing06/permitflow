# Phase 4: UI & Chat Panel - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire Phase 3's optimizer outputs and Nemotron Super chat into a single Leaflet screen. Map shows planned-future permits (naive vs optimized), tri-metric counter, and a right-docked chat panel that answers hero-block hypotheticals. Exit when the full 90-second demo loop is executable end-to-end, even with placeholder reasoning.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**5 success criteria are locked.** See `04-SPEC.md`.

**In scope:** Leaflet map · toggle · counter · chat panel · canned scenarios · camera flourish
**Out of scope:** Optimizer logic (Phase 3) · model swap (Phase 5) · pitch deck (Phase 6)

**Upstream constraints:**
- Phase 2 D-14: embedder NIM is offline during training (hours 4–22). Phase 4 dev window is hours 14–22 — at least half of it without embeddings.
- Phase 3 D-20/D-21: future-only optimizer. The demo arc is *prospective*, not retrospective.

</spec_lock>

<decisions>
## Implementation Decisions

### Timeline Scrubber — **Static for MVP**
- **D-30:** **No timeline animation for the MVP.** Render all ~80 next-quarter planned permits as a **static color-coded snapshot** (color = week within the quarter). Toggle Naive↔Optimized still works on the static view — polygons reshape and recolor.
- **D-31:** **Animation is a Phase 6 polish item, conditional on time.** If Phase 4 finishes ahead, add a play button that animates day 1→day 90 in ~12 seconds. If not, the static snapshot is the demo. Counter still ticks up to its final value over ~2 seconds on toggle for kinetic feel.
- **D-32:** Toggle behavior: Naive view shows all 80 permits as planned (each independent). Optimized view shows them re-grouped (merged clusters in amber, conflict-deferred in shifted-red, singletons in neutral). No crossfade in MVP — hard switch.

### Counter Design
- **D-33:** **Three equal metrics, side by side**: `permits_considered` · `excavations_avoided` · `$ cost_avoidance`. Same font size, same prominence. Tri-stat dashboard layout.
- **D-34:** Counter values animate (number tween) over 2 seconds on toggle so the user feels the optimizer "do work." Static end-states between toggles.
- **D-35:** Pitch lead must rehearse a single-sentence framing that *picks one* of the three numbers as the headline for the narrative (likely `excavations_avoided`), since the visual treats them equally.

### Canned Chat Scenarios — **Owned by Pitch Lead**
- **D-36:** The 3 canned scenarios are **drafted by the Pitch Lead during Phase 6**, not pre-locked here. They evolve with the pitch script.
- **D-37:** **Hard deadline: scenarios must be locked, cached, and tested by hour 30** (mid-Phase 6) — leaves 4 hours for any failures to surface during dry runs. If not locked by hour 30, fall back to the placeholder set: *Coordination / Conflict / Why-not* (the Recommended set from this discussion).
- **D-38:** Phase 4 ships with a working `/chat` endpoint and a UI panel that streams responses. The *content* of the canned set is deferred; the *plumbing* must exist.

### Chat Retrieval — Phased (revised by D-76)
- **D-39:** **Embedder is up from hour 0** (D-77 closed Phase 2, so the "embedder offline during training" window from D-14 no longer applies). RAG via NIM `nv-embedqa-e5-v5` on `:8003` is available end-to-end. Keyword fallback path stays in the codebase as a safety net but is not the primary path.
- **D-40:** RAG retrieval queries embed against `nv-embedqa-e5-v5`, retrieve top-5 hero-block permits from DuckDB, pass as context to the chat model. Single mode, no phased swap.
- **D-41:** Pipeline shape: embed query → top-5 retrieval → conflict-graph lookup → `/whatif` call (if hypothetical) → **stream from Ollama `nemotron-3-super:latest` on `:11434/v1/chat/completions`**. The chat model is the 123B local reasoning model (per D-76), not NIM Super 49B as originally planned.

### Claude's Discretion
- React component structure, SSE vs polling for streaming, font choice, color palette (use the GSD-aware palette from PROJECT.md's status table — red/amber/neutral for closures), spinner styling, error boundary placement, FastAPI route ordering.

</decisions>

<canonical_refs>
## Canonical References

### Phase 4
- `.planning/phases/04-ui-chat-panel/04-SPEC.md` — **Locked requirements.**

### Project-level
- `.planning/PROJECT.md` — demo arc (note: D-21 pivot pending update; this phase implements the *new* arc)
- `.planning/phases/03-optimizer-build/03-CONTEXT.md` — D-22/D-24/D-25/D-28/D-29 (the data this phase visualizes)
- `.planning/phases/02-finetune-kickoff/02-CONTEXT.md` — D-14 (embedder offline window justifies D-39/D-40)

### External docs
- Leaflet docs — `leafletjs.com/reference.html`
- React 18 — assumed stack; defer to executor for exact version
- SSE in FastAPI — `fastapi.tiangolo.com/advanced/custom-response/#using-streamingresponse-with-server-sent-events`
- Nemotron Super 49B model card — `build.nvidia.com/nvidia/llama-3-3-nemotron-super-49b-v1` (or current variant)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 ships Vite + React + Leaflet scaffold. Phase 4 adds map data layers, scrubber widget (static for MVP), counter widget, chat panel.
- Phase 3 produces `clusters.json`, `conflict-graph.json`, `naive.json`, `optimized.json`, `metrics.json`, plus the `/whatif` FastAPI endpoint. Phase 4 consumes these.
- FastAPI process is already running on GX10 from Phase 3 — add `/chat` route, don't spin a new service.

### Established Patterns
- Single FastAPI process hosts all backend routes (`/whatif`, `/chat`, `/metrics`). Frontend is one Vite SPA. No microservice gymnastics.

### Integration Points
- Chat panel and normalization both talk to Ollama `:11434` (`nemotron-3-super:latest`), per D-41 and D-76. Phase 5 model-swap is no longer relevant — single resident model.
- Phase 6 polish edits this phase's UI components, not its data contracts.

</code_context>

<specifics>
## Specific Ideas

- User questioned animation value: *"don't animate for the mvp or is it really useful?"* — captured the instinct in D-30. Ship static, polish to animated if time allows. Animation is a **judge-attention multiplier** but not a feature. Don't fight a Phase 4 scope expansion to ship it.
- User deferred canned chat to pitch lead — captured as D-36 with a hard deadline (D-37). If pitch lead is late, the fallback set fires automatically. No "we forgot to cache" failure mode allowed.

</specifics>

<deferred>
## Deferred Ideas

- **Timeline animation** — Phase 6 if time. D-31.
- **Crossfade toggle transitions** — polish, not MVP.
- **Sound cues on counter tick** — fun but distracting on stage. Skip.
- **In-chat citations linking to specific permits on the map** — would be slick but adds scope. Post-hackathon.

</deferred>

---

*Phase: 4-UI & Chat Panel*
*Context gathered: 2026-05-30*
