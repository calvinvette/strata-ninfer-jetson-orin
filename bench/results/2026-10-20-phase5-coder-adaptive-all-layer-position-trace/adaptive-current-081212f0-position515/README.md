# Current-source position-515 dispatch trace — Orin — 2026-10-20

This randomized, supervised correctness pair used the same current candidate
binary and pinned Coder IQ1_M model as the [64-token follow-up](../adaptive-current-081212f0-long64/README.md).
It repeated short-512 → long-2048 → short-512 with eight generated tokens per
request and captured all-layer verifier dispatch at accepted position 515.
The capture retains the initial-short and recovery-short rows; delayed control
used cap-8 adaptive swapping disabled. Both arms used `STRATA_NATIVE_CPU_Q8_1_DOT=all`
and `MemoryMax=28G`.

Delayed control matched all eight tokens, state fingerprints, per-GDN hashes,
and valid all-layer dispatch activations, expert IDs and owners between its
initial and recovery short requests. Adaptive recovery also returned the same
eight tokens, but state first differed at prefix index 4 (position 515); four
of eight committed-prefix states differed. The first changed per-GDN fingerprint
was ordinal 13, which maps to model layer 17 for the model's QSA interval of
four. The all-layer CPU activation capture is invalid at layer 17 in both
requests, so it cannot compare the layer-17 dispatch input directly. The first
valid changed captured dispatch input is at layer 18: all 2,560 values differ,
relative L2 is `0.0035630`, and maximum absolute difference is `0.0102571`.
Layer-18 expert IDs and owners still match. The activation difference is
therefore visible after the first changed committed GDN fingerprint, but this
capture does not establish which operation first changed its input or state.

Adaptive owner placement changed at layers 9 and 16 before layer 18, among
other later layers. Those observations do not prove which owner transition
caused the layer-17 state difference. A raw layer-17 verifier state and
intermediate capture at position 515 is the next localization step. Both
supervisors passed with zero cgroup memory events; minimum host/admission
availability was 14.35 GiB for adaptive and 14.27 GiB for delayed control.
This is a single correctness pair, with no performance or quality claim.

The exact accepted-prefix and all-layer comparison is in
`all-layer-analysis.json`; raw route rows, service logs, requests and supervisor
telemetry are retained in the arm directories. Reproduce with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261033 --sequence short-long-short --continuations 0 \
  --generated-tokens 8 --native-cpu-q8-1-dot all \
  --capture-moe-positions 515 --capture-moe-rows 96 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-position515

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/analyze_trace.py \
  --run bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-position515 \
  --capture-position 515 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-position515/all-layer-analysis.json
```

This does not close Phase 5 or establish a general accepted-state drift bound.
