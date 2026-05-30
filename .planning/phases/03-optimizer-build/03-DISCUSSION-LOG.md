# Phase 3: Optimizer Build - Discussion Log

**Date:** 2026-05-30
**Mode:** Interactive (autonomous --interactive), batched

---

## Area 1: Optimizer time scope

**Options presented:** Historical only / Future only / Both / Historical counter + future chat

**User selection:** Future only

**Major implication:** PROJECT.md's "watch one block over 18 months" demo arc is no longer accurate. The system now shows next-quarter planned permits and projected savings. Captured as D-20/D-21/D-22/D-23. Phase 6 polish must update PROJECT.md to reflect the pivot.

---

## Area 2: Conflict graph scope

**Options presented:** Hero-block only / Hero + 2km buffer / Citywide / Hero + lazy citywide

**User selection:** Hero-block only (recommended)

**Decisions captured:** D-24, D-25 (chat constrained to hero-block streets with graceful out-of-scope message)

---

## Area 3: Cost-avoidance dollar source

**Options presented:** TCMP / Generic industry / User-time-based / Skip the $

**User selection:** Toronto Congestion Management Plan (recommended)

**Decisions captured:** D-26 (TCMP primary, generic fallback), D-27 (counter ordering)

---

## Area 4: Singleton cluster handling

**Options presented:** Filter out / Show as 'already optimal' / Group by utility / Treat identically in counter

**User selection:** Treat them identically to merged in the counter

**Claude's nuance:** Implemented as a two-metric counter (D-28). `permits_considered` includes singletons (the headline). `excavations_avoided` does not (the honest savings). Visual color also distinguishes them (D-29).

**Decisions captured:** D-28, D-29

---

## Claude's Discretion

- DBSCAN eps / min_samples starting values
- Screenline intersection selection (manual list)
- Volume-data gap fallback
- FastAPI project layout

---

## Deferred Ideas

- Citywide conflict graph (v2)
- Retrospective historical optimizer (post-hackathon)
- Demand-responsive scheduling (post-hackathon)
- **PROJECT.md demo arc update** — must happen in Phase 6 polish
