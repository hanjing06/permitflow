# Phase 2: Fine-tune Kickoff - Discussion Log

**Date:** 2026-05-30
**Mode:** Interactive (autonomous --interactive), batched
**Areas discussed:** 4 of 4 presented

---

## Area 1: Label budget fallback

**Options presented:** 100 hand + 700 synth / 0 hand + 800 synth / Drop fine-tune / 50 hand eval-only

**User selection:** 0 hand + 800 synth

**Claude's follow-on:** Eval set still needs hand-verification (50 permits) or the lift number is unmeasurable. Captured as D-12.

**Decisions captured:** D-11, D-12, D-13

---

## Area 2: GX10 memory pressure plan

**Options presented:** Pause Super during training / Drop embedder / Train at FP4 / Use separate machine

**User selection:** "drop the embedder ? but once the training is over we can pull it back in no ?"

**Claude's interpretation:** Yes — embedder is ~2 GB and reloads in <5 min. Drop at hour 4, restore at hour 22.

**Decisions captured:** D-14, D-15, D-16 (fallback if memory still tight)

---

## Area 3: Swap decision bar

**Options presented:** ≥+15 pts / ≥+5 pts on any field / Any lift / ≥+20 pts or don't swap

**User selection:** ≥+15 pts schema-correct rate (recommended)

**Decisions captured:** D-17, D-18 (graceful framing if lift falls short)

---

## Area 4: Trainer choice

**Options presented:** Vanilla SFT / SFT + DPO / QLoRA / Full last-4-layer fine-tune

**User selection:** Vanilla SFTTrainer only (recommended)

**Decisions captured:** D-19

---

## Claude's Discretion

- Tokenizer settings, max seq length, batch packing, gradient checkpointing, optimizer, warmup ratio, logging cadence

---

## Deferred Ideas

- DPO second stage (post-hackathon)
- QLoRA / FP4 (decide at hour 5 if memory tight)
- Per-field eval rubrics (post-hackathon)
