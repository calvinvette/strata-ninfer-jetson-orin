# Direct layer-16 CPU-owner output capture — Orin — 2026-10-20

This follow-up captures the actual CPU expert-pool row at layer 16, position
515, during the adaptive short/short/short request sequence. It was needed
to identify the CPU-produced row directly. `verify-moe-parts.bin` is the
verifier's assembled per-expert buffer after CPU rows are copied and GPU-hit
rows are added; paired with the route trace it can identify the same row.

The test used the pinned Coder IQ1_M model from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. Expert 118 (IQ3_XXS/IQ4_NL) was
CPU-owned (`route_kind=-1`) on dispatch 352. The selected activation, routed
expert IDs, and router weights matched across the three requests. The captured
CPU owner row repeated bit-for-bit on a separate run.

The first standalone oracle comparison used its default CPU arithmetic mode,
while the service used `STRATA_NATIVE_CPU_Q8_1_DOT=all`; that comparison is
retained as a mode control, not a service comparison. A mode-matched oracle
rerun made the direct CPU pool row agree with the independent CPU result to a
maximum absolute difference of 5.0e-11 and relative L2 9.51e-10. The same-input
Q8_1 CPU and CUDA oracle outputs differ by 0.01352% relative L2 for expert 118.
The second migrating expert, 39, has bit-identical CPU and CUDA oracle rows.
The [same-service cross-check](../adaptive-generated-position512-layer40-expert114-mirror-state-pair/README.md#verifier-parts-capture-semantics-cross-check)
shows that direct CPU rows also appear in the verifier-parts buffer within its
JSON serialization precision. This validates the selected expert output for
this input and mode; it does not explain the later GDN state divergence or make
a performance claim.

The position-aware CPU-capture validation was added to `run_one.py`; the
default required position remains 511. The first capture run retained the
right dispatch row but returned failure because the validator was hard-coded
to position 511. The validated repeat passed under the 28-GiB supervisor with
14.25 GiB minimum host and admission availability. The original initial to
recovery state difference at layer-17 position 515 is retained in the
[combined state/oracle capture](../adaptive-short-short-short-layer16-owner-layer17-state-position515/README.md).

Reproduce the direct capture with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-short-short-short-layer16-cpu-owner-output-position515-validated/supervisor \
  --timeout 1200 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_one.py \
  --adapt-every 4 --adapt-swaps 8 --continuations 0 --generated-tokens 12 \
  --sequence short-short-short --native-cpu-q8-1-dot all \
  --capture-moe-positions 515 --capture-cpu-output-layer 16 \
  --capture-cpu-output-dispatch 352 --capture-cpu-output-position 515 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-short-short-short-layer16-cpu-owner-output-position515-validated/result
```

The direct capture, mode-matched and default-mode CPU/GPU oracle files,
comparison JSON, raw supervisor samples, and initial failed validator run are
retained here.
Phase 5 remains open.
