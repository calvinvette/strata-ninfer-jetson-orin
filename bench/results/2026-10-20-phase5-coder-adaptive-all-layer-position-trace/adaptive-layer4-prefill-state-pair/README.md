# Layer-4 prefill and position-511 dispatch trace — Orin — 2026-10-20

This randomized same-service pair used the pinned Coder IQ1_M model (Hugging Face revision `5348543e0147355ac9cbcb031184a3546350988e`) and candidate binary SHA256 `6e4b89f7d0979dd0d16eb000c238aa837d5c990dbe54033dada9a479a93fcd38`. Both arms enabled the CPU Q8_1 mirror only for `iq2_s/q2_0@layer=1`; the arm order was adaptive then delayed control. Each service processed short 512-token, long 2,048-token, and same-service recovery short prompts, generating 12 tokens per request.

At model layer 4 (GDN ordinal 3), prefill trace hashes matched at every chunk boundary for the repeated 505-token raw prompt. The raw end-of-prompt recurrent and convolution states were bit-identical between the adaptive initial and recovery requests. Delayed control also matched every boundary and its raw end state. This rules out a difference in layer-4 prefill state for this pair.

The per-GDN service-hash trace still diverged in adaptive recovery at endpoint 511, beginning at ordinal 3/model layer 4 and affecting 33 of 36 GDN hashes. Delayed control remained exact through endpoint 522. The all-layer dispatch capture at position 511 shows the first changed activation at layer 4 in the adaptive arm, while delayed control is exact; the owner trace changes at layers 1, 3, 6, 8–13, 15–19, 22–24, 26–34, 36, 37, 39, 42, 43 and 46. This moves the first observed difference out of prefill and into the decode path at layer 4, but does not identify the exact calculation. A separate direct layer-4 verifier and raw-state capture at position 511 is underway.

Both supervised runs passed. Minimum host/admission availability was 14.19 GiB for adaptive and 14.24 GiB for delayed control. Maximum scope use was 10.89 and 10.48 GiB, with zero sampled `high`, `max`, `oom`, and `oom_kill` events. No performance comparison was made.

Reproduce from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261047 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1' \
  --capture-moe-positions 511 --trace-prefill-gdn-state-layer 4 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer4-prefill-state-pair

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_prefill_gdn_state_pair.py \
  --service-log bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer4-prefill-state-pair/adaptive-cap8/result/service.log \
  --state-dump bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer4-prefill-state-pair/adaptive-cap8/result/prefill-gdn-state.bin \
  --layer 4 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer4-prefill-state-pair/adaptive-cap8/prefill-gdn-analysis.json
```

Raw service logs, per-chunk hashes, full end states, dispatch rows and supervisor telemetry are retained beside this report. The position-511 dispatch comparison pairs first and last records and includes the observed record counts. The direct verifier-state capture is tracked separately.
