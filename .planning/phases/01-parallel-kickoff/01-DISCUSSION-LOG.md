# Phase 1: Parallel Kickoff - Discussion Log

**Date:** 2026-05-30
**Mode:** Interactive (autonomous --interactive), batched
**Areas discussed:** 4 of 4 presented

---

## Area 1: Team composition & track ownership

**Options presented:**
- 4 people (per SPEC)
- 3 people (merge two tracks)
- 2 people (hard parallelism, cut camera flourish)
- Solo (drop OSRM conflict graph, canned-only chat)

**User selection:** 6 people + Claude Code w/ GSD

**Decisions captured:**
- D-01: Team is 6 humans + Claude Code (GSD)
- D-02: Track assignment ML pair / Data pair / OR solo / FE solo / Pitch lead floats
- D-03: Pitch lead must not own a Phase 1 track — owns the narrative from hour 0

---

## Area 2: NIM-vs-vLLM fallback trigger

**Options presented:**
- Hard container failure (recommended)
- Slow first inference (>10s)
- Either of the above
- Never fall back, stay on NIM

**User selection:** "dont know the difference but i think using as much 'nvidia stuff' as possible is good"

**Claude's interpretation:** NIM is NVIDIA's official inference container — using it maximizes NVIDIA branding for the pitch. vLLM is open-source serving. User wants the NVIDIA-stack pitch narrative, so lock NIM-first and only fall back on hard failure.

**Decisions captured:**
- D-04: NIM-first, no preemptive fallback
- D-05: Fall back to vLLM only on hard container failure (exit / OOM / fail to pull within 30 min). Slow inference alone is not a trigger.
- D-06: If fallback triggered, frame transparently on pitch slide

---

## Area 3: Hero block selection rule

**Options presented:**
- Widen window to 2020–2025 (recommended)
- Lower repeat threshold to ≥2
- Combine Utility Cuts + Building Permits
- Score by total lane-days, not repeat count

**User selection:** Combine Utility Cuts + Building Permits

**Decisions captured:**
- D-07: Combine Utility Cut Permits + Building Permits with site-disturbance filter
- D-08: Rank by total disruption events 2023–2025 per 100m segment
- D-09: If top candidate < 5 events, widen window to 2020–2025 before changing methodology

---

## Area 4: UI map stack

**Options presented:**
- Leaflet (per SPEC, recommended)
- MapLibre GL JS
- Mapbox GL JS (needs token)
- Decide in flight

**User selection:** "pick the easiest to mvp with"

**Claude's interpretation:** Leaflet — simplest API, no token, fastest scaffold.

**Decisions captured:**
- D-10: Leaflet locked. Do not revisit unless animation feels visibly weak after Phase 4.

---

## Claude's Discretion (no user input)

- DuckDB spatial extension version
- OSRM profile flags
- Leaflet plugin choices
- FastAPI project layout
- docker-compose structure for the NIM stack

---

## Deferred Ideas

- Mapbox / MapLibre swap (Phase 6 polish, if needed)
- Multi-city generalization (post-hackathon)
- Real-time permit queue / contractor portal (post-hackathon)
