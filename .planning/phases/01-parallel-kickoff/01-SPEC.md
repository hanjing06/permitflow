# Phase 1 — Parallel Kickoff

**Window:** Hour 0–4
**Owners:** All (4 parallel tracks)
**Gate:** G1 — Infra alive at hour 4

## Goal

Stand up every external dependency and pick the demo's hero neighbourhood so all later phases have something concrete to build on. By the end of hour 4, four services must be running and one geography must be chosen.

## Parallel tracks

### Track A — ML: NIM serving on GX10
- [ ] Pull NIM containers for Nemotron Nano 9B v2 and Nemotron Super 49B (FP8)
- [ ] Pull NIM container for `nv-embedqa-e5-v5`
- [ ] Run all three via docker compose on GX10
- [ ] Verify with `curl` from laptop: `:8001`, `:8002`, `:8003` all return 200 on `/v1/models`
- [ ] Check `nvidia-smi` — confirm combined VRAM/unified memory < 90 GB and headroom remains
- [ ] Fallback ready: vLLM with a downloaded Nemotron Nano checkpoint if NIM containers misbehave

### Track B — Data: Ingestion + hero block selection
- [ ] Pull Utility Cut Permits (JSON) via CKAN API
- [ ] Pull Road Restrictions v3, Traffic Volumes — Midblock, One Way Streets
- [ ] Load into DuckDB with spatial extension
- [ ] Query: which 1 km² cell of Toronto has the highest count of utility cut permits in 2023–2025 where the same street segment was opened ≥ 3 times
- [ ] Lock the hero neighbourhood. Write its bbox to `.planning/phases/01-parallel-kickoff/hero-block.json`
- [ ] Export filtered permits as `permits.geojson` for the UI

### Track C — OR: Valhalla routing stack
- [ ] Download Toronto OSM extract (BBBike preferred)
- [ ] Run `ghcr.io/gis-ops/docker-valhalla/valhalla:latest` with `tile_files=Toronto.osm.pbf` + `build_tiles=True` (builds tiles + serves in one container)
- [ ] Serve on host port `:5000` (container port 8002 remapped) so downstream port contract is unchanged
- [ ] Smoke test: `POST /route` with two hero-block intersections in the request body, get sensible polyline
- [ ] Smoke test edge closure: send `exclude_polygons` covering a street segment, confirm route detours

**Engine swap note:** Originally specced as OSRM. Project-OSRM's official Docker image is amd64-only; the GX10's Grace Blackwell is arm64. Switched to Valhalla because (a) gisops maintains multi-arch (arm64-native) images, (b) closure simulation via `exclude_polygons` / `exclude_locations` is functionally equivalent to OSRM edge-blocking for the conflict graph. See Phase 1 CONTEXT D-75.

### Track D — FE: Leaflet scaffold
- [ ] Vite + React + Leaflet skeleton
- [ ] Hard-code two permit polygons over the hero block to verify rendering
- [ ] Timeline scrubber component (no real data yet, just UI)
- [ ] Naive/Optimized toggle (no real data yet, just UI)
- [ ] Empty chat panel docked right

## Exit criteria (G1)

All five must be true at hour 4:

1. `curl localhost:8001/v1/models` returns Nemotron Nano on the GX10
2. `curl localhost:8002/v1/models` returns Nemotron Super on the GX10
3. Valhalla returns a valid `/route` response for two coordinates inside the hero block
4. `hero-block.json` exists and has been visually sanity-checked
5. The Leaflet UI renders the hero block with two placeholder polygons

## Risks

| Risk | Mitigation |
|---|---|
| NIM containers fail to pull / start | Track A fallback: vLLM + Nano checkpoint. Decide by hour 2. |
| OSM extract too large to process in time | Use a Toronto-only sub-extract from BBBike instead of GTA-wide |
| Utility Cut Permits doesn't have repeat-excavation pattern | Widen window to 2020–2025, or include Building Permits — Active |
| Memory pressure on GX10 | Drop embedder for now, run only Nano + Super, add back in Phase 4 |

## Deliverables to next phase

- Running NIM endpoints
- `hero-block.json` with neighbourhood bbox
- `permits.geojson` for the hero neighbourhood
- Running Valhalla on `:5000`
- Leaflet UI shell
