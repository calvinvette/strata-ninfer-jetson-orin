# Layer-25 owner-transition trace — Orin — 2026-10-20

This follow-up joined the all-layer dispatch-input/owner trace to the verifier
router, expert-part and shared/combined MoE captures at prompt-tail positions
505 and 506. It used the pinned Coder IQ1_M two-shard model from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and binary SHA256
`12012d9afe0d98ee110570ffa231a79db395597cca44e1cc445d8f2963866302`.
The randomized order was adaptive cap 8, then delayed control. Both arms ran a
same-service 512→2,048→512 short/long/recovery sequence, with no continuation.

In adaptive recovery at position 505, every captured layer input through layer
25 matched the initial short request. Layer-25 router IDs and weights were
identical. Expert 183 at rank 1 changed from CPU (`route_kind=-1`) to GPU
(`route_kind=0`). Its input vector was bit-identical, but all 2,560 output
values changed (maximum absolute difference 0.00132074; relative L2 1.2575%).
The shared-expert output was bit-identical; the combined MoE vector differed
in all 2,560 values (maximum absolute difference 0.00021524; relative L2
0.5382%). Position 506 had no layer-25 owner flip and all captured MoE output
sections matched.

An independent same-input `native_expert_parity` run for layer 25 expert 183
(IQ3_S gate/up, IQ4_NL down) matched the captured initial CPU output and
recovery GPU output bit-for-bit. Against its GGML-decoded float reference, the
CPU and GPU outputs had relative-L2 errors of 1.1555% and 1.1112%; their
CPU-to-GPU relative-L2 difference was 1.2575%. This confirms the changed
service row follows the selected execution owner on this exact input. It does
not establish a quality threshold or show that every adaptive migration has
the same effect.

The captured position-505 layer-26 activation is the first differing MoE input
in this sequence, after the layer-25 combined-output difference. At position
506, layer-26 GDN `x` and `qkv` match, while its convolved `h` differs; this is
consistent with the preceding row changing recurrent carry. The trace therefore
ties the first observed adaptive divergence to the layer-25 CPU/GPU owner
transition for this row, while accepted-prefix GDN state still differs in five
fields after recovery. Completion IDs match across the initial and recovery
short requests in both arms. Delayed control is bit-identical across owners,
routes, activations and captured layer-25 outputs at positions 505 and 506.

Both supervised runs passed with `MemoryMax=28G`: adaptive cap 8 took 186.08 s
with 14.17 GiB minimum host/admission availability; delayed control took
184.54 s with 14.31 GiB. Both retained at least six GiB headroom, and every
sampled cgroup low/high/max/OOM/OOM-kill counter remained zero. Clocks were
dynamic; energy was not process-attributed. These are correctness-localization
runs, not performance confirmation.

Reproduce the paired capture, per-layer analysis and verifier-output analysis
from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --continuations 0 --capture-moe-positions 505,506 \
  --capture-verify-moe-layer 25 --verify-moe-positions 505,506 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-owner-position505-506

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_layer25_owner_positions.py \
  --run bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-owner-position505-506 \
  --positions 505 506 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-owner-position505-506/owner-analysis.json
```

The exact captured operator inputs, CPU/GPU/reference outputs, parity command
and output comparison are retained under `operator-checks/expert183/` and
`operator-comparison.json`. Raw model files remain under `~/models/`.
