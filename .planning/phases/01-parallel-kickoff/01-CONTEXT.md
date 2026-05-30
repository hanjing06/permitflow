# Phase 1: Parallel Kickoff - Context

**Gathered:** 2026-05-30
**Status:** Infra largely landed (see HEALTHCHECK.md for delta)

> ⚠ **Reality-check (2026-05-31):** the stack swapped during execution.
> - **Inference: NIM → Ollama** (D-76, body §"Inference Engine Swap"). All Nemotron serving is `ollama nemotron-3-super:latest` (123B) on `:11434`. NIM Nano/Super containers are not used; only the NIM embedder (`nv-embedqa-e5-v5` on `:8003`) survives.
> - **Routing: OSRM → Valhalla** (D-75, body §"Routing Engine Swap"). OSRM was arm64-incompatible. Valhalla on `:5000` (gisops Docker image, Toronto OSM tiles).
> - Ignore Track A's NIM-Nano / NIM-Super language and Track C's OSRM language in the §Tracks section below — those are superseded.

<domain>
## Phase Boundary

Stand up every external dependency on the GX10 (Nemotron NIM endpoints for Nano + Super + embedder, OSRM with Toronto OSM, Toronto Open Data ingestion into DuckDB, Leaflet UI shell) and lock the hero neighbourhood. Four hours, parallel tracks. Exit when all five G1 success criteria from `01-SPEC.md` are true.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**5 success criteria are locked.** See `01-SPEC.md` for full tasks, exit criteria, risks, and deliverables.

Downstream agents MUST read `01-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Track A — Nemotron Nano + Super + embedder NIM containers on GX10
- Track B — Toronto Open Data ingestion + DuckDB load + hero block selection
- Track C — OSRM Docker on Toronto OSM extract, edge-closure simulation smoke test
- Track D — Vite + React + Leaflet scaffold, scrubber and toggle shells

**Out of scope:**
- Real permit data wiring (Phase 3 owns the optimizer outputs)
- Live LLM chat in UI (Phase 4 owns this)
- Fine-tuning (Phase 2 owns this)

</spec_lock>

<decisions>
## Implementation Decisions

### Team & Track Ownership
- **D-01:** Team is **6 humans + Claude Code (GSD orchestration)**. Larger than SPEC's assumed 4 — every track gets an owner plus a buddy.
- **D-02:** Track assignment for Phase 1:
  - **ML pair** — Track A (NIM serving) + sets up Phase 2 training infra in the background
  - **Data pair** — Track B (ingestion + hero block selection)
  - **OR** — Track C (Valhalla routing stack — see D-75) — single owner since this is mostly a Docker-config task
  - **FE** — Track D (Leaflet scaffold)
  - **Pitch lead** — floats during Phase 1; starts the deck and script from hour 12 onward (does not own a Phase 1 track)
- **D-03:** Pitch lead must NOT take a Phase 1 implementation track. Their job from hour 0 is "watch the build, draft the narrative." Hackathon-winning move.

### NIM vs vLLM Fallback
- **D-04:** **NIM-first, no preemptive fallback.** NIM (NVIDIA Inference Microservice) is NVIDIA's official inference container — using it maximizes the "all NVIDIA stack" pitch narrative, which is the framing the user wants.
- **D-05:** Fallback to vLLM is **only on hard container failure**: NIM exits, OOMs, or fails to pull within 30 minutes on the GX10. Slow inference alone is NOT a trigger — debug in place.
- **D-06:** If fallback is triggered, frame it on the pitch slide as "NIM is the production path; vLLM was used at the hackathon for X reason." Don't pretend it didn't happen.

### Hero Block Selection
- **D-07:** Combine **Utility Cut Permits + Building Permits (Active + Cleared)** datasets. Building permits don't all disrupt the street, so filter to those with site-disturbance signals (permit type ∈ {new construction, major renovation, demolition} OR explicit street-occupation flag).
- **D-08:** Rank candidates by **total disruption events 2023–2025 per 100m segment** (any year, any utility, any permit type). Pick the top segment's enclosing 1 km² as the hero block.
- **D-09:** If the top candidate has < 5 disruption events, widen the window to 2020–2025 before changing methodology. The "≥3 repeats" framing from SPEC stays as a narrative target, not a hard filter.

### Map Stack
- **D-10:** **Leaflet** (per SPEC). Fastest path to MVP, no token required, polygon animation is good enough for the demo's needs. Lock this decision — do not revisit unless animation feels visibly weak after Phase 4.

### Inference Engine Swap — NIM → Ollama (mid-execution amendment, 2026-05-30)
- **D-76:** **Inference backend switched from NIM to Ollama** for all Nemotron serving.
  - **Why:**
    - **Nano NIM (`nvcr.io/nim/nvidia/nvidia-nemotron-nano-9b-v2:latest`)** has a botched build — manifest claims `arm64 linux` but the binaries inside (`bash`, entrypoint) are amd64. `exec format error` on every entrypoint.
    - **Super NIM (`llama-3.3-nemotron-super-49b-v1:latest`)** starts on arm64 but the NIM profile selector finds no runnable profile for GB10 (Grace Blackwell). NVIDIA hasn't shipped a GB10 profile for this model yet. Hard fail per Phase 1 D-05.
    - Discovered an **Ollama server already running on `:11434`** with four models pre-loaded — including **`nemotron-3-super:latest`** (123.6B, Q4_K_M, MoE — `nemotron_h_moe` family). Local, immediate, no download.
  - **Architecture change:**
    - Chat **and** normalization both route to Ollama `:11434/v1/chat/completions` with `model: nemotron-3-super:latest`. One model, always hot, no Ollama model-swap latency.
    - Embedder stays on NIM `:8003` (NIM embedder works fine on arm64).
    - Port contract changes: backend env var `CHAT_URL=http://localhost:11434` and `NORMALIZER_URL=http://localhost:11434`. No nginx proxy — direct connect, simpler under demo pressure.
  - **Upgrade vs original plan:** 123B Q4 > 49B FP8 in raw scale. The pitch headline becomes *"123 billion parameter Nemotron-3 Super running locally on this box, no internet"* — strictly better than the original "49B local" narrative.
  - **Risk owned:** the Ollama install belongs to another user (`frost`) on the shared box. If they restart Ollama or remove the model mid-event, we're stuck. **Mitigation:** snapshot the model file (`ollama show nemotron-3-super:latest --modelfile`) at Phase 1 close so we can re-pull in an emergency. Document in Phase 7 contingency cards.

### Routing Engine Swap — OSRM → Valhalla (mid-execution amendment, 2026-05-30)
- **D-75:** **Routing engine switched from OSRM to Valhalla** for the conflict-graph and `/whatif` simulation.
  - **Why:** Project-OSRM's official Docker image (`ghcr.io/project-osrm/osrm-backend`) is amd64-only. The GX10's Grace Blackwell GB10 is arm64. Build-from-source was blocked by the workstation's external-source policy. Valhalla (gisops community Docker image `ghcr.io/gis-ops/docker-valhalla/valhalla`) ships native arm64 multi-arch images and is feature-equivalent for our needs.
  - **API shape change:** Valhalla uses `POST /route` with a JSON body (not OSRM's GET URL params). Edge-closure simulation uses `exclude_polygons` (polygon over the closed segment) or `exclude_locations` (point nodes), not OSRM's edge-blocking. Phase 3 SPEC and CONTEXT updated to match.
  - **Port contract preserved:** Valhalla container listens on 8002 internally; mapped to host `:5000` so all downstream phases (4, 5, 6, 7) and PROJECT.md's architecture box continue to reference `:5000`. No cascading port change.
  - **OR person's task adjustment:** Phase 1 Track C is now a single `docker run` of the gisops image with `tile_files=Toronto.osm.pbf` + `build_tiles=True` env vars. Simpler than the OSRM extract/partition/customize chain — Valhalla bundles tile build into one container start.

### Claude's Discretion
- DuckDB spatial extension version, Valhalla config tuning (tile cache size, isolation timeout), Leaflet plugin choices, FastAPI project layout, docker-compose structure for the NIM stack — all at implementation-time discretion. SPEC sets the contract; tactics are open.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level
- `.planning/PROJECT.md` — System architecture, GX10 memory budget, success criteria, cut-list
- `.planning/ROADMAP.md` — Phase ordering, dependencies, gate checks (G1 at end of this phase)
- `.planning/STATE.md` — Current position, recent decisions

### Phase 1
- `.planning/phases/01-parallel-kickoff/01-SPEC.md` — **Locked requirements.** Tasks, exit criteria, risks, deliverables. Read first.

### Data sources (Toronto Open Data, CKAN)
- Utility Cut Permits — `https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=utility-cut-permits`
- Road Restrictions v3 — `https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=road-restrictions`
- Building Permits Active + Cleared — search CKAN: `q=building+permit`
- Traffic Volumes — Midblock — `q=traffic+volume`
- One Way Streets — `q=one+way+streets`

### External docs (consult during implementation)
- NIM container catalog — `build.nvidia.com/models` (filter for Nemotron family)
- OSRM backend docs — `project-osrm.org/docs/v5.5.1/api/`
- Toronto OSM extract — `download.bbbike.org/osm/bbbike/Toronto/` (smaller than Geofabrik GTA)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield repo. Working dir is `/home/shmul95/Repositories/nvidia/` with only `.planning/` populated.

### Established Patterns
- `.planning/` is a symlink into the personal vault at `~/shmulsidian/02_Projects/PermitFlow/GSD`. Content commits land in the vault; the repo only tracks the symlink.
- Nix shell is the dependency provider on this machine — no global Python/Node/jq. Use `nix-shell -p` for one-off tools, or write a `shell.nix` / `flake.nix` for the repo if the stack stabilizes.

### Integration Points
- GX10 is reachable from the laptop over the local network. NIM endpoints must be exposed (or tunneled) so the FastAPI backend on the GX10 can call them and the laptop UI can hit the backend. Assume same-LAN for the hackathon.

</code_context>

<specifics>
## Specific Ideas

- User explicitly framed the project around "using as much NVIDIA stuff as possible." NIM is the canonical NVIDIA inference path — prefer it everywhere it works. This is a pitch-narrative constraint, not just an engineering choice.
- "Easiest to MVP with" was the user's lock criterion for the map stack — apply the same standard to other Phase 1 tactical choices: prefer the well-trodden path, leave optimization for Phase 6 polish.

</specifics>

<deferred>
## Deferred Ideas

- **Mapbox / MapLibre swap** — if Leaflet animation feels weak after Phase 4, revisit in Phase 6 polish. Don't act on it during Phase 1.
- **Multi-city generalization** (Montréal, Vancouver) — noted in PROJECT.md as post-hackathon scope. Not in Phase 1.
- **Real-time permit queue / contractor portal** — productionization. Post-hackathon.

</deferred>

---

*Phase: 1-Parallel Kickoff*
*Context gathered: 2026-05-30*
