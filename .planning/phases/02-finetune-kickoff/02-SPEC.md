# Phase 2 — Fine-tune Kickoff

**Window:** Hour 4–6
**Owner:** ML
**Runs in background through Phases 3 and 4**

## Goal

Kick off a LoRA fine-tune of Nemotron Nano 9B v2 that turns messy Toronto utility-cut permit free-text into a canonical JSON schema. The actual training runs unattended for ~2–3 hours, completing in time for Phase 5 evaluation.

This phase is what justifies the GX10 being part of the project. The artifact must exist by hour 24 for the pitch slide to be true.

## Task definition

**Input:** raw permit `description` field, plus structured fields where present (start_date, end_date, applicant, street).

**Output:** canonical JSON:

```json
{
  "work_type": "watermain_replacement | hydro_pull | gas_main | fibre_pull | sewer_repair | road_resurfacing | other",
  "lanes_affected": "none | shoulder | one_lane | multi_lane | full_closure",
  "depth_class": "surface | shallow_cut | deep_excavation",
  "expected_duration_days": <int>,
  "utility_owner": "toronto_water | toronto_hydro | bell | rogers | enbridge | city_transportation | other"
}
```

## Tasks

- [ ] Hand-label 200 examples from the Utility Cut Permits dataset (split across the team during Phase 1; each person owns 50)
- [ ] Generate 600 synthetic labels by prompting Nemotron Super 49B with the schema + few-shot examples; spot-check 10% and accept the rest
- [ ] 90/10 train/eval split → freeze the eval set; never look at it during training
- [ ] LoRA config: r=16, alpha=32, dropout=0.05, target modules = q_proj, k_proj, v_proj, o_proj
- [ ] Trainer: 3 epochs, batch 4, gradient accumulation 4, lr 2e-4 with cosine schedule
- [ ] Use HuggingFace PEFT + TRL `SFTTrainer`, bf16
- [ ] Launch training detached (`tmux` or `nohup`) so it survives terminal close
- [ ] Log loss curves to a local file you can screenshot for the pitch deck
- [ ] Save checkpoints every epoch to `~/permitflow/checkpoints/nano-toronto-ep{n}`

## Exit criteria

By end of hour 6:

1. Training process is running on GX10 (`ps` confirms, GPU util > 0)
2. Loss has decreased measurably from step 0 to step ~100
3. Held-out eval set exists at `~/permitflow/data/eval-100.jsonl` and is untouched

## Risks

| Risk | Mitigation |
|---|---|
| Training OOMs alongside NIM serving | Pause Nemotron Super NIM during training; restart for Phase 5. Phase 3/4 only need Nano + embedder + OSRM during this window. |
| Synthetic labels too noisy | Manually verify a higher % (25%) or reduce synth count to 300 |
| Training diverges | Drop lr to 1e-4, restart. Don't sink more than 30 min into recovery — fall back to raw Nano. |
| Schema too ambitious | Drop `depth_class` and `expected_duration_days` first — they're the noisiest fields |

## Deliverables to Phase 5

- Trained LoRA adapter at `~/permitflow/checkpoints/nano-toronto-ep3/`
- Eval set at `~/permitflow/data/eval-100.jsonl`
- Loss curve plot for the pitch deck
