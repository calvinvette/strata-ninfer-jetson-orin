# Coder exp2f two-live layer-11 owner boundary

Date: 2026-10-24. Correctness diagnostic on Jetson AGX Orin (ARM64, CUDA
12.6), using the Coder IQ1_M model from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. The same temporary exp2f profile
and two-live workload were used for serial controls and batch capture. This is
not a performance result or a Phase 5 closeout.

## Result

The batch runner assigned the two requests to physical slots in reverse order
from their serial-control indices. Pairing by slot number alone gives false
large deltas. The capture's per-layer hash mapping and exact token sequence
identify batch slot 0 as serial control 1 (prompt 1), and batch slot 1 as
serial control 0. All comparisons below use that mapping.

For prompt 1, layer-10 GDN stage fields matched serial at positions 87 (token
13769) and 88 (token 3010). At layer 11 / position 87, routes, activation,
all ten expert parts and combined MoE output also matched bitwise despite
several owner changes. At position 88, routes and the full 2,560-float MoE
input activation still matched exactly. Expert 114 (rank 6) moved from GPU to
CPU; it was the only expert part that changed. Its service output changed in
all 2,560 values (maximum absolute `2.74256e-5`, relative L2 `4.12504e-4`),
and the combined MoE output changed in all values (maximum absolute
`1.68383e-6`, relative L2 `6.80979e-5`).

The independent `native_expert_parity` replay used the captured activation
(SHA256 `be8dbce409654ca63e8724efa2c2e0852a280e22a639ebc3816268419735147d`)
and exact layer-11/expert-114 model weights. Serial service output matched
the GPU oracle bitwise; batch service output matched the CPU oracle bitwise.
The CPU and GPU oracle outputs differed in all values (maximum absolute
`2.74256e-5`, relative L2 `4.12515e-4`). The oracle's independent float
reference, weight decode checks, and width-invariance checks passed. This
isolates the captured part difference to the owner-specific CPU/GPU arithmetic
for this activation and expert.

A prior separate same-profile boundary capture at position 88 found the first layer
12 stage difference in its input `x` (2,554/2,560 values, relative L2
`2.36056e-5`), followed by changed layer-12 committed GDN state (782,395 /
817,152 values, relative L2 `9.27875e-5`). Together with the exact layer-10
fields and same-input layer-11 expert oracle above, this is consistent with
the layer-11 owner delta entering layer 12. These were separate captures, so
they do not prove the entire causal path in one execution. It is one prompt
pair and one position; it does not establish quality impact, a bound on later
state drift, or a general CPU/GPU preference. The 32-token batch and serial
outputs in the QSA follow-up were exact, but that does not establish long-chain
state parity.

## Same-run boundary replication

A final supervised capture recorded layer-10 stages, layer-11 routes/parts,
and every GDN commit state together at positions 86, 87 and 88. Its hash and
token-sequence mapping was batch slot 0 → serial control 0 and batch slot 1 →
serial control 1; both requests emitted 32/32 tokens identical to their
serial controls. For prompt 1 / batch slot 1, every captured GDN layer state
was bit-identical at positions 86 and 87. At position 88, layer 12 was the
first changed state (782,395/817,152 values; relative L2 `9.27875e-5`),
followed by later GDN layers. Layer-10 fields were bit-identical at positions
87 and 88. Layer-11 routes, input activation and all expert parts/output were
bit-identical at position 87. At position 88, routes and activation remained
bit-identical; expert 114 GPU→CPU was the only changed part, with relative L2
`4.12504e-4`, and the combined MoE output changed at relative L2
`6.80979e-5`.

The independent parity replay on the exact position-88 activation (same SHA256
as above) again matched serial service to the GPU oracle and batch service to
the CPU oracle bitwise. The one-run boundary brackets the first observed
state change between positions 87 and 88, immediately after the position-88
owner-specific MoE delta. This strongly localizes the sampled state movement
to that boundary. It does not establish long-chain drift bounds, quality
impact, other owner transitions, or general parity. The capture completed in
207.4 seconds with 17.71 GiB minimum available physical memory and zero cgroup
pressure/OOM events; GPU clocks were observed dynamically, EMC readback was
denied, and energy was not analyzed.

An offline operator replay on this exact activation checked a possible host
exp2f-SiLU correction. CPU/CUDA Q8_1 activation and IQ2_S gate/up outputs
matched bitwise, and CPU IQ4_NL down on the CUDA hidden Q8_1 values reproduced
the grouped CUDA result bitwise. The ordinary CPU hidden quantization differed
from CUDA in 3/60 blocks (three code bytes; no scale or sum-byte differences).
Independent host `expf` and host `exp2f` quantizer probes both missed the same
CUDA blocks (11, 31 and 51). The parity harness's host-exp2f candidate still
differed in all 7,680 down-output words (relative L2 `4.13e-4`). This
one-sample result does not justify enabling exp2f for expert 114.

The Orin runtime and parity binaries were SHA256
`ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df` and
`70ef263ef83cf4d492c18c35561827ccd08ab663a91c1bd4681fed02f327eff5`.
The parity source revision was `4b324ade`; the temporary expert profile SHA256
was `1f03ed71cdac371e07480a3b4473e93be5cdfc9afb910f2fdac8491ac555502e`.
Model shards remain in `~/models/`.

The supervised batch capture passed its six-GiB physical-memory guard and
retained 17.70 GiB minimum available physical memory, with zero sampled cgroup
pressure/OOM events. The supervised oracle passed in 1.07 seconds and retained
24.48 GiB minimum availability. GPU clocks were observed dynamically; EMC
readback and energy analysis were unavailable. No clocks or services were
changed.

## Reproduction and retained evidence

The raw capture and full oracle dumps remain local and ignored. Compact paired
analyses are `stage10-slot0-prompt1-position-{87,88}.json`,
`moe11-slot0-prompt1-position-{87,88}.json`, and the supervisor records under
this directory. The final one-run paired analyses are `final-stage10-slot1-`,
`final-moe11-slot1-`, and `final-state-slot1-` for positions 86–88; the source
capture is `capture-final-boundary-86-87-88/`.

The activation can be extracted from batch owner row 0 at layer 11 / position
88 / token 3010 in `capture/batch.owners.jsonl`. Run the parity tool under
`tools/integration/run_control.py` with that raw 2,560-float activation,
`STRATA_NATIVE_CPU_Q8_1_DOT=all`, the Coder IQ1_M shard containing layer 11,
`--expert 114`, and layer argument `11`. Compare the captured rank-6 expert
part from `serial-slot-1.parts.stmparts` and `batch.parts.stmparts` against
`layer-11-expert-114-gpu-output.f32` and
`layer-11-expert-114-cpu-output.f32` respectively.

Phase 5 remains open for accepted-prefix state contracts, broader migration
and recovery coverage, and a bounded long-chain contract. No selector or
default profile was changed.
