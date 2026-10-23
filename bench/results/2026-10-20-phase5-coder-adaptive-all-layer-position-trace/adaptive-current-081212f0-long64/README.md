# Current-source adaptive accepted-prefix follow-up — Orin — 2026-10-20

This randomized, supervised correctness pair used the current candidate binary
(`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`) from
checkout `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`. Both arms loaded the pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` snapshot
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. The workload was
short-512 → long-2048 → short-512, with 64 generated tokens per request,
zero explicit continuations, and `STRATA_NATIVE_CPU_Q8_1_DOT=all`. The adaptive
arm used the cap-8 policy; the control delayed swaps. `MemoryMax=28G` applied
to each process. This is one state-correctness diagnostic, not a timing or
quality comparison.

Both arms completed all three requests and passed supervision. Delayed control
reproduced all 64 accepted-prefix state fingerprints and token IDs between the
initial and recovery short requests. Adaptive recovery differed from its
initial short request at 40/64 token IDs, first at output index 23 (accepted
position 534). Its committed-state fingerprints first differed at zero-based
prefix index 4 (accepted position 515) and differed at 60/64 prefixes. At that
first changed prefix, GDN hash ordinals 13–35 differed. The state divergence
therefore precedes the first output-token divergence; this pair does not
identify the numerical cause.

Across adaptive and delayed-control arms, the initial short request returned
identical token IDs, though its state hashes differed in 34/64 prefixes,
starting at index 30. The long request differed in 62/64 states (first at index
2) and 31/64 token IDs (first at index 20). Recovery differed in 60/64 states
(first at index 4) and 40/64 token IDs (first at index 23). These cross-arm
differences are consistent with the owner-policy treatments changing runtime
state and output; the pair does not establish output quality or isolate a
specific operation.

The 28-GiB supervisors reported minimum host/admission availability of 13.97
GiB for adaptive and 14.34 GiB for delayed control. Both returned zero; inspect
the raw `supervisor/result.json`, memory samples and tegrastats logs for the
full records. The accepted-prefix parser preserves the service's ordering of
`STATE_HASH_GDN`, `STATE_HASH_QSA_LAYERS`, and `ACCEPTED_PREFIX` records; the
machine-readable comparison is `accepted-prefix-analysis.json`.

Reproduce the pair from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261032 --sequence short-long-short --continuations 0 \
  --generated-tokens 64 --native-cpu-q8-1-dot all \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-long64

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/analyze_trace.py \
  --run bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-long64 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-long64/accepted-prefix-analysis.json
```

This remains one model, prompt sequence and pair. It does not close Phase 5 or
qualify adaptive migration across workloads, quantizations or speculation
windows.
