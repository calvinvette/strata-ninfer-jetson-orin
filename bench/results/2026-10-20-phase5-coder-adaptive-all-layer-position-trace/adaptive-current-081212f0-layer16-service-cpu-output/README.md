# Current-source layer-16 service CPU rows — Orin — 2026-10-20

This randomized short/long/short pair used current candidate binary
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`, the
pinned Coder IQ1_M snapshot, and `STRATA_NATIVE_CPU_Q8_1_DOT=all`. It captured
CPU expert rows at layer 16, dispatch 352, token position 515. Each arm passed
all three eight-token requests under `MemoryMax=28G`.

The initial short request matched the separate position-515 all-layer capture:
all eight emitted token IDs and accepted state fingerprints at positions
511–518 were identical. That run provides the exact saved layer-16 activation
used by the same-input CPU/CUDA oracles below.

The initial short request routed experts 118 and 39 through the service CPU
pool in both arms. Their captured service rows are bit-identical to independent
CPU oracle outputs on the same activation. At the exact same activation,
expert 118's CPU and CUDA oracle outputs differ in all 2,560 values (relative
L2 `1.35199e-4`, maximum absolute difference `1.21295e-5`); expert 39's CPU and
CUDA outputs match bit-for-bit. Both oracle rows reproduce the previous
same-input oracle outputs bit-for-bit. On adaptive recovery at the same
position, the separate [position-515 all-layer trace](../adaptive-current-081212f0-position515/README.md)
shows both experts move from CPU ownership to VRAM ownership, while the
layer-16 dispatch input and expert IDs remain identical. Expert 118 is a
measured owner-dependent numerical contributor at this position. It is
consistent with the already-observed
layer-17 `x` and recurrent-state change, but the pair does not directly capture
the recovered CUDA owner rows or prove the complete combined-output delta.

Both supervised services passed with zero cgroup memory events; minimum
host/admission availability was 14.39 GiB for adaptive and 14.25 GiB for
delayed control. This is a single correctness diagnostic, not an accuracy,
quality or performance claim. The raw CPU rows and per-row CPU/CUDA oracle
comparison are in `*/result/cpu-moe-outputs.jsonl` and
`service-owner-analysis.json`; the exact-input oracle outputs and their
supervisor records are in the sibling [layer-17 follow-up](../adaptive-current-081212f0-layer17-position515/).

Reproduce with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261035 --sequence short-long-short --continuations 0 \
  --generated-tokens 8 --native-cpu-q8-1-dot all \
  --capture-cpu-output-layer 16 --capture-cpu-output-dispatch 352 \
  --capture-cpu-output-position 515 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer16-service-cpu-output
```

Phase 5 remains open; broader state-transaction, KV, cancellation, graph-life,
and MTP gates remain to be completed.
