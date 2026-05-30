# Roadmap: PermitFlow

## Overview

PermitFlow is a 36-hour NVIDIA hackathon build: an AI-assisted permit consolidation system for the City of Toronto, running Nemotron locally on an ASUS Ascent GX10. The seven phases below are time-boxed to the hackathon clock — Phase N covers Hour X–Y. Phase 1 stands up infrastructure in parallel. Phase 2 kicks off a LoRA fine-tune that runs in the background through Phases 3 and 4. Phase 3 builds the geospatial optimizer (DBSCAN clustering + OSRM-driven conflict graph). Phase 4 wires the UI and chat panel. Phase 5 evaluates the trained model and swaps it into the pipeline. Phase 6 polishes the demo arc. Phase 7 rehearses and records a backup video. Three hard gates: G1 (infra alive @ h4), G2 (end-to-end skeleton @ h22), G3 (offline demo @ h34).

## Phases

**Phase Numbering:**
- Integer phases (1–7): The seven hour-block phases
- Decimal phases would be urgent insertions if needed during the hackathon

- [ ] **Phase 1: Parallel Kickoff** — Stand up NIM, OSRM, data ingestion, UI scaffold; pick hero block (Hour 0–4)
- [ ] **Phase 2: Fine-tune Kickoff** — Launch LoRA training on Nemotron Nano in background (Hour 4–6)
- [ ] **Phase 3: Optimizer Build** — DBSCAN clusters + OSRM conflict graph + naive/optimized timelines (Hour 6–14)
- [ ] **Phase 4: UI & Chat Panel** — Leaflet scrubber, savings counter, Nemotron Super chat (Hour 14–22)
- [ ] **Phase 5: Fine-tune Eval & Swap** — Eval tuned Nano vs raw, swap into pipeline, capture pitch artifacts (Hour 22–28)
- [ ] **Phase 6: Demo Polish** — Lock 90-second arc, deck, cost-avoidance figure, camera flourish (Hour 28–34)
- [ ] **Phase 7: Dry Runs & Backup** — Three rehearsals, WiFi-off test, backup video, contingency cards (Hour 34–36)

## Phase Details

### Phase 1: Parallel Kickoff
**Goal**: Stand up every external dependency (Nemotron NIM endpoints on GX10, OSRM with Toronto OSM, data ingestion into DuckDB, Leaflet UI shell) and lock the hero neighbourhood so every later phase has concrete inputs.
**Depends on**: Nothing (first phase)
**Window**: Hour 0–4
**Success Criteria** (what must be TRUE):
  1. `curl localhost:8001/v1/models` returns Nemotron Nano on the GX10
  2. `curl localhost:8002/v1/models` returns Nemotron Super on the GX10
  3. `osrm-routed` returns a valid route for two coordinates inside the hero block
  4. `hero-block.json` exists with the chosen neighbourhood bbox
  5. Leaflet UI renders the hero block with two placeholder polygons
**Plans**: TBD

Plans:
- [ ] 01-01: NIM serving for Nemotron Nano, Super, and embedder on GX10
- [ ] 01-02: Toronto Open Data ingestion + hero block selection
- [ ] 01-03: OSRM stack on Toronto OSM extract
- [ ] 01-04: Leaflet + timeline scrubber UI scaffold

### Phase 2: Fine-tune Kickoff
**Goal**: Launch a LoRA fine-tune of Nemotron Nano 9B that normalizes Toronto utility-cut permit free-text into a canonical JSON schema. Training runs unattended through Phases 3 and 4.
**Depends on**: Phase 1
**Window**: Hour 4–6
**Success Criteria** (what must be TRUE):
  1. Training process is running on GX10 (GPU util > 0)
  2. Loss has decreased measurably from step 0 to step ~100
  3. Held-out eval set exists at `~/permitflow/data/eval-100.jsonl` and is untouched
**Plans**: TBD

Plans:
- [ ] 02-01: Label 200 permits + synthesize 600 via Nemotron Super
- [ ] 02-02: LoRA training launch (Nano 9B, r=16, 3 epochs, detached)

### Phase 3: Optimizer Build
**Goal**: Produce the two timelines (naive vs optimized) and the conflict graph that drive the demo. DBSCAN clustering for space-time merge candidates; OSRM-driven detour simulation for the conflict graph.
**Depends on**: Phase 1
**Window**: Hour 6–14
**Success Criteria** (what must be TRUE):
  1. `clusters.json` exists with at least 5 multi-permit clusters in the hero neighbourhood
  2. `conflict-graph.json` exists with non-zero edges weighted by traffic volume
  3. `naive.json` and `optimized.json` differ visibly when overlaid on the map
  4. Headline metrics computed: redundant excavations avoided + lane-days saved
  5. FastAPI `/whatif?street=X&date=Y` endpoint responds with conflict assessment
**Plans**: TBD

Plans:
- [ ] 03-01: DBSCAN clustering + merge savings computation
- [ ] 03-02: OSRM conflict graph (closure simulation + volume weighting)
- [ ] 03-03: Greedy interval scheduler + `/whatif` API

### Phase 4: UI & Chat Panel
**Goal**: Wire the optimizer outputs and Nemotron Super chat into a single screen that tells the demo story. Even with placeholder chat content, the map alone should communicate the project.
**Depends on**: Phase 3
**Window**: Hour 14–22
**Success Criteria** (what must be TRUE):
  1. Timeline scrubber plays through the historical window, polygons animate correctly
  2. Naive ↔ Optimized toggle works and savings counter updates live
  3. Chat panel returns a streamed Nemotron Super response for at least one live question
  4. All three canned scenarios run end-to-end with cached responses
  5. The full 90-second demo loop is executable end-to-end
**Plans**: TBD

Plans:
- [ ] 04-01: Leaflet map + timeline scrubber + savings counter
- [ ] 04-02: Naive↔Optimized toggle + crossfade
- [ ] 04-03: Chat panel + Nemotron Super streaming + RAG context assembly
- [ ] 04-04: Traffic camera hover flourish

### Phase 5: Fine-tune Eval & Swap
**Goal**: Turn the LoRA checkpoint from Phase 2 into a quantifiable win and a live demo upgrade. Produce a real before/after lift number for the pitch slide and swap the tuned model into the live ingestion pipeline.
**Depends on**: Phase 2, Phase 4
**Window**: Hour 22–28
**Success Criteria** (what must be TRUE):
  1. `eval-report.json` exists with concrete per-field accuracy numbers
  2. Tuned Nano shows ≥ +15 points (≥ +20 ideal) on overall schema-correct rate vs raw Nano
  3. Tuned Nano is the model running in the NIM container during the demo
  4. Hero-neighbourhood data has been re-normalized with the tuned model
  5. Pitch artifacts saved: loss curve, 3 side-by-side examples, headline number
**Plans**: TBD

Plans:
- [ ] 05-01: Eval tuned vs raw Nano on held-out 100
- [ ] 05-02: Swap tuned adapter into NIM, re-ingest hero data
- [ ] 05-03: Capture pitch artifacts (loss curve, examples, nvidia-smi screenshot)

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
| 1. Parallel Kickoff | 0/4 | Not started | - |
| 2. Fine-tune Kickoff | 0/2 | Not started | - |
| 3. Optimizer Build | 0/3 | Not started | - |
| 4. UI & Chat Panel | 0/4 | Not started | - |
| 5. Fine-tune Eval & Swap | 0/3 | Not started | - |
| 6. Demo Polish | 0/3 | Not started | - |
| 7. Dry Runs & Backup | 0/4 | Not started | - |
