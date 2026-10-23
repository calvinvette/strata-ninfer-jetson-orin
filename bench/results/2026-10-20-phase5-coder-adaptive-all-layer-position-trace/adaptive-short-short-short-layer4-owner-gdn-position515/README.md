# Earliest position-515 owner change: layer 4 — Orin — 2026-10-20

The full position-515 dispatch trace showed that layer 4 is the earliest owner
change across the initial and recovery short requests: expert 153 moves from
CPU to VRAM while activation, expert IDs, and router weights match. Layer 16
has a second owner change for experts 118 and 39; the first selected activation
difference appears at layer 18.

A mode-matched standalone `native_expert_parity` run used the pinned Coder IQ1_M
shards from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and
`STRATA_NATIVE_CPU_Q8_1_DOT=all`. The directly captured CPU-pool row for expert
153 matched the same-input CPU oracle within maximum absolute difference
5.0e-11 (relative L2 1.21e-9). The CPU and CUDA oracle rows were bit-identical,
so the weighted contribution changes by zero across this owner transition.

At this same position, every captured layer-4 verifier GDN intermediate and
raw pre/post state was bit-identical across all three requests. Those GDN
captures come from the separate CUDA verifier path; they are not a record of the
CPU pool's combined mixed-owner result. Therefore the earliest owner change
alone does not show a numeric operator delta in expert 153, and this evidence
does not establish the cause of the downstream state difference. The remaining
layer-16 expert-118 result is a small measured CPU/GPU difference and is a
later candidate boundary, not yet an isolated causal intervention.

The supervised service run passed with 14.23 GiB minimum host/admission
availability; the standalone oracle passed with 24.51 GiB. No energy or
performance claim is made. Raw service, state, intermediate and oracle captures
are retained here. See `layer4-owner-gdn-analysis.json` for compact comparisons.

Reproduction used `run_one.py` with short/short/short, 12 generated tokens,
`--capture-moe-positions 515`, CPU output layer 4 / dispatch 340 / position
515, and verifier MoE, GDN intermediate and GDN state captures at layer 4,
position 515. The independent oracle command is the expert-118 command in the
layer-16 sibling report, changed to `--expert 153`, the captured layer-4 input,
and model layer `4`.

The raw post-state hash for all three position-515 records also matches the
service's GDN ordinal-3 hash (`2f8e630252f9f8d8`), as retained in
`service-hash-crosscheck.json`.
