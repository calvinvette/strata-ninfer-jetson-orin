# Layer-4 verifier and accepted-state capture at position 511 — Orin — 2026-10-20

This randomized same-service pair used the pinned Coder IQ1_M model, Hugging Face revision `5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256 `6e4b89f7d0979dd0d16eb000c238aa837d5c990dbe54033dada9a479a93fcd38`. Both arms enabled the opt-in CPU Q8_1 mirror only for `iq2_s/q2_0@layer=1`; order was adaptive then delayed control. Both processed identical 512-token, 2,048-token, and same-service 512-token recovery prompts and returned identical 12-token outputs in each request. Delayed control's terminal fingerprints match; adaptive recovery differs in `gdn`, `tail`, `pooled`, `pooled_full`, and `kv`.

At model layer 4, position 511, delayed-control verifier routes, router weights, expert rows, combined MoE output, GDN intermediates, and raw pre/post state are bit-identical between initial and recovery requests. Adaptive initial and recovery use the same ten expert IDs, but router weights differ and all 25,600 expert-hit values differ (relative L2 `0.014705`); all 2,560 combined MoE outputs differ. Layer-4 GDN field `x` is the first changed intermediate, with all 2,560 values differing (relative L2 `0.00289145`).

The layer-4 pre-state already differs in adaptive recovery: 786,414/786,432 recurrent values and 20,480/30,720 convolution-history values differ (relative L2 `0.00120604` and `0.00157143`). The post-state differs in 786,419 recurrent values and the same 20,480 convolution values (relative L2 `0.00120925` and `0.00255207`). The committed-state capture at endpoint 511 cross-checks against the service's GDN ordinal-3 hash. Adaptive initial committed state matches delayed initial bit-for-bit; delayed initial/recovery remain exact. Adaptive recovery is the only differing state. Thus layer 4 is a confirmed persistent-state boundary, but its pre-state and `x` show that the discrepancy is already present on entry to this captured row. The prior layer-3 transition is the next target; this report does not claim a causal operation yet.

Both runs passed supervision. Minimum host/admission availability was 14.21 GiB for adaptive and 14.33 GiB for delayed control; maximum scope use was 10.53 and 10.34 GiB, with zero sampled `high`, `max`, `oom`, and `oom_kill` events. This is correctness evidence for one model/workload, not a performance or migration qualification.

Reproduce from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261048 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1' \
  --capture-moe-positions 511 \
  --capture-verify-moe-layer 4 --verify-moe-positions 511 \
  --capture-verify-gdn-layer 4 --verify-gdn-positions 511 \
  --capture-verify-gdn-state-layer 4 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 4 --gdn-commit-state-positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer4-generated-position511-verifier-pair
```

All-layer dispatch, verifier route/parts/output, GDN intermediate and raw state captures, service logs, comparator outputs, and supervisor telemetry are retained beside this report.
