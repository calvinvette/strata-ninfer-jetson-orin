# Layer-3 expert-87 owner change at decode position 511 — Orin — 2026-10-20

This randomized delayed/adaptive pair used the pinned Coder IQ1_M model (revision `5348543e0147355ac9cbcb031184a3546350988e`) and candidate binary SHA256 `6e4b89f7d0979dd0d16eb000c238aa837d5c990dbe54033dada9a479a93fcd38`. It enabled the opt-in Q8_1 arithmetic mirror only for `iq2_s/q2_0@layer=1`; order was adaptive then delayed control. Both arms returned the same 12 output token IDs for the 512-token short, 2,048-token long and same-service recovery short requests. Delayed terminal fingerprints were exact; adaptive recovery terminal fingerprints differed in `gdn`, `tail`, `pooled`, `pooled_full`, and `kv`.

At layer 3, position 511, initial and recovery requests have identical router IDs and weights and a bit-identical input activation. Expert 87 is the only routed contribution that changes: its ownership switches from CPU to GPU in adaptive recovery; all other nine expert rows are bit-identical. The combined layer-3 MoE output changes in 2,560/2,560 values (relative L2 `0.00442521`), and expert 87's row differs at relative L2 `0.01431965`. Delayed control has identical route, owner and expert rows.

An independent native CPU/GPU expert harness used the captured layer-3 activation (SHA256 `08ae55595ff07731cfe8ff754ba5edc2ca3b6fcbf4b9cf0c88c8f87a84f7d680`). Its CPU output matches the initial adaptive and both delayed rows exactly; its GPU output matches adaptive recovery exactly. This establishes same-input CPU/GPU expert arithmetic as the direct source of the changed layer-3 row. With the layer-1-only mirror, the following layer-4 GDN input `x` already differs, and its accepted commit state diverges; the layer-4 raw commit hash matches the service's GDN ordinal-3 hash.

The same native harness with `iq2_s/iq4_nl@layer=3` enabled produced bit-identical CPU and GPU outputs for expert 87 (0/7,680 float words differ). This suggests a combined layer-1 plus layer-3 mirror test. Because the selector previously accepted only one rule, the Q8_1 selector now accepts comma-separated pair/layer rules; its CTest contract covers exact layer and quant-pair matches, and rejects a trailing empty rule. Candidate rebuild and the one-test selector CTest passed, as did the 163-test integration Python suite. This is diagnostic correctness evidence only; the Q8_1 rules remain opt-in, and no performance or model-quality claim follows.

Both service runs passed supervision. Minimum host/admission availability was 14.23 GiB for adaptive and 14.23 GiB for delayed control; maximum scope use was 10.61 and 10.52 GiB, with zero sampled `high`, `max`, `oom`, and `oom_kill` events.

Reproduce the service pair with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261049 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1' \
  --capture-moe-positions 511 \
  --capture-verify-moe-layer 3 --verify-moe-positions 511 \
  --capture-verify-gdn-layer 4 --verify-gdn-positions 511 \
  --capture-verify-gdn-state-layer 4 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 4 --gdn-commit-state-positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer3-generated-position511-verifier-pair
```

For the independent operator oracle, first extract the initial layer-3 activation from `adaptive-cap8/result/all-layer-position511.jsonl` into the distinct file `expert87-oracle/layer-3-expert-87-service-activation.f32`, then run:

```sh
STRATA_EXP_MODE=0 build/integration/candidate/native_expert_parity \
  "$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf" \
  --expert 87 \
  --activation-f32 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer3-generated-position511-verifier-pair/expert87-oracle/layer-3-expert-87-service-activation.f32 \
  --dump-f32-dir bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer3-generated-position511-verifier-pair/expert87-oracle 3

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-layer1-verifier-pair/compare_owner_oracle.py \
  --root bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer3-generated-position511-verifier-pair \
  --layer 3 --position 511 --experts 87 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer3-generated-position511-verifier-pair/owner-oracle-analysis.json
```

The retained `layer-3-expert-87-service-activation.f32` is the one-row service input. Keep the input path separate from `--dump-f32-dir`: the harness writes an output activation file with its own standard filename. All service and oracle outputs, comparisons, raw captures and telemetry are retained beside this report.
