# Phase 7 — Dry-Run Checklist

**Window:** Hour 34 → 36 · **Hard stop on commits:** Hour 35 (D-74)

Print or pin this. Punchlist keeper (pitch lead) checks items live.

---

## T-0 · Hour 34 · Setup (5 min)

- [ ] GX10 on side table, power LED visible, `nvidia-smi` ticking in a terminal (D-69)
- [ ] Laptop on stage, browser at `http://localhost:5173`, console clean
- [ ] Phone in airplane mode (no notifications mid-pitch)
- [ ] CONTINGENCY-CARDS.md printed and taped to back of laptop (D-73)
- [ ] Backup video copies present: **laptop local** AND **USB stick** (D-64)
- [ ] Phase 5 screenshots captured (`nvidia-smi` showing 123B resident + one chat latency capture)
- [ ] Pitch lead has script + 3 switch-line variants memorized (D-66)
- [ ] Tech standby identified, briefed, sitting front row (D-60, D-61)

---

## Run 1 · Hour 34:05 · Live, all-glitches-logged (90s)

- [ ] Live demo end-to-end. Don't pause to fix anything.
- [ ] Pitch lead delivers full script.
- [ ] Punchlist keeper writes down EVERY glitch seen (no editorializing).

**After Run 1 — 15 min triage window:**
- [ ] Top 3 glitches identified
- [ ] Each fix is **config / staging / cache only** — NOT code changes (D-70)
- [ ] All 3 fixed before Run 2

---

## Run 2 · Hour 34:45 · Live, post-fix (90s)

- [ ] Live demo again
- [ ] Verify the 3 fixes from Run 1 hold
- [ ] Log new glitches if any

**After Run 2 — 15 min triage window:**
- [ ] Top 2 new glitches resolved (still no code changes)
- [ ] If script ran > 95s: cut a sentence (D-70)

---

## Run 3 · Hour 35:15 · Dress rehearsal (90s)

- [ ] Final live demo with full polish
- [ ] If script ran > 100s: **cut a line** — don't try to speak faster (D-70)
- [ ] If 3 runs all under 95s with no panic moments → ready

---

## Hour 35:30 · WiFi-off run (D-71)

- [ ] Turn off WiFi on laptop AND phone
- [ ] Run the full 90s demo
- [ ] Note anything that fails: probably Leaflet map tiles or any CDN-served asset
- [ ] If anything fails: pre-bundle the missing asset (offline tiles, etc.) and re-test
- [ ] Re-test must complete by Hour 35:45

---

## Hour 35:50 · Record backup video (D-72)

- [ ] Pick the cleanest of Run 1/2/3
- [ ] Re-run it ONE more time at the pitch lead's rehearsed tempo (NOT arbitrary tempo — D-63)
- [ ] OBS or QuickTime recording at 1080p / 60fps
- [ ] **Silent** — no audio track (D-62)
- [ ] Save as `~/permitflow/demo/backup.mp4` (or similar)
- [ ] Copy to USB stick (D-64)
- [ ] Verify both copies play

---

## Hour 36:00 · Final checks

- [ ] Browser tab pinned, no other tabs open
- [ ] System notifications silenced
- [ ] Slack/Discord/email closed
- [ ] Backup video tested on the laptop's actual video player (not just preview)
- [ ] Power adapter plugged in
- [ ] CONTINGENCY-CARDS.md re-read by pitch lead (1 min)
- [ ] Tech standby has the snapshot path memorized for post-event recovery
- [ ] Deep breath

---

## What constitutes a STOP signal during a dry run

A dry run that exhibits any of these triggers the 5-second trip-wire (D-65):
- Chat panel shows spinner > 5 seconds with no streaming text
- Map renders blank/grey for > 5 seconds
- Counter shows `NaN` / `undefined` / stuck mid-tween
- Toggle stops responding
- Any 404 or red text in the visible UI

If any of those happen during a dry run: log it, don't fix on stage. Practice triggering the switch line + backup video instead.

---

## Day-of pitch — what NOT to do

- ❌ Don't reload the page mid-pitch (counter loses its tween-from-zero feel)
- ❌ Don't restart Ollama / Valhalla / FastAPI mid-pitch (D-67)
- ❌ Don't apologize for switching to the backup video (D-65 makes it look intentional)
- ❌ Don't commit code or planning after hour 35 (D-74). Even "just one small fix" — no.
- ❌ Don't introduce a new metric, color, or string the team hasn't seen
- ❌ Don't oversell the conflict graph as "Valhalla-validated" — it's a space-time proxy (Phase 3 honest-framing rule)
