# Phase 6: Demo Polish - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Convert the working system into a 90-second presentation. No new features. UI polish, three-slide deck, pitch script timed to ≤ 90s, back-of-envelope cost-avoidance number with the math visible. Exit at G3 — offline demo runs cleanly end-to-end.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**5 success criteria are locked.** See `06-SPEC.md`.

**In scope:** UI polish · 3-slide deck · pitch script · cost-avoidance math · PROJECT.md update (per Phase 3 D-21)
**Out of scope:** New features · animation (cut, D-51) · live camera (cut, D-54) · code changes after hour 35 (per Phase 7 G3)

**Upstream items landing here:**
- Phase 3 D-21: PROJECT.md demo arc → future-only
- Phase 3 D-26: cost-avoidance figure (revised to back-of-envelope, D-53)
- Phase 4 D-31: timeline animation decision (cut, D-51)
- Phase 4 D-37: canned chat scenarios drafted + cached + tested by hour 30
- Phase 4 D-35: pitch lead picks the headline metric from the tri-stat counter

</spec_lock>

<decisions>
## Implementation Decisions

### Team Structure — Triage Mode
- **D-52:** **Free-for-all triage.** No fixed track owners during Phase 6 — the team looks at what's worst and fixes it. Tracks the user's instinct that fixed assignment over-scopes a polish phase.
- **D-52b:** **One designated "punchlist keeper"** (recommended: pitch lead, since they're already watching the build). Maintains a single visible list (whiteboard or shared doc) of "what still feels broken." Anyone can pick from it. Anyone can add to it. Prevents the swarm from re-fixing the same thing or missing items entirely.

### Timeline Animation — Cut
- **D-51:** **Animation cut. Lock static color-coded snapshot from Phase 4.** This overrides the Phase 4 D-31 conditional. Polish bandwidth goes to typography, color, counter feel — not motion.

### Cost-Avoidance Number — Back-of-Envelope
- **D-53:** **Derived from City of Toronto operating budget and construction figures.** Approximate method:
  1. Find published "annual construction disruption cost" or "congestion cost" from a recent City of Toronto budget / report / press release.
  2. Divide by total lane-days disrupted per year (estimate from Road Restrictions feed historical density).
  3. Resulting `$/lane-day` is the multiplier for the counter.
  4. **Show the math on the deck slide.** Two lines: "$X / Y lane-days = $Z per lane-day." Judges respect transparent derivation more than a cited number with no context.
- **D-53b:** If even a back-of-envelope source can't be assembled by hour 32, fall through to dropping the dollar metric (counter becomes two-stat: permits considered + excavations avoided). Don't fake it.

### Camera Flourish — Cut
- **D-54:** **Drop the traffic camera flourish entirely.** Cuts SPEC subsystem D. Frees ~3 hours of dev/polish time. The savings counter and chat panel carry the demo — camera was sugar.

### UI Polish Focus (revised scope)
- **D-55:** With animation and camera cut, polish focuses on:
  - Hero block auto-centring and zoom on load
  - Polygon saturation/outline distinguishing merged (amber) / conflict-deferred (red) / singleton (neutral)
  - Counter typography — clear, large, tween-animated on toggle
  - Toggle button — unambiguous active state ("Naive | Optimized")
  - "Running on GX10" badge on the chat panel (large, visible, period-accurate font)
  - Top-bar headline metric always visible
  - **PROJECT.md demo arc rewritten** for future-only narrative (D-21) — by hour 30 at latest

### Pitch Lead Deliverables (hard deadlines)
- **D-56:** **Hour 28** — first draft of 90-second pitch script (paper, untimed)
- **D-57:** **Hour 30** — canned chat scenarios drafted, cached, tested (per Phase 4 D-37)
- **D-58:** **Hour 30** — headline metric chosen from tri-stat (per Phase 4 D-35); pitch script revised around it
- **D-59:** **Hour 33** — three-slide deck finished, script timed under 90s, three rehearsals done

### Claude's Discretion
- Exact color hex codes, font family, slide template (Keynote vs slides.com vs PDF), screenshot vs in-app for slides, microphone strategy.

</decisions>

<canonical_refs>
## Canonical References

### Phase 6
- `.planning/phases/06-demo-polish/06-SPEC.md` — **Locked requirements.**

### Project-level
- `.planning/PROJECT.md` — **must be updated this phase** to reflect future-only arc (D-21). Update file location: PROJECT.md § "The 90-second arc" — rewrite to next-quarter framing.
- `.planning/phases/03-optimizer-build/03-CONTEXT.md` — D-21 (pivot reason)
- `.planning/phases/04-ui-chat-panel/04-CONTEXT.md` — D-33 (tri-stat), D-35 (headline metric), D-37 (canned scenarios deadline)
- `.planning/phases/05-finetune-eval-swap/05-CONTEXT.md` — D-44 (raw-Nano fallback narrative if lift weak — affects which slide we ship)

### External (Phase 6 research)
- City of Toronto open budget — for D-53 cost derivation
- City of Toronto Congestion Management Strategy reports — `toronto.ca/services-payments/streets-parking-transportation/road-construction-projects/congestion-management/` (verify URL)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- All Phase 4 UI components — polish in place, don't rewrite.
- Phase 5's `eval-report.json` and screenshots feed the deck.
- Phase 3's `metrics.json` is the source for the on-screen counter values.

### Established Patterns
- No code changes after hour 35 (Phase 7 G3). Phase 6 is the LAST code-touching phase.

### Integration Points
- The deck references screenshots from the live app — keep screenshots current after each polish pass (last update no later than hour 33).

</code_context>

<specifics>
## Specific Ideas

- User trimmed Phase 6 aggressively: cut animation, cut camera, cut TCMP authority claim. This is consistent with the MVP instinct that ran through Phase 4 (cut animation) and Phase 3 (hero-block only). The pitch is becoming leaner — pitch lead must hold the line.
- "Free-for-all triage" — accepted, but added the punchlist-keeper (D-52b) because hackathon swarms reliably waste 30+ min without a visible task list. Single source of truth, not a manager.

</specifics>

<deferred>
## Deferred Ideas

- **Timeline animation** — fully cut. Not Phase 7. Post-hackathon if PermitFlow continues.
- **Live traffic camera** — fully cut.
- **Authority-cited cost source (TCMP)** — replaced by back-of-envelope. Post-hackathon work: actually find and validate the figure for a production pitch.
- **Slide animation / build effects** — keep slides static unless pitch lead instinct says otherwise. Don't over-produce.

</deferred>

---

*Phase: 6-Demo Polish*
*Context gathered: 2026-05-30*
