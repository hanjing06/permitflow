# Contingency Cards (D-73)

Print this page, cut into 6 cards, tape to the back of the laptop in the order shown.
**Rule:** never improvise recovery on stage (D-67). The switch IS the recovery.

---

```
╔══════════════════════════════════════════════════════════════╗
║  CARD 1 · CHAT HANGS                                         ║
║                                                              ║
║  Symptom: chat panel shows spinner > 5 sec, no text streams  ║
║                                                              ║
║  Action: click the next canned scenario button.              ║
║         The cached response fires immediately.               ║
║                                                              ║
║  Do NOT: reload, restart Ollama, retype the question.        ║
╚══════════════════════════════════════════════════════════════╝
```

---

```
╔══════════════════════════════════════════════════════════════╗
║  CARD 2 · MAP TILES WON'T LOAD                               ║
║                                                              ║
║  Symptom: map is blank grey, no Toronto street outlines      ║
║                                                              ║
║  Action: refresh the page ONCE. Tiles fall through to the    ║
║         bundled offline cache.                               ║
║                                                              ║
║  If still blank after 5 sec: TRIGGER CARD 5 (backup video).  ║
╚══════════════════════════════════════════════════════════════╝
```

---

```
╔══════════════════════════════════════════════════════════════╗
║  CARD 3 · OLLAMA / NEMOTRON CRASHES MID-DEMO                 ║
║                                                              ║
║  Symptom: chat returns "(chat unavailable)" fallback frame   ║
║                                                              ║
║  Action: pitch lead delivers prepared line, switches to      ║
║         backup video. Tech standby does NOT restart Ollama.  ║
║                                                              ║
║  Snapshot lives at:                                          ║
║   .planning/phases/01-parallel-kickoff/ollama-modelfile.txt  ║
║  (post-event recovery only — never during pitch)             ║
╚══════════════════════════════════════════════════════════════╝
```

---

```
╔══════════════════════════════════════════════════════════════╗
║  CARD 4 · COUNTER SHOWS WEIRD NUMBER                         ║
║                                                              ║
║  Symptom: tri-stat shows NaN, undefined, 0, or stuck mid-    ║
║         tween                                                ║
║                                                              ║
║  Action: refresh the page ONCE. The /metrics fetch will      ║
║         re-run and counter tweens from 0.                    ║
║                                                              ║
║  If still wrong after refresh: continue pitch, ignore the    ║
║  counter, gesture to the map instead. Don't draw attention.  ║
╚══════════════════════════════════════════════════════════════╝
```

---

```
╔══════════════════════════════════════════════════════════════╗
║  CARD 5 · GX10 UNREACHABLE                                   ║
║                                                              ║
║  Symptom: every endpoint returns network error; map blank;   ║
║         backend health check fails                           ║
║                                                              ║
║  Action: pitch lead delivers the prepared line               ║
║         ("Let me show you the recorded version — same        ║
║         system"), switches to backup video, gestures to      ║
║         the GX10 box: "system runs locally on this box."     ║
║                                                              ║
║  Tech standby: do NOT poke at the GX10 during the pitch.     ║
║  Diagnose after.                                             ║
╚══════════════════════════════════════════════════════════════╝
```

---

```
╔══════════════════════════════════════════════════════════════╗
║  CARD 6 · PITCH LEAD FREEZES                                 ║
║                                                              ║
║  Symptom: pitch lead loses the thread, silence > 3 sec       ║
║                                                              ║
║  Action: tech standby (front row) delivers the next          ║
║         sentence from memory. Pitch lead picks up at the     ║
║         next natural beat.                                   ║
║                                                              ║
║  No apology, no "where was I" — keep moving.                 ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Prepared switch-line (D-66)

Three flavors — pick the one that fits the moment:

1. *"Let me show you the recorded version — same system, same data."*
2. *"Real demos are messy. Here's the version we recorded earlier."*
3. *"This is the same flow, just on video — the box is still running it live."*

Rehearse all three in dry runs so whichever you pick sounds natural, not panicked.
