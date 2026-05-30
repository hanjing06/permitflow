# Phase 7: Dry Runs & Backup - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Two hours. Three dry runs. WiFi-off test. Backup video recorded. Contingency cards reviewed. No code changes after hour 35. Exit when the demo can be delivered cleanly, with a known safety net for every plausible failure.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**5 success criteria are locked.** See `07-SPEC.md`.

**In scope:** Dry runs · offline test · backup video · contingency cards · final checks
**Out of scope:** Any code change · feature additions · UI changes (G3 frozen at hour 34)

</spec_lock>

<decisions>
## Implementation Decisions

### Stage Presence
- **D-60:** **Pitch lead presents solo.** One tech-fluent teammate sits in the front row to handle judge follow-up questions after the 90s. Clean stage, single voice during the pitch.
- **D-61:** Tech standby is *the same person* who owns the GX10 / NIM stack — they can answer "yes that's a 49B model running locally" without lookup. Pick this person at hour 34, not earlier; assign whoever has the most current systems context.

### Backup Video Audio
- **D-62:** **Silent video + live narration.** Video runs the visual 90s loop without sound; pitch lead narrates over it live, with the same script as the live demo. Same words, different visual source.
- **D-63:** **Why this beats pre-recorded voiceover:** if a live failure forces the switch mid-pitch, the narration continues seamlessly — judges don't experience a voice-change tell. Risk: timing drift if pitch lead's pace differs from the recorded video. Mitigate by recording the video at the pitch lead's *rehearsed* tempo (hour 35), not arbitrary tempo.
- **D-64:** Two video copies: laptop local + USB stick. Both at 1080p/60. No cloud-only copy (venue WiFi unreliable).

### Live-to-Backup Trip-Wire
- **D-65:** **5-second visible-failure rule.** If anything on the demo UI is visibly broken for >5 seconds during the live run (404 in chat panel, blank map, frozen scrubber, missing counter), pitch lead delivers a single prepared line ("Let me show you the recorded version — same system") and switches to backup video.
- **D-66:** Prepared line is **rehearsed in every dry run** so it sounds natural, not panic. Three flavors written; pitch lead picks the one that fits the moment.
- **D-67:** **Never improvise recovery on stage.** Don't fix things. Don't reload. Don't restart NIM containers. The switch is the recovery.

### Team Position & GX10 Visibility
- **D-68:** **Team in front row of audience.** GX10 placed on a side table where judges can see it (not behind the laptop). Pitch script *gestures* to the GX10 during the "all running on this box" line — physical, not metaphorical.
- **D-69:** GX10 must be set up at the venue **with its power LED on and a small visible status indicator** (e.g., a terminal showing `nvidia-smi` ticking) — proves the demo is live, not video. Tech standby owns this.

### Dry-Run Cadence
- **D-70:** Three runs, in order:
  1. **Run 1 (hour 34, ~5 min after entering Phase 7)** — everything live, all glitches logged. Pitch lead delivers the script.
  2. **Run 2 (hour 34:45)** — top 3 glitches from Run 1 must be fixed *before* this run starts. Note: fixes ≠ code changes; they're config/staging/cache fixes only.
  3. **Run 3 (hour 35:15)** — final dress rehearsal. If this run > 100s, *cut a line from the script* rather than try to speed up.
- **D-71:** **Hour 35:30 — WiFi-off run.** Disconnect everything from network. If anything fails, fix the staging (pre-bundle missing assets) and re-test by hour 35:45.
- **D-72:** **Hour 35:50 — record backup video** from the cleanest run available. No further runs after this.

### Contingency Cards
- **D-73:** Six cards, printed/taped to the back of the laptop:
  1. *Chat hangs* → click cached canned scenario
  2. *Map tiles won't load* → fall through to bundled offline tiles
  3. *NIM crashes mid-demo* → switch to backup video (don't restart)
  4. *Counter shows weird number* → refresh page
  5. *GX10 unreachable* → switch to backup video, gesture to box, "system runs locally"
  6. *Pitch lead freezes* → tech standby delivers next sentence from memory; pitch lead resumes when ready

### No-Commit Hard Stop
- **D-74:** **No commits to repo or vault after hour 35.** Pitch lead enforces. Even "just one small fix" — no. The team lead's job from hour 35 is saying no.

### Claude's Discretion
- Screen recording tool (OBS, QuickTime), USB stick format, exact dry-run venue setup, contingency card physical format.

</decisions>

<canonical_refs>
## Canonical References

### Phase 7
- `.planning/phases/07-dry-runs-backup/07-SPEC.md` — **Locked requirements.**

### Project-level
- `.planning/PROJECT.md` — updated by Phase 6 to reflect future-only arc; this phase rehearses against the updated narrative
- `.planning/phases/06-demo-polish/06-CONTEXT.md` — D-56–D-59 (pitch deadlines that feed Phase 7's rehearsal-ready state)

### External docs
- OBS recording config — venue-specific; tech standby pre-configs on hour 34

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The frozen build from Phase 6 — nothing new gets built here.

### Established Patterns
- Atomic commits per phase. Phase 7 produces **no code commits** by design (D-74). Final commit is the Phase 6 closeout.

### Integration Points
- Backup video file path lives outside the repo (e.g., `~/permitflow/demo/backup.mp4`). USB stick is a manual copy.

</code_context>

<specifics>
## Specific Ideas

- User chose **silent video + live narration** — sharp instinct. Recovery is invisible to judges because the voice is continuous. This is a hackathon-vet-level call.
- User chose **front-row + visible GX10** — turns the hardware into a prop. The pitch literally points at it. Strong physical-stakes moment.
- User chose the **5-second trip-wire** — concrete, rehearsable, removes panic-judgment from the stage.

</specifics>

<deferred>
## Deferred Ideas

- **Post-demo Q&A prep cards** — judges typically ask 2–3 questions after a pitch. Worth drafting in Phase 7 if time, but not blocking. Pitch lead + tech standby can wing it.
- **Demo recording for portfolio / post-event use** — separate from the backup video. Capture the live run if it goes well. Defer to post-hackathon.

</deferred>

---

*Phase: 7-Dry Runs & Backup*
*Context gathered: 2026-05-30*
