# Phase 4: UI & Chat Panel - Discussion Log

**Date:** 2026-05-30
**Mode:** Interactive (autonomous --interactive), batched

---

## Area 1: Timeline scrubber animation

**Options presented:** Day-by-day 90-day playback / Full quarter 4× / No timeline static / Two stacked timelines

**User selection:** "dont animate for the mvp or is it really usefull ?"

**Claude's interpretation:** User wants to scope down. Animation deferred. MVP ships static color-coded snapshot.

**Decisions captured:** D-30 (static MVP), D-31 (animation = Phase 6 if time), D-32 (hard toggle, no crossfade)

---

## Area 2: Counter design

**Options presented:** Giant headline + subtext / Two equal / Three equal / Permits hero + savings fine print

**User selection:** Three equal: permits + avoided + $

**Decisions captured:** D-33 (tri-stat), D-34 (number tween animation on toggle), D-35 (pitch lead must verbally pick the headline metric)

---

## Area 3: Canned chat scenarios

**Options presented:** Coordination/Conflict/Why-not (recommended) / Three what-ifs / Savings/Forecast/Tradeoff / Defer to pitch lead

**User selection:** Let pitch lead draft them in Phase 6

**Claude's safety net:** Hard deadline hour 30 (D-37). If not locked, the Recommended set auto-fires as fallback. Plumbing (chat endpoint, panel) ships in Phase 4 regardless of content.

**Decisions captured:** D-36, D-37, D-38

---

## Area 4: Embedder-offline chat retrieval

**Options presented:** Hard-code hero permits / Keyword fallback / Defer chat to hour 22 / Skip embedder entirely

**User selection:** Keyword retrieval as fallback

**Decisions captured:** D-39 (keyword during hours 14–22), D-40 (swap to embeddings at hour 22 via adapter interface), D-41 (downstream pipeline shape unchanged)

---

## Claude's Discretion

- React component structure
- SSE vs polling
- Font / color palette tactical choices
- Spinner / error boundary placement
- FastAPI route ordering

---

## Deferred Ideas

- Timeline animation (Phase 6, if time)
- Crossfade toggle transitions
- Sound cues
- In-chat citations linking to specific permits
