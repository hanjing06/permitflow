---
phase: 01-parallel-kickoff
plan: 01
subsystem: data-ingestion
tags:
  - data-ingestion
  - ckan
  - toronto-open-data
  - gap-closure
requirements:
  - G1-DATA
dependency_graph:
  requires:
    - backend/open_toronto.py  # CKAN downloader (existing)
  provides:
    - data/utility_cuts.csv
    - data/building_permits.csv
    - data/road_resurfacing.csv
    - data/sidewalk_construction.csv
    - data/road_restrictions.csv
    - data/road_reconstruction.csv  # idempotent re-pull from this run
  affects:
    - .planning/HEALTHCHECK.md   # "Data ingestion: actual files pulled" can flip 🟡 → ✅ (with caveats)
    - Plan 01-02                  # unblocks hero block selection
tech_stack:
  added: []                       # no new libs; existing pandas/requests
  patterns:
    - "Per-dataset try/except so a single bad CKAN id no longer aborts a batch (Rule 2)"
    - "CKAN package_search to discover correct package ids when curated mapping is stale (Rule 1)"
key_files:
  created:
    - data/utility_cuts.csv
    - data/building_permits.csv
    - data/road_resurfacing.csv
    - data/sidewalk_construction.csv
    - data/road_restrictions.csv
    - data/road_reconstruction.csv
    - .planning/phases/01-parallel-kickoff/01-01-SUMMARY.md
  modified:
    - backend/open_toronto.py
decisions:
  - "Skipped watermain_breaks: CKAN only publishes XLSX + SHP for this dataset (no CSV/GeoJSON/JSON). Plan permits CONTEXT-tier skip; revisit in Phase 3 if needed (would require openpyxl or shapely+pyshp)."
  - "Fetched road_restrictions from Toronto's secure.toronto.ca v3 JSON feed (the CKAN package's only json resource), with a regex-strip of invalid \\-escapes the feed emits. 2,651 rows flattened from Closure[]."
  - "Discovered candidate permit datasets (utility_cuts, building_permits) ship without inline geometry on CKAN — only GEO_ID + DISPLAY_DESC (street address). Plan 01-02 must do address geocoding or GEO_ID spatial-join against the program datasets (road_reconstruction/resurfacing/sidewalk_construction) which DO carry LineString geometries."
metrics:
  duration: "~12 minutes"
  completed: "2026-05-31"
  tasks_completed: 1
  files_created: 7
  files_modified: 1
---

# Phase 01 Plan 01: Pull Toronto Open Data CKAN Datasets — Summary

Pulled five new CKAN datasets (one re-pull) into `data/`; hardened the downloader after discovering a stale CKAN package id (`building-permits-active` → `building-permits-active-permits`) and an inline-error that was aborting batch runs.

## What landed

| Dataset                  | Rows    | Geometry column             | Shape                  | Source                                                 |
| ------------------------ | ------- | --------------------------- | ---------------------- | ------------------------------------------------------ |
| utility_cuts             | 87,880  | NONE (uses GEO_ID + address)| n/a — spatial-join req | CKAN datastore CSV                                     |
| building_permits         | 228,573 | NONE (uses GEO_ID + address)| n/a — spatial-join req | CKAN datastore CSV                                     |
| road_resurfacing         | 1,478   | `geometry`                  | LineString (GeoJSON)   | CKAN GeoJSON dump                                      |
| sidewalk_construction    | 99      | `geometry`                  | GeoJSON (LineString)   | CKAN CSV with embedded geometry column                 |
| road_restrictions        | 2,651   | `latitude` + `longitude`    | Point (lat/lon pair)   | secure.toronto.ca v3 JSON, flattened from `Closure[]`  |
| road_reconstruction      | 325     | `geometry`                  | LineString (GeoJSON)   | CKAN GeoJSON dump (re-pull, idempotent overwrite)      |

All four load-bearing datasets (utility_cuts, building_permits, road_resurfacing, sidewalk_construction) cleared the row-count thresholds from `must_haves.artifacts`.

## What was skipped

- **watermain_breaks** — CKAN package `watermain-breaks` only exposes XLSX (1990–2016 Excel) and SHP (zipped shapefile) resources; the downloader's allowed-formats whitelist is `(csv, geojson, json)` and there is no equivalent CSV resource. Plan explicitly allows CONTEXT-tier skip. If Phase 3 needs this, add `openpyxl` to the nix shell and a one-off XLSX→CSV reader.

## Deviations from plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale CKAN package id for building permits**
- **Found during:** Task 1 (CKAN pull, first run)
- **Issue:** `package_show?id=building-permits-active` returned HTTP 404. CKAN's real id is now `building-permits-active-permits` (verified via `package_search?q=building+permit`). The wrong id aborted the entire batch via an unhandled `HTTPError` before context datasets got a chance to run.
- **Fix:** Patched `backend/open_toronto.py` CANDIDATES dict to the correct id.
- **Commit:** e77b3fa

**2. [Rule 2 - Robustness] Single bad id aborted the whole batch**
- **Found during:** Task 1 (same run as above)
- **Issue:** `fetch_package()` raised `HTTPError` straight out of `main()`'s loop, so a single dead id halted ANCHORS/CANDIDATES/CONTEXT processing partway. The downloader is supposed to pull as much as it can; per-dataset failures should be logged and skipped, like the existing `pd.read_csv` failure path already does.
- **Fix:** Wrapped `fetch_package()` in try/except in `download_dataset()`, mirroring the existing `df = pd.read_csv(...)` try/except. Now a 404/timeout on one id skips that dataset and continues.
- **Commit:** e77b3fa

### Discovered constraints (no auto-fix; surfaced to next plan)

**3. Candidate permit datasets carry no inline geometry**
- **Found during:** Task 1 verification (geometry-column scan)
- **What:** `utility_cuts` and `building_permits` ship with `GEO_ID` (Toronto geo-reference code) and `DISPLAY_DESC` (street address like `"154 ROBINA AVE (Between GLENHURST AVE AND EARLSDALE AVE)"`) — no lat/lon, no geometry blob. Confirmed across CKAN's CSV, JSON, AND XML resources for both packages; this is how Toronto Open Data publishes these.
- **Implication for Plan 01-02:** Hero block selection cannot just `SELECT ST_AsGeoJSON(geometry) ...` on the candidate datasets. It will need either (a) a GEO_ID spatial-join against the program datasets that DO carry LineStrings, or (b) address-string geocoding against the `DISPLAY_DESC` field. Recommend (a) — cheaper, deterministic, and the GEO_IDs are stable centerline-segment ids.
- **Plan-spec mismatch:** Plan 01-01's `must_haves.truths[2]` says "Files retain a parseable geometry column ... so hero block ranking can run." This is true for the program datasets and road_restrictions, but not for the candidate datasets. The geometry constraint should be reframed as "files retain a spatial referent (geometry OR GEO_ID OR address)" — file this against 01-02 SPEC.

**4. road_restrictions feed has invalid JSON escapes**
- **Found during:** Task 1 post-fetch parsing
- **What:** The CKAN package for `road-restrictions` resolves to a non-CKAN JSON endpoint at `secure.toronto.ca/opendata/cart/road_restrictions/v3?format=json`. The body contains backslash-escapes that aren't valid JSON (e.g. lone `\` not followed by `"/bfnrtu\`). Python's `json.loads` and pandas both choke.
- **Fix:** Inline regex strip of bad backslashes before `json.loads`, then flatten `Closure[]` into a DataFrame and write CSV. Done outside the downloader (one-off `python -c`) per plan note about not over-modifying `open_toronto.py`. If Phase 3 needs to re-fetch, this script should move into `open_toronto.py` behind a special-case branch for the road_restrictions package id.

### Authentication gates

None. All CKAN endpoints are public.

## Python invocation used

`nix develop -c python backend/open_toronto.py {all|candidates|context}` — system has no global `python` (nix-managed); `nix develop` provides Python 3.13.13 with pandas + requests from `flake.nix`. No `nix run .#default` needed — the dev shell was sufficient.

## Acceptance criteria checklist

- [x] All six expected CSVs exist in `data/` — **five of six**: watermain_breaks documented as CONTEXT-tier skip (allowed by `done` criterion).
- [x] utility_cuts.csv has > 100 rows — **87,880**
- [x] building_permits.csv has > 100 rows — **228,573**
- [x] road_resurfacing.csv > 50 rows — **1,478**
- [x] sidewalk_construction.csv > 50 rows — **99** (passes; threshold is 50, plan's `min_lines: 50`)
- [~] Each file has parseable geometry — **anchors and road_restrictions yes; candidates carry GEO_ID + address only** (see Deviation 3 above; reframes the constraint for Plan 01-02)

## Impact on HEALTHCHECK

The `Data ingestion: actual files pulled` row can flip from 🟡 to ✅ (with a footnote that watermain_breaks is XLSX-only on CKAN and is deferred per plan permission). HEALTHCHECK update is the next plan's housekeeping, not this one's commit.

## Self-Check: PASSED

- File `data/utility_cuts.csv` — FOUND (95,641 lines incl header, 87,880 data rows)
- File `data/building_permits.csv` — FOUND (228,574 lines, 228,573 data rows)
- File `data/road_resurfacing.csv` — FOUND (1,485 lines, 1,478 data rows)
- File `data/sidewalk_construction.csv` — FOUND (105 lines, 99 data rows)
- File `data/road_restrictions.csv` — FOUND (2,652 lines, 2,651 data rows)
- File `data/road_reconstruction.csv` — FOUND (325 data rows)
- File `data/watermain_breaks.csv` — INTENTIONALLY ABSENT (no CSV/JSON/GeoJSON resource on CKAN; documented above)
- Commit e77b3fa — FOUND in `git log`
