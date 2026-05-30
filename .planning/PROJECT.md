# PermitFlow

> AI-assisted permit consolidation for the City of Toronto. Built for the NVIDIA hackathon, runs on ASUS Ascent GX10.

## One-line pitch

Toronto issues ~30,000 utility cut permits a year. The same blocks get torn up 3–6 times in 18 months because permits are issued in isolation. PermitFlow clusters spatially-and-temporally adjacent permits into single coordinated closures, and uses traffic-flow simulation to decide which permits can be issued in parallel without compounding congestion — explained by a Nemotron model fine-tuned on Toronto permit data, running locally on the GX10.

## Who it's for

**Primary user:** City of Toronto — Transportation Services / Toronto Water / Engineering & Construction Services teams that issue and coordinate right-of-way permits.

**Hackathon judges:** want to see (1) a working geospatial pipeline, (2) Nemotron doing real reasoning on local hardware, (3) a visceral before/after that communicates the problem in 30 seconds.

## Core idea

Two simultaneous optimizations on top of the live permit feed:

1. **Space-time clustering** — group permits that touch the same block in overlapping windows so the road is opened once, not five times.
2. **Traffic-conflict-aware scheduling** — simulate edge closures on Toronto's road graph (Valhalla on OSM); allow concurrent permits only when their detour paths don't compound on the same arterial.

Nemotron is the *spokesperson and normalizer*, not the optimizer:
- A LoRA-tuned **Nemotron Nano 9B** normalizes messy permit free-text into a canonical schema.
- **Nemotron Super 49B** generates human-readable consolidation proposals and answers "what if I close X next week" in a chat panel.

## Data sources (Toronto Open Data, CKAN)

| Dataset | Role |
|---|---|
| Utility Cut Permits | Hero dataset — the "tear up the road" permits being clustered |
| Road Restrictions (v3) | Currently-active closures, validation overlay |
| Traffic Volumes — Midblock | Weights detour impact by actual measured flow |
| One Way Streets | Routing graph correctness |
| Traffic Cameras | Demo overlay flourish |
| Building Permits — Active | Optional, expands "things that block sidewalk" |

## Hardware

ASUS Ascent GX10 (DGX Spark variant). 128 GB unified memory, FP4-native. **Non-negotiable: all Nemotron inference and the LoRA fine-tune run on this box.** The hackathon laptop is a thin client; the GX10 is the product.

### Memory budget

| Service | Approx footprint |
|---|---|
| Ollama: nemotron-3-super 123B Q4_K_M | ~88 GB |
| NIM: nv-embedqa-e5-v5 | ~2 GB |
| Valhalla + OSM Toronto extract | ~4 GB |
| FastAPI + DuckDB + headroom | ~10 GB |
| **Total** | **~104 GB / 128 GB** |

See Phase 1 CONTEXT D-76 and Phase 2 CONTEXT D-77 for the Ollama swap and fine-tune skip. The 24 GB of headroom is tighter than the original NIM plan but the 123B reasoning model is a substantial upgrade over the planned Super 49B.

Verify in Phase 1 with `nvidia-smi`.

## Architecture

```
┌─ ASUS Ascent GX10 ────────────────────────────────────┐
│                                                       │
│  Ollama: nemotron-3-super:latest (123B) :11434        │  ← chat + normalization
│  NIM: nv-embedqa-e5-v5                  :8003         │  ← RAG retrieval
│                                                       │
│  Valhalla (Toronto OSM extract)        :5000          │  ← detour simulation
│  DuckDB + permits.geojson                             │  ← data layer
│  FastAPI orchestrator                  :8080          │  ← demo backend
└───────────────────────────────────────────────────────┘
                          │
                          ▼
              Leaflet UI on laptop (demo)
```

## Hackathon constraints

- **Time:** ~36 hours.
- **Scope:** one Toronto neighbourhood, ~1–2 km². Chosen in Phase 1 as the block with the most repeat excavations in 2023–2025.
- **Demo arc (90 seconds):**
  1. Time-lapse on the hero block — 6 separate red closures over 18 months.
  2. Toggle to optimized — same block, 2 consolidated closures. Counter ticks: "11 redundant excavations avoided · 38 lane-days saved."
  3. Chat panel: judge asks "what if I issue a watermain permit on Harbord next week?" — Nemotron answers with traffic-impact reasoning and a deferral / batching recommendation.
- **Wow lever:** the model talking to the judge is running locally on the GX10 and was fine-tuned on Toronto permits last night.

## Success criteria

| # | Criterion | Measured by |
|---|---|---|
| 1 | Reasoning + embedder both serving on GX10 | curl returns 200 from Ollama `:11434/v1/models` (lists nemotron-3-super) AND NIM embedder `:8003/v1/models` |
| 2 | ~~LoRA fine-tune lift~~ — **superseded by D-77 (skip fine-tune).** New pitch anchor: "**123B Nemotron-3 Super running locally**" on this box, no internet. |
| 3 | Optimizer produces non-trivial savings | hero block: ≥ 5 redundant excavations identified across the historical window |
| 4 | Conflict simulator working | toggling closures in UI shows Valhalla-driven detour volume deltas |
| 5 | End-to-end demo runs offline | full 90-second arc completes with WiFi disabled |
| 6 | Backup video exists | recorded by hour 35 |

## Roadmap

See [ROADMAP.md](./ROADMAP.md). Seven phases mapped to the 36-hour budget.

## Risks & cut-list

If running behind, cut in this order:

1. **Cut embedding/RAG.** Hard-code chat context to "all permits in this neighbourhood." Saves ~4h.
2. **Cut fine-tune.** Fall back to raw Nemotron Nano. Saves ~4h, costs the "trained on GX10 overnight" slide.
3. **Cut interactive chat.** Pre-record canned scenarios as in-UI video. Saves ~6h, costs interactivity.

**Never cut:** local Nemotron serving on GX10 · before/after time-lapse on hero block · savings counter.
