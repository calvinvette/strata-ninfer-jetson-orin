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

## Expert-114 rank-0 residency intervention

A diagnostic profile moved layer-11 expert 114 from rank 9,412 to rank 0
(profile SHA256
`e495a29eb202f0918388e79e33b24691295c3b898ef1118c1a4491beafa0ebf8`).
With this profile, the 32-token two-live capture returned exact outputs for
both slots. For the prompt mapped to physical batch slot 0 in that run, all
captured GDN states at positions 86, 87 and 88 were exact; layer-10 fields and
layer-11 routes, activation, expert parts and combined output were also exact
at position 88. Expert 114 remained GPU-owned. The other observed CPU owner
changes at that row did not change their expert outputs.

The 72-token supervised repeat passed, but the intervention did not provide
long-chain parity: logical slot 0 stayed exact and logical slot 1 first
differed at output token 60. The dynamically assigned physical batch row for
the targeted prompt differed between captures, so row-level comparisons were
paired from each run's token/hash mapping. At position 88 the targeted prompt
still had exact layer-10 stage fields, layer-11 routes/activation/parts/output,
and all 36 committed GDN states. Its accepted-prefix GDN hash first diverged
later, at batch position 99 (serial prefix 97), ten positions later than the
baseline profile's first observed mismatch at batch position 89 (serial prefix
87). The 72-token run took 317.51 seconds and retained 17.74 GiB minimum
physical availability, with no sampled cgroup pressure/OOM events.

This targeted static residency change repaired the sampled position-88 owner
transition and delayed one later hash mismatch, but it did not prevent state
drift or one logical slot's output mismatch. It may also change residency for
other experts. This is a diagnostic result, not evidence for a global
CPU/GPU ownership preference or a serving profile; no default changed.

A same-profile supervised replication repeated the 72-token run. Exact-hash
alignment again mapped the target prompt (serial control 1) to a different
physical batch row; its first GDN mismatch was again batch position 99 / serial
prefix 97, with 18/36 allocations changed. The other prompt first differed at
position 75 / prefix 73, with 12/36 allocations changed. Both runs' logical
output records again had slot 0 exact and slot 1 first differing at token 60.
The replication took 354.55 seconds, retained 17.74 GiB minimum physical
availability, and recorded no cgroup pressure/OOM events. This reproduces the
sampled onset under this profile, but the persistent-state changes still have
no numerical drift or quality bound.

## Numeric state at the later divergence

A supervised follow-up captured every GDN commit at absolute positions 98 and
99 under the same expert-114 rank-0 profile. Exact token/hash alignment mapped
batch rows 0 and 1 to serial controls 0 and 1 for this run. At both captured
positions, row 0 / control 0 first differed at model layer 5: at position 98,
479,628/817,152 values differed (relative L2 `4.18e-7`, max absolute
`5.07e-6`); at position 99, 476,632 values differed (relative L2
`4.09e-7`, max absolute `5.04e-6`). Row 1 / control 1 first differed at
model layer 24: at position 98, 786,404 values differed (relative L2
`8.67e-5`, max absolute `0.0014014`); at position 99, 794,497 values differed
(relative L2 `9.16e-5`, same maximum absolute difference). Later GDN layers
also differed in both rows.

These snapshots precede the first output-token mismatch at index 60 (prompt
length 68). They show numeric recurrent-state differences before that output
mismatch, while the accepted-prefix hash trace places the respective first
hash changes at batch positions 75 and 99. The captures are same-absolute-
position snapshots; they do not identify the operation that first caused the
numeric change or bound its quality impact. The supervised capture took
314.81 seconds, retained 17.65 GiB minimum physical availability, and had no
cgroup pressure/OOM events. GPU clocks were observed dynamically; EMC readback
was denied and energy was not analyzed.

## Layer-23 owner transition in the rank-0 intervention

A separate same-profile capture sampled layer-22 stages and layer-23 MoE at
positions 98/99. At position 98 for the prompt paired to serial control 1,
all ten layer-22 stage fields (`x`, `qkv`, `h`, `gate`, `beta`, `z`, `y`,
`gdn_out`, `ffn_x`, `ffn_y`) were bit-identical. Layer-23 routes and the
2,560-value input activation were also exact. Expert 191 at rank 5 moved
GPU→CPU; it was the only expert part with a numerical difference (all 2,560
values; max absolute `3.0525e-5`, relative L2 `1.74245e-4`). Five other owner
changes at this row did not change their parts. The combined layer-23 MoE
output changed in 2,557/2,560 values (max absolute `1.9521e-6`, relative L2
`2.10527e-5`). The same capture's accepted-prefix hash trace first changed
for this prompt at batch position 99 / serial prefix 97, with 18/36 GDN
allocations changed.

The independent `native_expert_parity` replay used activation SHA256
`6c203aa62019f86efebdb91edc9455518daf20ed8812a30b365e46a818373039` and the
layer-23/expert-191 IQ2_S/IQ4_NL weights. The captured serial part matched the
CUDA oracle bitwise; the batch part matched the CPU oracle bitwise. CPU/GPU
oracle outputs differed in all 2,560 values (max absolute `3.0525e-5`, relative
L2 `1.74245e-4`). CPU/CUDA Q8_1 gate/up inputs and outputs matched; hidden Q8_1
differed in 3/60 scale bytes, and CPU down on CUDA hidden blocks reproduced
the CUDA output bitwise. This independently attributes the sampled expert
part delta to owner-specific arithmetic. It does not prove that this is the
only cause of later recurrent drift or establish a quality impact.

The direct numeric position-98/99 state snapshots described above came from a
separate run with the same profile and workload. The layer-22/23 capture
completed in 288.00 seconds with 17.74 GiB minimum physical availability and
no cgroup events. The oracle passed in 1.07 seconds with 26.84 GiB minimum
availability. The first two oracle invocations were harness setup failures
(an unsupported `--` argument and then a missing dump directory); the final
corrected oracle run passed. No accelerator default or profile changed.

## Earlier prompt: layer-30/31 boundary

A same-profile capture at batch position 75 mapped physical row 0 to serial
control 0 by the exact per-layer hash trace. The direct committed-state
comparison at this same position first differed at GDN model layer 32. At
layer 30, every captured stage field was bit-identical. At layer 31, however,
the MoE input activation already differed in all 2,560 values (max absolute
`0.0018873`, relative L2 `5.2730e-4`), and the routed expert IDs differed.
All ten expert parts and the combined layer-31 output therefore differed;
expert ownership codes were unchanged across the two rows. The combined
output relative L2 was `0.006014`. Because the input activation and route were
not equal, this is not an owner-arithmetic comparison. It places the sampled
change between the exact layer-30 stage and the layer-31 MoE input, before
expert execution, followed by changed GDN state at layer 32. It does not name
the responsible operation.

In the separate layer-4 check at the same position, routes and input activation
were exact. Expert 218 moved GPU→CPU but its part and combined layer-4 output
remained bit-identical. The layer-3 stage dump was requested but no `.stgdiag`
file was emitted, so that stage comparison is unsupported. The layer-30/31
capture passed in 287.03 seconds with 17.73 GiB minimum physical availability
and zero cgroup pressure/OOM events. This is a diagnostic run, not a performance
result.

The companion same-position follow-up maps batch row 0 to serial control 0 for
the earlier prompt. Layer-30 stage fields are exact and all layer-31 owner
codes match, but layer-31 routes differ and its input activation differs in all
2,560 values (max absolute `0.0018873`, relative L2 `5.2730e-4`). All ten
expert parts and the combined layer-31 output differ (combined relative L2
`0.006014`). The same run's GDN snapshot first differs at model layer 32. Since
the layer-31 inputs already differ, this does not support attributing its part
or output differences to owner arithmetic. It places the tested drift between
the layer-30 stage and layer-31 MoE input; the normalization/residual path
there remains unlocalized.

## `STRATA_NO_MULTI_GR` diagnostic ablation

A single-factor 72-token repeat set `STRATA_NO_MULTI_GR=1` with the same model,
profile, prompts, controls and position-75 captures. Exact-hash mapping again
paired the two rows to their serial controls. At the tested prompt, all
layer-30 fields remained bit-identical; layer-31's MoE input delta and route
difference were unchanged (relative L2 `5.2730e-4`), as were the combined
output delta (`0.006014`) and first committed GDN difference at layer 32.
Output slot 0 remained exact and slot 1 still first differed at token 60.
Thus this kernel-specialization flag did not repair the sampled boundary. The
single diagnostic run took 317.67 seconds with 17.66 GiB minimum physical
availability and no cgroup events. Instrumented run durations are not a
performance comparison; no default changed.
