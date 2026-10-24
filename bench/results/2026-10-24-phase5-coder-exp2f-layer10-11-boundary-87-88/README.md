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

## `STRATA_GR_V3=1` boundary intervention and 128-token extension

The existing opt-in two-kernel fused hyperconnection read (`STRATA_GR_V3=1`)
was tested with the same expert-114 rank-0 profile, model and prompt pair. In a
72-token capture, both outputs matched their serial controls. At position 75
for the prompt paired to serial control 0, layer-30 stage fields, layer-31
routes/input activation/all expert parts/combined output and all 36 GDN state
records were bit-identical. This changes the earlier baseline observation at
that position: without GR-V3, the layer-31 activation and routes differed and
GDN state first differed at layer 32.

The 128-token extension reproduced exact position-75 parity at those same
boundaries. Both output streams matched their serial controls: one stopped
identically at 120 tokens and the other matched all 128 requested tokens.
Persistent state parity still failed later. Exact hash alignment found the
first mismatch at batch position 100 / serial prefix 98 for control 0 (9/36
GDN allocations changed) and position 105 / prefix 103 for control 1 (21/36).
Direct same-absolute-position snapshots found the first changed GDN layer was
36 at position 99 and 100 for control 0, and layer 20 at position 105 for
control 1. Those numeric snapshots use absolute model positions, while the
hash report uses accepted-prefix alignment; keep the coordinate definitions
separate when comparing the values. The accepted-prefix hash onset repeated
at the same positions in the separate 72-token run.

This is a promising opt-in local/state and output improvement for this prompt
pair, but it delays rather than eliminates later state drift. It has no held-out
prompt, quality, sustained-service or performance confirmation and does not
qualify a profile or default. The 72-token capture took 286.88 seconds; the
128-token capture took 484.45 seconds and retained 17.69 GiB minimum physical
availability, with no cgroup pressure/OOM events. Clocks varied dynamically;
EMC readback was denied; energy was not analyzed.

#### Committed-state alignment at positions 103–105

A follow-up captured all GDN committed-state layers at model positions 103 and
105 in the same 128-token GR-V3 run. Both serial and two-live output streams
matched exactly (120 and 128 generated tokens). The batch and serial rows had
the same token at each compared absolute model position. At position 103, all
36 GDN states were bit-identical. At position 105 (token 7620), the first
changed state was model layer 20: 796,266/817,152 values changed, maximum
absolute delta `0.0031543`, relative L2 `1.8271e-4`; its recurrent and
convolution portions had relative L2 `9.4160e-5` and `1.8276e-4`. A separate
same-profile capture at position 104 also found layer 20 as the first changed
state. These captures bound the sampled onset to the layer-20 boundary around
positions 103–105, but do not isolate the operation.

At the same-position p105 stage capture, layer-20 `x`, `qkv`, `gate`, `beta`
and `z` were exact; `h` was the first changed field (relative L2
`1.7037e-4`). `gdn_out` and `ffn_y` were downstream deltas (relative L2
`1.6631e-3` and `7.2968e-3`). The focused convolution+L2 test passes for equal
history/input at every verifier window and split, so it does not identify a
local kernel arithmetic defect; divergent convolution history or an upstream
state/input difference remains possible.

The accepted-prefix hash labels need a separate interpretation. Source inspection
shows batch GDN hashes are sampled before `ver.run_slot_rows()` (before that
window updates state), while the serial `ACCEPTED_PREFIX` hash is sampled after
commit. Thus the hash analyzer's batch-p105 / serial-prefix-103 match is not a
pair of committed states at those numeric positions. A direct attempted
cross-position dump comparison was rejected by the new analyzer because the
captured tokens differ (serial p103: 27379; batch p105: 7620). Comparing the
committed dumps at equal model position instead checks equal token and state
boundary: p103 was exact and p105 first changed at layer 20. This clarifies the
sampling boundary without invalidating the hash records at their own stages.

The repeat took 427.29 seconds and retained 17.68 GiB minimum physical
availability with zero cgroup OOM events. Binary SHA256 was
`ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df`; temporary
expert-profile SHA256 remained `e495a29eb202f0918388e79e33b24691295c3b898ef1118c1a4491beafa0ebf8`.
The full dump and compact analyses remain local; the reusable position-aware
analyzer is `tools/integration/compare_gdn_commit_state.py`.

#### Expert-137 residency intervention

At p104 in the baseline profile, layer-19 routes and input activation were
exact. Expert 137 (rank 2 among the ten routed experts) and expert 146 changed
GPU→CPU. Expert 137 was the only changed part: its relative L2 delta was
`2.1722e-4`; expert 146's part stayed bit-identical. The combined MoE output
changed by relative L2 `6.8178e-5`. The activation SHA256 was
`459114f25e2642d1d679e489358e08865614dc51d443bdc3343eca3d7b6489a2`.

The exact-activation native oracle confirmed the owner arithmetic. With
`STRATA_NATIVE_CPU_Q8_1_DOT=all` matching the capture environment, serial
expert-137 service output matched the GPU oracle bitwise and batch output
matched the CPU oracle bitwise; their relative L2 difference was `2.1722e-4`.
Expert 146's CPU and GPU oracle outputs were bit-identical for this activation,
matching its unchanged service part. An initial oracle call without the Q8_1
selector failed these service-to-oracle joins; it was retained as a harness
configuration mismatch and rerun with the recorded selector.

A one-factor profile moved layer-19 expert 137 from global rank 9,938 to rank 0
while retaining the prior layer-11 expert-114 rank-0 profile. Its profile
SHA256 was `0ed56fbe092e01d981f317ea85854b7c1e3bffcbff8a8b485f0d24fa6fe7d86f`.
At p104, expert 137 stayed GPU-owned in both rows; expert 146 still changed
owner but all parts and the layer-19 combined output were bit-identical. Layer
20's stage and committed state were exact. In the same 72-token run, all 36
committed GDN layers remained exact at matched-token positions 103, 104 and
105. At p105, three layer-19 owner changes also left all expert parts and the
combined output exact.

This is a local state-boundary repair, not an end-to-end improvement. Slot 0's
72-token output remained exact, but slot 1 first differed at output token 66;
the prior GR-V3 profile with expert 137 at its original rank matched both
72-token outputs. The candidate's pre-window batch hash trace first differed
later at batch position 126 / serial accepted-prefix position 124, rather than
at its earlier baseline hash positions. The hash and committed-state captures
have different sampling boundaries as documented above. The intervention
shows that expert-137 owner arithmetic contributed to the sampled p104 MoE and
layer-20 state delta, but it did not remove later state/output divergence and
is not a serving recommendation. The run took 309.01 seconds with 17.61 GiB
minimum physical availability and no cgroup OOM events. Full raw captures and
oracle dumps remain local under `capture-gr-v3-72-e137-first-103-105/` and
`oracle-layer19-expert137-q8all/`.

### GDN layer-20 follow-up and verifier convolution parity

Two additional 128-token `STRATA_GR_V3=1` captures sampled layer-20 and layer-19
MoE around the control-1 accepted-prefix hash onset (batch position 105 / serial
prefix 103). In both, layer-19 MoE inputs, routes, expert parts and combined
output were exact despite three owner changes. The adjacent-position capture
also sampled batch position 104. Direct state comparison by *same absolute
position* first reported layer 20 changed at both positions; at 104 the first
different captured layer-20 stage field was `x` (relative L2 `1.872e-5`), while
at 105 it was `h` (`1.704e-4`) and `x`/`qkv` were exact. At 105 the changed
downstream fields included `gdn_out` (relative L2 `1.663e-3`) and `ffn_y`
(`7.297e-3`). These observations do not isolate the operator responsible.
Crucially, these are same-absolute-position comparisons; the accepted-prefix
hash pairing compares batch position p with serial prefix p-2. The numeric
snapshots therefore are not equivalent aligned accepted-prefix pairs and must
not be read as the accepted-state onset or a causal first-difference trace.
The accepted-prefix hash onset remained p100/prefix98 for control 0 and
p105/prefix103 for control 1; output tokens remained exact in this 128-token
run. The adjacent capture took 422.58 seconds and retained 17.64 GiB minimum
physical availability with no cgroup events.

To close a focused functional coverage gap, `gdn_parity` now compares
`gdn_conv_l2_multi` against the ordinary state-advancing single-token kernel for
the model channel width (10,240), all verifier windows T=1..8, and each split
`t_begin` position. The supervised Orin CUDA run passed bitwise for both the
whole-window and split calls at every T; the existing accepted-prefix history
check also passed all 44 `(T, keep)` combinations. An initial test-harness run
incorrectly advanced the reference history twice (the single-token kernel
already commits it); that harness mistake was corrected, with no kernel change.
The complete `gdn_parity` executable then reported zero failures. Build used
`-j1`; the supervisor recorded 26.25 GB minimum physical availability and no
pressure events. HIP/SYCL builds remain pending maestro1 scratch-space recovery.
