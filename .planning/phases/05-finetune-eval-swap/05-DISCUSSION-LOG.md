# Phase 5: Fine-tune Eval & Swap - Discussion Log

**Date:** 2026-05-30
**Mode:** Interactive (autonomous --interactive), batched

---

## Area 1: Late-training handling

**Options presented:** Latest checkpoint / Wait 1h / Kill training / Skip eval

**User selection:** Use latest completed checkpoint (recommended)

**Decisions captured:** D-42, D-43 (hard deadline hour 23)

---

## Area 2: Serving path for tuned Nano

**Options presented:** NIM LoRA → vLLM fallback / Side vLLM immediately / Merge into base / Permanent side-by-side

**User selection:** Try NIM LoRA loading, fall back to side-vLLM (recommended)

**Decisions captured:** D-45 (NIM attempt, 30 min budget), D-46 (vLLM fallback on :8011), D-47 (single env var swap)

---

## Area 3: Below-bar pitch fallback

**Options presented:** Best-field lead / Raw Nano local serving / Loss curve only / Hide the number

**User selection:** Show raw Nano running locally, skip the lift claim

**Claude's note:** This is the honest fallback. GX10 narrative re-anchors on inference, not training. Loss curve + nvidia-smi go into Q&A appendix (D-48).

**Decisions captured:** D-44, D-48

---

## Area 4: Checkpoint selection

**Options presented:** Best by eval loss / Last epoch / Eval all three / Pitch-optimal pick

**User selection:** Best by eval loss (recommended)

**Decisions captured:** D-49, D-50 (stratified dev subset)

---

## Claude's Discretion

- Eval script structure
- Batching strategy
- JSON output schema for eval-report.json
- Screenshot tooling
- Plot styling

---

## Deferred Ideas

- Self-consistency / pass@k eval
- Per-permit error analysis (v2)
- Adapter merge into base weights (if both serving paths fail)
