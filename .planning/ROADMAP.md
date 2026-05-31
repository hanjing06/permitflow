# Roadmap: PermitFlow

## Overview

PermitFlow is a 36-hour NVIDIA hackathon build: an AI-assisted permit consolidation system for the City of Toronto, running Nemotron-3 Super 123B locally on an ASUS Ascent GX10 via Ollama. The seven phases below are time-boxed to the hackathon clock — Phase N covers Hour X–Y. Phase 1 stands up infrastructure in parallel (Ollama, Valhalla, data, UI). **Phase 2 is closed (D-77)** — no LoRA fine-tune; the 123B local model is the anchor instead. Phase 3 builds the geospatial optimizer (DBSCAN trench-sharing clusters + Valhalla-driven conflict graph — D-79). Phase 4 wires the UI and chat panel. **Phase 5 is reduced (D-78)** to verification + screenshot capture. Phase 6 polishes the demo arc. Phase 7 rehearses and records a backup video. Three hard gates: G1 (infra alive @ h4), G2 (end-to-end skeleton @ h22), G3 (offline demo @ h34).

> **Reality-check (2026-05-31):** ROADMAP success criteria below reflect the current stack — Ollama (not NIM Nano/Super), Valhalla (not OSRM), no fine-tune. See `.planning/HEALTHCHECK.md` for the per-phase implementation delta. Decisions D-75 / D-76 / D-77 / D-78 / D-79 in STATE.md drive the changes.

## Phases

**Phase Numbering:**
- Integer phases (1–7): The seven hour-block phases
- Decimal phases would be urgent insertions if needed during the hackathon

- [x] **Phase 1: Parallel Kickoff** — Stand up Ollama (123B), Valhalla, NIM embedder, data ingestion, UI scaffold; pick hero block (Hour 0–4) ✅ all 5 G1 criteria satisfied 2026-05-30
- [x] ~~**Phase 2: Fine-tune Kickoff**~~ — **CLOSED (D-77).** No fine-tune; 123B local is the anchor. Phase 5 D-44 fallback narrative replaces it.
- [x] **Phase 3: Optimizer Build** — DBSCAN trench-sharing (anchor + piggyback per D-79) + space-time-proxy conflict graph + naive/optimized timelines (Hour 6–14) ✅ merged hanjing06/c6100d0 + wired endpoints in 27ac93b 2026-05-31. Demo: 532 considered / 2 merges / 3 excavations avoided / $210K.
- [x] **Phase 4: UI & Chat Panel** — Leaflet hero-block view, naive↔optimized toggle, tri-stat counter, streaming Nemotron Super chat (Hour 14–22) (completed 2026-05-31)
- [ ] **Phase 5: Verification & Pitch Artifacts** — REDUCED per D-78: nvidia-smi (123B resident) screenshot + live chat latency screenshot. No fine-tune eval. (Hour 22–24)
- [ ] **Phase 6: Demo Polish** — Lock 90-second arc, deck, cost-avoidance figure, camera flourish (Hour 28–34)
- [ ] **Phase 7: Dry Runs & Backup** — Three rehearsals, WiFi-off test, backup video, contingency cards (Hour 34–36)

## Phase Details

### Phase 1: Parallel Kickoff
**Goal**: Stand up every external dependency (Ollama serving Nemotron-3 Super 123B on GX10 — D-76; NIM embedder; Valhalla with Toronto OSM tiles — D-75; Toronto Open Data ingestion into DuckDB; Leaflet UI shell) and lock the hero neighbourhood so every later phase has concrete inputs.
**Depends on**: Nothing (first phase)
**Window**: Hour 0–4
**Success Criteria** (what must be TRUE):
  1. `curl localhost:11434/api/tags` (on GX10) lists `nemotron-3-super:latest`
  2. `curl localhost:8003/v1/models` returns NIM `nv-embedqa-e5-v5`
  3. `curl localhost:5000/route ...` (Valhalla) returns a valid route for two coords inside the hero block
  4. `hero-block.json` exists with the chosen neighbourhood bbox
  5. Leaflet UI renders the hero block with permits from the CKAN feed
**Plans**: TBD (CONTEXT, SPEC, infra largely landed — see HEALTHCHECK.md)

Plans:
- [x] 01-01: Ollama (123B) + NIM embedder on GX10 ✅ standing
- [x] 01-02: Toronto Open Data ingestion (CKAN multi-dataset) + hero block selection ✅ datasets ✅, hero ✅ (segment-43666-79364, Danforth/Greektown, 5 events 2023-2025)
- [x] 01-03: Valhalla stack on Toronto OSM extract ✅
- [x] 01-04: Vite + React + Leaflet UI scaffold ✅

### Phase 2: Fine-tune Kickoff — ⏭ CLOSED (D-77)

**Status:** Closed. No work.
**Decision:** D-77 — skip the LoRA fine-tune entirely. The Nemotron-3 Super 123B running locally on the GX10 (D-76) replaces the planned tuned-Nano-9B story as the demo's "wow" anchor. Phase 5's D-44 fallback narrative ("123B reasoning model on local hardware, no cloud") becomes the pitch line that the fine-tune was originally meant to enable.
**Nothing to plan. Nothing to build.**

### Phase 3: Optimizer Build
**Goal**: Produce the two timelines (naive vs optimized) and the conflict graph that drive the demo. **Trench-sharing two-pass per D-79**: utility-cut-permits are *candidates*, road-reconstruction / resurfacing / sidewalk programs are *anchor windows*. DBSCAN clusters candidates spatially+temporally against anchors, then a Valhalla `exclude_polygons` pass simulates concurrent closures for the conflict graph.
**Depends on**: Phase 1
**Window**: Hour 6–14
**Success Criteria** (what must be TRUE):
  1. `clusters.json` (or equivalent) identifies ≥ 5 anchor↔candidate trench-sharing matches in the hero neighbourhood
  2. `conflict-graph.json` exists with non-zero edges from Valhalla detour simulation, weighted by traffic volume
  3. `naive.json` and `optimized.json` differ visibly when overlaid on the map
  4. Headline metrics computed and persisted to `metrics.json`: redundant excavations avoided + lane-days saved + estimated cost avoidance (per D-53, not magic $15K)
  5. FastAPI `/whatif?street=X&date=Y` endpoint calls Valhalla and responds with detour-volume delta (not the current hardcoded delay-week stub)
**Plans**: TBD — biggest remaining gap per HEALTHCHECK

Plans:
- [ ] 03-01: Future-window data prep — anchor + candidate tables (D-20/D-22, D-07 building filter)
- [ ] 03-02: Trench-sharing two-pass — anchor<->candidate match + leftover-cluster DBSCAN (D-79, D-28/D-29) -> clusters.json + SCHEMAS.md
- [ ] 03-03: Valhalla conflict graph — exclude_polygons precompute -> conflict-graph.json
- [ ] 03-04: Greedy interval scheduler -> naive.json + optimized.json + durable metrics.json
- [ ] 03-05: API surface — real /whatif (Valhalla) + /metrics from disk + /clusters,/naive,/optimized,/conflict-graph for Phase 4

### Phase 4: UI & Chat Panel
**Goal**: Wire the optimizer outputs and Nemotron-3 Super 123B chat (over Ollama) into a single screen that tells the demo story. Even with placeholder chat content, the map alone should communicate the project.
**Depends on**: Phase 3
**Window**: Hour 14–22
**Success Criteria** (what must be TRUE):
  1. Map auto-centres on hero block at appropriate zoom (D-55)
  2. Naive ↔ Optimized toggle works and tri-stat counter updates live (D-32, D-33)
  3. Chat panel returns a streamed Ollama response for at least one live question (D-41 — SSE, not batch)
  4. RAG retrieval uses the NIM embedder for context assembly (D-39/D-40/D-41) — or fall back to "all permits in this neighbourhood" per cut-list
  5. All three canned scenarios run end-to-end with cached responses by hour 30 (D-37)
  6. The full 90-second demo loop is executable end-to-end
**Plans:** 2/2 plans complete

Plans:
- [x] 04-01-PLAN.md — Backend: POST /chat (SSE Ollama stream) + POST /retrieve (NIM embedder → top-5) + RAG helpers in llm.py
- [x] 04-02-PLAN.md — Frontend rewrite: HeroMap (auto-centre via /hero-block) + ToggleSwitch (naive↔optimized hard cut) + TriStatCounter (3 equal metrics, 2s tween) + ChatPanel (SSE consumer + 3 canned scenarios)

### Phase 5: Verification & Pitch Artifacts — REDUCED (D-78)
**Goal**: Capture proof that the 123B Nemotron-3 Super is genuinely resident and serving on the GX10. No fine-tune to eval (Phase 2 closed per D-77); the artifacts feed the pitch slide directly.
**Depends on**: Phase 1, Phase 4
**Window**: Hour 22–24 (compressed from original 22–28)
**Success Criteria** (what must be TRUE):
  1. `ollama-modelfile.txt` snapshot captured (✅ done in Phase 1)
  2. `nvidia-smi` screenshot showing the 123B model resident in GPU memory
  3. One live chat round-trip latency screenshot from the demo path
**Plans**: TBD

Plans:
- [ ] 05-01: Capture `nvidia-smi` while a live chat call is in flight
- [ ] 05-02: Capture chat-latency screenshot + add to pitch deck assets

### Phase 6: Demo Polish
**Goal**: Convert a working system into a 90-second presentation that wins. No new features — only existing ones getting sharper, faster, and legible to a first-time viewer.
**Depends on**: Phase 5
**Window**: Hour 28–34
**Success Criteria** (what must be TRUE):
  1. The full 90-second arc runs cleanly end-to-end with WiFi off
  2. All canned chat scenarios return cached responses within 1.5 seconds
  3. Pitch script is timed to ≤ 90 seconds
  4. Three-slide deck is finished and rehearsed
  5. No unfixed UI jank in the recorded demo path
**Plans**: TBD

Plans:
- [ ] 06-01: UI polish pass (hero centring, polygon styling, counter animation)
- [ ] 06-02: Three-slide deck + pitch script + cost-avoidance figure
- [ ] 06-03: Live traffic camera flourish (with offline fallback)

### Phase 7: Dry Runs & Backup
**Goal**: Make the demo bulletproof. Three full run-throughs, an offline test, a recorded backup video, and a contingency for every plausible failure. No code changes after hour 35.
**Depends on**: Phase 6
**Window**: Hour 34–36
**Success Criteria** (what must be TRUE):
  1. Three successful dry runs completed under 100 seconds each
  2. Backup video exists in two locations (laptop + USB stick)
  3. WiFi-off run passes
  4. Contingency cards reviewed and within reach of pitch person
  5. No commits to repo after hour 35
**Plans**: TBD

Plans:
- [ ] 07-01: Three live dry runs + glitch triage
- [ ] 07-02: Offline test (WiFi off) + offline asset bundling
- [ ] 07-03: Backup video recording + duplication
- [ ] 07-04: Contingency cards + final checklist

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Parallel Kickoff | 4/4 (infra ✅, data ✅, hero ✅) | Complete | 2026-05-30 |
| 2. ~~Fine-tune Kickoff~~ | n/a | ⏭ Closed (D-77) | 2026-05-30 |
| 3. Optimizer Build | 0/5 | In progress (single-pass DBSCAN only; Valhalla not wired) | - |
| 4. UI & Chat Panel | 2/2 | Complete   | 2026-05-31 |
| 5. Verification & Pitch Artifacts | 1/2 (modelfile ✅; nvidia-smi + latency ❌) | In progress | - |
| 6. Demo Polish | 0/3 | Not started | - |
| 7. Dry Runs & Backup | 0/4 | Not started | - |

See `.planning/HEALTHCHECK.md` for the per-item gap analysis.
