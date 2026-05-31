# Phase 5: Verification & Pitch Artifacts - Context

**Gathered:** 2026-05-30
**Status:** REDUCED per D-78 — most of this doc is moot

> ⚠ **Reality-check (2026-05-31):** Phase 5 is reduced to verification + screenshot capture.
> - **D-77 closed Phase 2** — no LoRA was trained. There is nothing to eval and nothing to swap.
> - **D-78** collapses Phase 5 to: (a) `ollama-modelfile.txt` snapshot ✅ (captured in Phase 1), (b) `nvidia-smi` screenshot showing the 123B resident in GPU memory ❌, (c) one live chat round-trip latency screenshot ❌. See body §"Phase 5 Reduced".
> - The eval-set / LoRA-swap / NIM-`--lora-modules` / vLLM-fallback content below (D-42 through D-46) is preserved as historical record only. **Do not plan against it.**

<domain>
## Phase Boundary

Evaluate the LoRA checkpoint from Phase 2 on the hand-verified eval set, decide whether to swap it into the live demo, and capture the pitch artifacts (loss curve, side-by-side examples, headline lift number, `nvidia-smi` screenshot). Exit when either (a) tuned Nano is live in the pipeline with a documented lift ≥ +15 pts, or (b) the fallback "raw Nano local serving" pitch is locked in.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**5 success criteria are locked.** See `05-SPEC.md`.

**In scope:** Eval tuned vs raw · adapter swap · pitch artifact capture
**Out of scope:** Training itself (Phase 2) · UI changes (Phase 4) · pitch deck (Phase 6)

**Upstream constraints:**
- Phase 2 D-12: eval set is **50 hand-verified permits** (not 100). All accuracy numbers computed on 50.
- Phase 2 D-17: ≥ +15 pts overall schema-correct rate → swap.
- Phase 2 D-18: below +15 — graceful framing (revised here in D-44).

</spec_lock>

<decisions>
## Implementation Decisions

### Late-Training Handling
- **D-42:** **Use latest completed checkpoint.** If training isn't done at hour 22, take whatever epoch finished and eval it. ep1 or ep2 are valid candidates — don't wait for ep3.
- **D-43:** Hard deadline: if NO checkpoint exists at hour 23 (training failed), Phase 5 pivots immediately to the raw-Nano-local-serving pitch (per D-44). No silent waiting.

### Serving Path
- **D-45:** **Try NIM LoRA loading first.** Attempt `--lora-modules` on the Nano container. Budget: 30 min. If working: tuned Nano replaces raw Nano on `:8001`. Done.
- **D-46:** **Fallback: side-by-side vLLM.** If NIM LoRA loading doesn't work in 30 min, spin tuned Nano in vLLM on `:8011`. Ingestion pipeline routes to `:8011`. NIM `:8001` retains raw Nano (for A/B if needed). Memory cost: ~+18 GB; verify it fits with Super still loaded.
- **D-47:** Pipeline-side change is a single env var (`NORMALIZER_URL`). No code rewrite when port changes.

### Below-Bar Fallback (Lift < +15)
- **D-44:** **Pitch reframes to "Nemotron Super 49B running locally on this box, no internet."** Drop the training/lift slide entirely. The GX10 narrative anchors on **inference**, not training. This is the user's call — cleaner story than apologizing for a small lift.
- **D-48:** Loss curve and `nvidia-smi` screenshots are STILL captured even when the lift fallback fires — they go into a "speaker notes / Q&A" appendix slide. Judges who probe get answered honestly: "training ran 3 hours on this box, lift was preliminary, we kept raw Nano for the demo."

### Checkpoint Selection
- **D-49:** **Best by eval loss.** Compare ep1/ep2/ep3 on a 10-example dev subset (split off from training, never used for the 50-eval). Pick the checkpoint with lowest dev loss. Then eval that one on the 50.
- **D-50:** Dev subset is stratified the same way as the 50-eval (by `utility_owner` and `work_type`). Computed once during Phase 2 data prep.

### Claude's Discretion
- Eval script structure (HF `evaluate` lib vs custom scorer), batching strategy on the 50-eval, JSON output schema for `eval-report.json`, screenshot tooling, plot styling.

### Phase 5 Reduced — Fine-Tune Skipped Upstream (mid-execution amendment, 2026-05-30)
- **D-78:** **Phase 5 is reduced to a verification + capture step.** Per Phase 2 D-77, no LoRA was trained. There is nothing to evaluate and nothing to swap into NIM.
  - **What Phase 5 now does:**
    1. Verify Ollama `nemotron-3-super:latest` is responding on `:11434` (smoke test) — repeat the Phase 1 verification immediately before the demo as a sanity check.
    2. Capture `ollama show nemotron-3-super:latest` output → save as `ollama-modelfile.txt` for the pitch appendix.
    3. Take an `nvidia-smi` screenshot showing the 123B model resident in unified memory.
    4. Take a screenshot of one live chat round-trip latency (target: under 10s for the hot model).
  - **Pitch artifacts revised:** drop loss curve, drop side-by-side raw vs tuned. Replace with: model card + `nvidia-smi` showing 123B resident + measured inference latency.
  - **Phase 5 window reclaimed:** ~6 hours of person-time freed. Roll into Phase 6 polish.
  - **Q&A answer if probed:** "We evaluated multiple Nemotron variants on this hardware. The 123B Nemotron-3 Super running fully locally gave us reasoning quality the LoRA-Nano path wouldn't reach in 3 hours, so we used the pre-trained model. Fine-tuning is on the roadmap." Honest.

</decisions>

<canonical_refs>
## Canonical References

### Phase 5
- `.planning/phases/05-finetune-eval-swap/05-SPEC.md` — **Locked requirements.**

### Project-level
- `.planning/phases/02-finetune-kickoff/02-CONTEXT.md` — D-12 (50-eval), D-13 (synth quality controls), D-17/D-18 (swap bar)
- `.planning/PROJECT.md` — pitch arc (will be updated in Phase 6; this phase's pitch artifacts feed it)

### External docs
- NIM LoRA adapter docs — `docs.nvidia.com/nim/large-language-models/latest/multi-lora.html` (verify availability for Nano container)
- vLLM LoRA serving — `docs.vllm.ai/en/latest/models/lora.html`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `~/permitflow/checkpoints/nano-toronto-ep{1,2,3}/` — LoRA adapters from Phase 2
- `~/permitflow/data/eval-50.jsonl` — hand-verified eval set from Phase 2
- `~/permitflow/data/dev-10.jsonl` — checkpoint-selection dev subset (D-49/D-50)

### Established Patterns
- Single env var `NORMALIZER_URL` controls where ingestion sends normalization requests. Phase 1 wires it; Phase 5 flips it if swap happens.

### Integration Points
- Phase 5 re-ingests hero-block permits through the new normalizer. Output: `permits.tuned.geojson` next to `permits.geojson`. UI loads whichever is configured.

</code_context>

<specifics>
## Specific Ideas

- User chose the **honest fallback** path (D-44): if lift is weak, the pitch *re-anchors* on local inference rather than overselling the training result. This is a strong instinct — judges sniff overclaiming. Encode the alternative narrative in Phase 6 deck draft so it's ready to go.
- "Best by eval loss" (D-49) — user picked rigor over simplicity. Phase 5 must produce the dev-loss comparison plot too; it's a nice pitch-appendix slide.

</specifics>

<deferred>
## Deferred Ideas

- **Self-consistency / pass@k eval** — better methodology but not in scope. Pass@1 is the hackathon standard.
- **Per-permit error analysis** — useful for v2; not needed for the demo.
- **Adapter merging into base weights** — clean serving path but adds time. Defer to post-hackathon if NIM LoRA + vLLM both fail.

</deferred>

---

*Phase: 5-Fine-tune Eval & Swap*
*Context gathered: 2026-05-30*
