# Phase 7 — Dry Runs & Backup

**Window:** Hour 34–36
**Owners:** All

## Goal

Make the demo bulletproof. Two hours, three full run-throughs, one backup video, and a contingency for each plausible failure. No code changes after hour 35.

## Tasks

### A — Three full dry runs
- [ ] Run 1: With everything live (NIM, OSRM, FastAPI, UI, chat). Note every glitch.
- [ ] Run 2: Fix the top 3 glitches from Run 1.
- [ ] Run 3: Repeat with the actual pitch person presenting.
- [ ] If any of the 3 runs takes > 100 seconds, cut a line from the script.

### B — Offline test (the WiFi-off test)
- [ ] Disconnect the laptop and the GX10 from WiFi/ethernet
- [ ] Run the full demo
- [ ] Anything that fails to load, fix it (likely candidates: external map tiles, Traffic Camera, any CDN'd font/icon)
- [ ] Decision: ship offline-first if the venue WiFi is unreliable

### C — Backup video
- [ ] Screen-record the best of the 3 dry runs at 1080p, 60fps
- [ ] Edit to exactly 90 seconds
- [ ] Embed audio of the pitch script (not live mic at venue — clean studio take)
- [ ] Save to laptop locally *and* to a USB stick *and* upload to a private link
- [ ] If the live demo dies on stage, the pitch person says one prepared sentence and plays the video. No fumbling.

### D — Contingency cards
Tape these to the back of the laptop or memorize them.

| If this fails... | Do this |
|---|---|
| Chat is slow / hangs | Click the cached "What if I close X" canned scenario instead |
| Map tiles won't load (no internet) | Fall through to bundled offline tile set (prep in C) |
| NIM container crashes mid-demo | Restart command pre-typed in a terminal; or play backup video |
| Counter shows weird number | Refresh page; the Optimized timeline is loaded fresh |
| Traffic camera dead | Pre-recorded clip plays instead (loaded in Phase 6) |
| GX10 unreachable from laptop | Backup video, no apologies |

### E — Final checks
- [ ] PROJECT.md and ROADMAP.md updated with actual results (phase outcomes, headline numbers)
- [ ] Repo committed and pushed
- [ ] Devices charged, USB stick in pocket
- [ ] Pitch person fed, hydrated, has water on stage

## Exit criteria

By hour 36:

1. Three successful dry runs completed
2. Backup video exists in two locations
3. WiFi-off run passes
4. Contingency cards reviewed
5. No code commits after hour 35

## Risks

| Risk | Mitigation |
|---|---|
| Last-minute "one more thing" temptation | Hard rule: no commits after hour 35. The team lead enforces. |
| Backup video looks bad | Re-record from the cleanest dry run, prioritize that over a 4th live run |
| Pitch person under-rehearsed | Cut script length further; conviction > completeness |

## Post-hackathon (out of scope but worth noting)

- Productionization: full City of Toronto integration, real-time permit queue, official cost figures, contractor-facing portal
- Larger fine-tune corpus: extend to all four permit categories, not just utility cuts
- Other cities: Montréal and Vancouver publish similar open data; the system generalises
