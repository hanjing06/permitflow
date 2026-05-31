# PermitFlow

> AI-assisted permit consolidation for the City of Toronto. Built for the NVIDIA hackathon. Runs entirely local on an ASUS Ascent GX10 (DGX Spark variant) — 123B reasoning model, embedder, and routing engine coexisting in 128 GB unified memory.

**Pitch:** Toronto issues ~30,000 utility-cut permits a year. The same blocks get torn up 3–6 times in 18 months because permits are issued in isolation. PermitFlow ingests the live Toronto Open Data feed, clusters spatially-and-temporally adjacent permits into single coordinated closures, and uses a 123B Nemotron-3 Super (Ollama, local) to explain each recommendation.

---

## Quick start

### Option A — on the GX10 itself

```bash
git clone <repo-url> permitflow
cd permitflow
nix run                       # backend :8000, frontend :5173
# open http://<gx10-host>:5173
```

The default `nix run` assumes Ollama (`:11434`), NIM embedder (`:8003`), and Valhalla (`:5000`) are already running on the same box. Without Nix:

```bash
pip install -r requirements.txt
( cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 ) &
( cd frontend && npm install && npm run dev -- --host 0.0.0.0 )
```

### Option B — laptop, with Ollama tunneled from the GX10

```bash
export PERMITFLOW_GX10=<gx10-host>     # ssh-reachable
nix run .#deploy-tunnel
# opens ssh -L 11434:localhost:11434 to the GX10, then runs backend+frontend locally
```

### Sub-apps

```bash
nix run .#backend     # FastAPI :8000 only
nix run .#frontend    # Vite dev :5173 only
```

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Reasoning LLM | **Nemotron-3 Super 123B** (Ollama, Q4_K_M) | Local, no cloud. ~88 GB resident. |
| Embedder | **NIM `nv-embedqa-e5-v5`** | Local RAG over the permit corpus. |
| Routing | **Valhalla** on Toronto OSM extract | Detour simulation for live `/whatif`. |
| Optimizer | Custom Python — two-pass anchor/piggyback + GEO_ID/street clustering + greedy conflict-deferred scheduler | `backend/optimizer.py` |
| Backend | FastAPI + DuckDB + pandas + scikit-learn | `backend/main.py` |
| Frontend | Vite + React + Leaflet | `frontend/` |
| Orchestration | Nix flake + bash | `flake.nix`, `scripts/gx10-up.sh` |

### Architecture

```
┌─ ASUS Ascent GX10 (DGX Spark, 128 GB unified) ────────────┐
│                                                           │
│  Ollama  · nemotron-3-super:latest (123B)   :11434  ~88GB │  chat + skill summaries
│  NIM     · nv-embedqa-e5-v5                  :8003  ~2GB  │  RAG retrieval
│  Valhalla · Toronto OSM extract              :5000  ~4GB  │  detour simulation
│                                                           │
│  FastAPI orchestrator                        :8000  ~10GB │  artifacts + SSE chat
│  ├── /metrics /clusters /naive /optimized                 │
│  ├── /hero-block /conflict-graph /whatif-street           │
│  └── /chat (SSE) — natural language + slash skills        │
└───────────────────────────────────────────────────────────┘
                          │  CORS *
                          ▼
        Vite + React + Leaflet UI   :5173
        ├── HeroMap   (naive ↔ optimized toggle)
        ├── TriStatCounter (tweened headline metrics)
        └── ChatPanel (SSE consumer + /help /whatif /clusters /permit)
```

Data flow (offline build, served from disk):

```
CKAN Toronto Open Data
   │
   ▼
backend/open_toronto.py     →  data/*.csv
   │
   ▼
backend/optimizer.py
   ├── load_canonical_permits   (5 schemas → one)
   ├── match_piggybacks         (250m / 35d tolerance)
   ├── cluster_leftover_candidates  (GEO_ID → street → temporal)
   ├── cluster_anchor_program   (review-only)
   ├── build_conflict_graph     (space-time proxy)
   └── build_optimized_timeline (greedy + 7-day deferral)
   │
   ▼
data/artifacts/{hero-block, clusters, conflict-graph,
                naive, optimized, permits.geojson, metrics}.json
   │
   ▼
FastAPI endpoints  ⇄  React UI / SSE chat
```

---

## Reproducing the demo

### 1. Bring up the NVIDIA services on the GX10

These run in long-lived containers with `--restart unless-stopped`:

```bash
# Ollama serving Nemotron-3 Super 123B
ollama serve &
ollama pull nemotron-3-super:latest

# NIM embedder
docker run -d --restart unless-stopped --gpus all \
  -p 8003:8000 nvcr.io/nim/nvidia/nv-embedqa-e5-v5:latest

# Valhalla (Toronto OSM extract pre-built into a volume)
docker run -d --restart unless-stopped \
  -p 5000:8002 -v valhalla_tiles:/custom_files \
  ghcr.io/gis-ops/docker-valhalla/valhalla:latest
```

Verify:

```bash
curl localhost:11434/api/tags     | jq '.models[].name'
curl localhost:8003/v1/models     | jq
curl -X POST localhost:5000/route -d '{"locations":[{"lat":43.66,"lon":-79.36},{"lat":43.67,"lon":-79.35}],"costing":"auto"}'
```

### 2. Pull the Toronto Open Data CSVs

```bash
python backend/open_toronto.py            # all tiers
# or: python backend/open_toronto.py anchors | candidates | context
```

### 3. Build artifacts (one-shot, ~30s)

```bash
cd backend && python -c "from optimizer import build_phase3_artifacts; build_phase3_artifacts()"
```

Writes `data/artifacts/{hero-block, clusters, conflict-graph, naive, optimized, permits.geojson, metrics}.json`. FastAPI lazy-builds on first hit if absent.

### 4. Launch the stack

```bash
nix run                # or scripts/gx10-up.sh
```

Open `http://<host>:5173`, toggle Naive ↔ Optimized, ask the chat panel a question.

### No API keys are required.

Everything is local. The only external service is Toronto's public CKAN endpoint, used once during ingest (no auth).

### Environment variables (all optional, sensible defaults)

```bash
# ---- service endpoints ----
OLLAMA_URL=http://localhost:11434/v1/chat/completions
OLLAMA_MODEL=nemotron-3-super:latest
NIM_EMBED_URL=http://localhost:8003/v1/embeddings
NIM_EMBED_MODEL=nv-embedqa-e5-v5
VALHALLA_URL=http://localhost:5000
RAG_TOP_K=5

# ---- optimizer tuning ----
PERMITFLOW_TODAY=2026-05-30                # "now" for scope filtering
PERMITFLOW_WINDOW_DAYS=90                  # forward planning horizon
PERMITFLOW_ANCHOR_MATCH_M=250              # piggyback spatial tolerance
PERMITFLOW_ANCHOR_MATCH_DAYS=35            # piggyback temporal tolerance
PERMITFLOW_EPS_M=220                       # DBSCAN epsilon (legacy path)
PERMITFLOW_TIME_M_PER_DAY=9                # time → meters weighting
PERMITFLOW_MIN_SAMPLES=2
PERMITFLOW_CONFLICT_M=500                  # conflict-graph spatial radius
PERMITFLOW_CONFLICT_THRESHOLD=0.15         # edge-prune threshold
PERMITFLOW_LANE_DAY_COST=15000             # placeholder, swap to TCMP
PERMITFLOW_MOBILIZATION_SAVINGS=5000
PERMITFLOW_STREET_WINDOW_DAYS=60           # same-street temporal bucket

# ---- deployment ----
PERMITFLOW_HOSTNAME=gx10-4896              # advertised in gx10-up.sh
PERMITFLOW_GX10=gx10-4896                  # ssh target for deploy-tunnel
VITE_API_URL=http://localhost:8000         # frontend → backend
```

A sample `.env` mirroring the defaults above is not strictly needed — every value falls back inside the code. Override only what you need.

---

## Datasets & provenance

All datasets are **public, real Toronto Open Data** (CKAN), pulled via `backend/open_toronto.py`. No synthetic data, no scraped content.

| File | Source dataset (CKAN package) | Role |
|---|---|---|
| `data/utility_cuts.csv` | `utility-cut-permits` | **Candidates** — short flexible permits |
| `data/building_permits.csv` | `building-permits-active-permits` | Candidates |
| `data/road_resurfacing.csv` | `road-resurfacing-program` | **Anchors** — fixed city windows |
| `data/road_reconstruction.csv` | `road-reconstruction-program` | Anchors |
| `data/sidewalk_construction.csv` | `sidewalk-construction-program` | Anchors |
| `data/road_restrictions.csv` | `road-restrictions` | Context (active closures overlay) |
| `data/open_toronto_permits.csv` | `road-reconstruction-program` (initial pull) | Bootstrap |

CKAN endpoint: `https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=<package>`
License: [Open Government Licence — Toronto](https://open.toronto.ca/open-data-license/).

Hero block: `Greektown corridor (Danforth, 43.6657 / -79.3642)`, ~1 km², selected by 100m-grid disruption-event count over 2023–2025 via DuckDB spatial join (`scripts/pick_hero_block.py`).

Headline counts produced from this data: **532 permits considered · 3 excavations avoided · $210K cost avoidance · 124 review-only coordination opportunities · 1228 conflict edges** (90-day forward window, `metrics.json`).

---

## Known limitations

1. **`utility_cuts.csv` has no inline lat/lon** — only `GEO_ID + DISPLAY_DESC`. Candidates without coordinates are silently dropped, so `piggybacks_accepted = 0` in the current demo data. Geocoding `DISPLAY_DESC` is the highest-leverage unblock.
2. **Conflict graph is a space-time proxy**, not a Valhalla `exclude_polygons` precompute. Intentional — keeps the demo runnable WiFi-off. The Valhalla client (`backend/valhalla.py`) is wired for live `/whatif-street` calls when the box is online.
3. **`$15,000 / lane-day` is a placeholder.** Replace with the Toronto Congestion Management Plan figure for a defensible dollar number.
4. **Anchor-program clusters (124 of them) are review-only** — we deliberately don't claim $ savings because we can't distinguish "already one coordinated city project" from "genuinely separate permits" with CKAN data alone.
5. **Street normalizer is ~90% correct.** Typos, abbreviations, and missing values exist in the raw data; we refuse to group permits whose normalized name is empty.
6. **Scope is one hero block (~1 km²)** for the demo. Citywide rollout requires re-running the optimizer on a larger window — pipeline already supports it via `PERMITFLOW_WINDOW_DAYS` / removing the hero-block filter.

---

## Next steps

- **Geocode `utility_cuts.DISPLAY_DESC`** to land real piggybacks → headline numbers jump from `3 avoided / $210K` into the high tens of millions citywide.
- **Wire Valhalla precompute** for the conflict graph (replace space-time proxy with real detour-volume deltas).
- **Layer-3 intersection clustering** — permits ~50 m apart on different streets at the same intersection (deferred from Phase 8).
- **Swap `$15K` placeholder for TCMP figure.**
- **Multi-block / citywide rollout** — current code is bounded by `filter_to_hero_block`; remove for a citywide pass.
- **City integration:** export coordinated schedules as CSV / iCal for permitting officers, with diff against the as-applied schedule.
- **Authentication + audit log** before any real city use.

---

## Repository layout

```
backend/
  main.py            FastAPI app — REST endpoints + SSE /chat
  optimizer.py       Two-pass clustering + scheduler + metrics
  llm.py             Ollama streaming + NIM RAG + skill router
  street_norm.py     Pure street-name normalizer
  valhalla.py        Routing client
  open_toronto.py    CKAN ingester
  tests/             Optimizer + normalizer tests
frontend/
  src/App.jsx        Toggle + tri-stat + map + chat
  src/components/    HeroMap, ChatPanel, ToggleSwitch, TriStatCounter
  src/lib/           Color scheme, count-up hook
data/
  *.csv              Raw CKAN pulls (gitignored except small samples)
  artifacts/         Precomputed JSON consumed by the UI
scripts/
  gx10-up.sh         Single-command bring-up
  pick_hero_block.py Hero-block selection (DuckDB spatial)
.planning/           GSD planning artifacts (PROJECT.md, ROADMAP.md, HEALTHCHECK.md)
flake.nix            Nix entrypoints: default | deploy-tunnel | backend | frontend
```
