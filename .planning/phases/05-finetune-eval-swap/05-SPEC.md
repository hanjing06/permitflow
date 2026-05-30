# Phase 5 — Fine-tune Eval & Swap

**Window:** Hour 22–28
**Owner:** ML

## Goal

Turn the LoRA checkpoint from Phase 2 into a quantifiable win and a live demo upgrade. The pitch slide says: *"Raw Nemotron Nano gets N% of permits' canonical schema right. After 3 hours of LoRA training on a GX10, our tuned Nano gets M%."* You need real M and N.

## Tasks

### A — Eval the tuned vs raw Nano
- [ ] Load `~/permitflow/data/eval-100.jsonl` (untouched since Phase 2)
- [ ] Run raw Nemotron Nano 9B over all 100 examples → record predicted JSON
- [ ] Run LoRA-tuned Nano (best-epoch checkpoint) over all 100 → record predicted JSON
- [ ] Score each prediction per field:
  - Categorical fields (`work_type`, `lanes_affected`, `depth_class`, `utility_owner`): exact match
  - `expected_duration_days`: within ±20% of label
- [ ] Compute per-field accuracy + overall schema-correct rate (all fields right)
- [ ] Target lift: ≥ +20 points on overall schema-correct rate
- [ ] Write `eval-report.json` and a one-page chart for the pitch deck

### B — Swap into pipeline
- [ ] Reload NIM Nemotron Nano with the LoRA adapter mounted (use NIM's adapter-loading flag or stop/start with `--lora` path)
- [ ] Smoke test on 5 fresh permits not in train or eval — confirm tuned outputs look canonical
- [ ] Re-run the ingestion job for the hero neighbourhood with the tuned Nano so the demo data benefits from it
- [ ] Verify no regression in downstream optimizer (cluster counts should be same or better)

### C — Capture artifacts for the pitch
- [ ] Screenshot of `nvidia-smi` during training (proves real GX10 utilization)
- [ ] Loss curve plot (saved in Phase 2)
- [ ] Side-by-side: 3 examples where tuned Nano correctly normalizes a permit that raw Nano got wrong — this is your most persuasive single slide
- [ ] One sentence with the headline number for the pitch script: *"3 hours of LoRA on the GX10 took us from N% to M% on schema extraction."*

## Exit criteria

By end of hour 28:

1. `eval-report.json` exists with concrete numbers
2. Lift is ≥ +15 points (≥ +20 ideal)
3. Tuned Nano is the one running in the NIM container during the demo
4. Hero-neighbourhood data has been re-normalized with the tuned model
5. Pitch artifacts (loss curve, side-by-side examples, headline number) are saved to `.planning/phases/05-finetune-eval-swap/artifacts/`

## Risks

| Risk | Mitigation |
|---|---|
| Tuned model worse than raw (overfit on noisy synth labels) | Use earlier checkpoint (ep1 or ep2). If still worse, revert to raw Nano and reframe the slide as "future work — preliminary lift in early epochs" |
| Adapter loading in NIM unsupported | Run tuned Nano via vLLM on a different port; route ingestion calls there |
| Re-ingestion breaks Phase 4 data | Keep raw-normalized data as fallback `permits.raw.geojson`; UI can swap if needed |
| Lift exists but isn't dramatic | Pick the most flattering field (usually `utility_owner` — small vocab, easy lift) and lead the slide with that |

## Deliverables to Phase 6

- Headline number for the slide
- Side-by-side examples
- Tuned Nano live in pipeline
