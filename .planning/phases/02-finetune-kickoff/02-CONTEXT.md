# Phase 2: Fine-tune Kickoff - Context

**Gathered:** 2026-05-30
**Status:** ⏭ **CLOSED — do not plan, do not execute.**

> ⛔ **Phase 2 is closed (D-77, see body §"Phase Closure").**
> No LoRA fine-tune. No label corpus. No held-out eval. The Nemotron-3 Super 123B running locally on the GX10 via Ollama (D-76) replaces the tuned-Nano story as the demo's wow anchor. Phase 5 D-78 collapses the downstream eval/swap step in lockstep.
> The body of this doc below is preserved as a historical record of what *would* have been built.

<domain>
## Phase Boundary

Kick off a LoRA fine-tune of Nemotron Nano 9B v2 on Toronto utility-cut permit text → canonical JSON schema. Training launches detached and runs unattended for ~2–3 hours through Phases 3 and 4. Exit when the training process is alive on the GX10 with measurable loss reduction and the eval set is frozen.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**3 success criteria are locked.** See `02-SPEC.md` for full task definition (schema, LoRA config, trainer choice), exit criteria, and risk table.

Downstream agents MUST read `02-SPEC.md` before planning or implementing.

**In scope (from SPEC.md):**
- Label corpus assembly (revised below — see D-11)
- LoRA training launch on GX10 (Nemotron Nano 9B v2, r=16, α=32, 3 epochs, lr 2e-4)
- Held-out eval set
- Loss curve logging

**Out of scope:**
- Eval execution (Phase 5 owns this)
- Adapter swap into NIM (Phase 5)
- Pitch artifact capture (Phase 5)

</spec_lock>

<decisions>
## Implementation Decisions

### Label Corpus
- **D-11:** **0 hand-labels + 800 synthetic** for the **training set**. Nemotron Super 49B generates all 800 with the schema + 5 few-shot anchors at `temperature=0` for consistency. Saves the hand-labeling slot in Phase 1.
- **D-12:** **The eval set is NOT synthetic.** 50 hand-verified permits, drawn from a stratified sample (by utility_owner and work_type to cover the field vocab). Without human-anchored eval, the Phase 5 "lift" number is unmeasurable. This work happens during Phase 1 by the Pitch lead and one Data person — small enough not to bottleneck.
- **D-13:** Mitigate the "model learns Super's biases" risk by: (a) Super at `temperature=0`, (b) 25% spot-check of the synthetic set by the team during Phase 1 (200 permits checked), (c) reject any synthetic example where Super outputs an out-of-schema value.

### GX10 Memory Plan
- **D-14:** **Drop the embedder during training.** NIM `nv-embedqa-e5-v5` is stopped at hour 4. Embedder is ~2 GB and reloads in <5 minutes, so it returns at hour 22 (Phase 5 swap) — no permanent loss.
- **D-15:** During training (hours 4–22): GX10 runs Nemotron Super 49B (~50 GB) + Nano + LoRA training (~25 GB combined) + OSRM (~4 GB) + FastAPI/DuckDB (~5 GB) ≈ 84 GB. Within the 128 GB budget. Verify with `nvidia-smi` at hour 5.
- **D-16:** If memory still tight: pause Super NIM during training (chat panel falls back to Nano during Phase 3/4 work), restore Super at hour 22. Phase 3/4 don't strictly need Super for development.

### Swap Decision Bar (Phase 5 Gate)
- **D-17:** **≥ +15 points** overall schema-correct rate (tuned Nano vs raw Nano on the 50-permit eval set) → swap into the demo. SPEC's target.
- **D-18:** Below +15 pts: keep raw Nano in demo, reframe the slide as *"3 hours of LoRA on GX10 — preliminary lift: +N pts on `utility_owner` field"* leading with the field with the biggest gain. Honest but the GX10 narrative still survives.

### Trainer
- **D-19:** Vanilla `TRL SFTTrainer` + PEFT LoRA, bf16, no DPO / no QLoRA / no full-layer fine-tune. SPEC default.

### Fine-Tune Skipped — Phase 5 D-44 fallback fires (mid-execution amendment, 2026-05-30)
- **D-77:** **Phase 2 is closed without execution.** No LoRA training, no synthetic label corpus, no held-out eval set.
  - **Why:**
    - Nano NIM image is broken on arm64 (D-76); the original LoRA target doesn't exist locally.
    - Pulling Nemotron Nano 9B from HuggingFace via vLLM costs ~1.5 hr at the venue's ~3 MB/s wifi — too risky given the 36-hour clock.
    - LoRA-tuning a 33B MoE model (the next-best Ollama-resident option) is bigger, slower, less familiar; high failure-mode probability.
    - The discovery of a **local 123B Nemotron-3 Super** (D-76) makes the original training narrative redundant. We already have a strictly bigger model running locally.
  - **Pitch impact:** Phase 5 D-44 contingency was designed for exactly this — the slide re-anchors on "Nemotron running locally on this box, no internet" rather than on lift numbers. **The new anchor is even stronger than D-44 anticipated**: not just "Super 49B local," it's "**123 billion parameter Nemotron-3 Super local**."
  - **Time freed:** the ~3 hours of ML person-time that would have been training watch-time goes directly to **UI polish + dry-run rehearsal** in Phases 6/7. Hackathons are won on rehearsal, not on lift slides.
  - **Phase 5 implication:** see Phase 5 D-78. The eval/swap step is also closed; Phase 5 reduces to "verify chat works, capture `ollama show` output for the appendix slide."

### Claude's Discretion
- Tokenizer settings, max sequence length, batch packing, gradient checkpointing, optimizer choice (AdamW default), warmup ratio, logging cadence — all at planner/executor discretion within the LoRA config locked above. **(Moot per D-77.)**

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 2
- `.planning/phases/02-finetune-kickoff/02-SPEC.md` — **Locked requirements.** Read first.

### Project-level
- `.planning/PROJECT.md` — GX10 memory budget table (relevant to D-14 / D-15)
- `.planning/phases/01-parallel-kickoff/01-CONTEXT.md` — D-04 / D-05 (NIM-first decision); D-11/D-12 here depends on Phase 1 producing 800 synth + 50 hand-verified eval samples

### External docs
- HuggingFace TRL `SFTTrainer` docs — `huggingface.co/docs/trl/sft_trainer`
- HuggingFace PEFT LoRA docs — `huggingface.co/docs/peft/en/conceptual_guides/lora`
- Nemotron Nano 9B v2 model card — `build.nvidia.com/nvidia/nemotron-nano-9b-v2`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 produces the synthetic label corpus and the hand-verified eval set in `~/permitflow/data/`. Phase 2 just reads them.

### Established Patterns
- All GPU work runs on the GX10. Phase 2 training is launched via SSH/tmux from the laptop but executes on the GX10. SPEC requires `nohup` or `tmux detach` so it survives terminal close.

### Integration Points
- LoRA adapter is written to `~/permitflow/checkpoints/nano-toronto-ep{n}` per epoch. Phase 5 reads from there.

</code_context>

<specifics>
## Specific Ideas

- User instinct on memory: "drop the embedder, pull it back once training is over." Confirms D-14 — reversibility is the key insight. Apply that frame to anything else GX10-tight: prefer reversible pauses over permanent cuts.
- "0 hand + 800 synth" — user accepted the bias risk for time savings. D-13's mitigations matter; flag in plan-phase that the spot-check IS part of Phase 1 work, not optional.

</specifics>

<deferred>
## Deferred Ideas

- **DPO second stage on hand-corrected outputs** — would improve quality but doesn't fit the 3-hour training budget. Post-hackathon.
- **QLoRA / FP4 training** — possible if memory becomes an issue; defer the decision to hour 5 when `nvidia-smi` data is in hand.
- **Multi-field per-field eval rubrics** — for v1 we score categoricals as exact match and `expected_duration_days` as ±20%. Post-hackathon: design domain-specific rubrics.

</deferred>

---

*Phase: 2-Fine-tune Kickoff*
*Context gathered: 2026-05-30*
