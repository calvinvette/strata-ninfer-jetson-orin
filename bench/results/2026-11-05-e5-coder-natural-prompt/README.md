# Coder natural-prompt service and recurrent-state check

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This is a small E5
functional/state screen, not an answer-quality suite or performance result.

## Controls and task

The paired service arms used the same binary, Coder IQ1_M two-shard artifact,
pack, profile, cache options, four workers, prefill chunk 64 and 512-token
context. They used greedy sampling, `STRATA_PREFILL_CPU_SHARE=0`, prompt-cache
disabled and strict NInfer for the candidate. The model identity is pinned in
the [mixed-backend report](../2026-11-05-e5-mixed-static-one-token-pair/state-parity-8token-recheck/README.md).

The chat-formatted prompt was: “Solve this arithmetic problem: What is 2 + 2?
Respond with only the numeral.” It encoded to 32 prompt tokens. The expected
answer oracle requires exactly `4` after removing the generated `<|im_end|>`
stop marker. Each arm generated two tokens, `[19, 248046]`.

## Results

Both backends passed the exact answer oracle and returned identical token IDs
and accepted-prefix token sequences. Persistent-state hashes differed at both
accepted prefixes and at request completion.

Two fresh runs per backend captured the final GDN state at accepted length 33.
Within each backend, the two raw GDN captures were bit-identical. Across
Strata and strict NInfer, all 36 GDN layers differed: 28,205,015 of 29,417,472
float values, global relative L2 `0.0362582`. The first changed model layer
was layer 1 (`1.51e-9` relative L2); layer 2 was `7.36e-5`, and the maximum
per-layer relative L2 was `0.09134` at layer 23. The maximum absolute value
delta was `0.76329` at layer 25. The cross-backend result repeated exactly in
both paired captures.

The two Strata state dumps share SHA-256
`6be6e30a93d62a7c8591e5439223b4ffaac250fd5b8c926b318aa510c4384214`; both
strict-NInfer dumps share SHA-256
`e6959575aee54e414f53e3de36502f0412a6d2bcd9ea3ea72d0700c36d0d557a`.
The cross-backend per-layer comparisons are retained as JSON in each capture
directory; raw state arrays remain local because each is 113 MiB.

This shows deterministic recurrent-state drift despite identical answer tokens
for this one short arithmetic task. It does not establish a user-visible quality
regression or a useful numerical bound. The first synthetic-prompt diagnostic
found only `~1e-7` layer-0 operator/activation differences; the large recurrent
state movement here requires broader, layer-by-layer numerical analysis. No
latency is reported because state capture is intrusive and the request is too
short for a serving comparison.

Minimum available physical RAM was 20.44–20.59 GiB across the two supervised
GDN-captured pairs; the pre-existing cgroup OOM-kill count remained one in both.
Clocks were observed and dynamic, EMC readback was denied, and energy was not
measured. Raw command logs, memory samples and supervisor records are retained
in this directory. The 113 MiB per-arm GDN dumps remain local and are excluded
from Git; their comparison JSON and hashes are retained.

### Final-only arithmetic state recheck

Two additional fresh service pairs repeated this exact arithmetic prompt with
accepted-prefix tracing and GDN dumps disabled. Both backends returned answer
`4` and token IDs `[19, 248046]` in both pairs. All 11 final state fields,
including MTP and stale-page hashes, matched across backends and repeated
within each backend. This differs from the per-token trace's state mismatch
above. The trace helper synchronizes and copies state after each accepted
token; final-only hashing runs after generation and therefore has less
opportunity to affect scheduling. Instrumentation sensitivity is plausible,
not proven, and the final-only check cannot test intermediate states. The
minimum available RAM was 20.94 GiB, sampled swap peaked at 1.18 GiB, and the
pre-existing OOM counter remained one. The two-token request is not a
performance measurement. See the [final-only report](arithmetic-final-only/README.md).

## Next E5 gate

Repeat accepted-prefix numerical state checks over varied natural short tasks
and longer answer/retrieval tasks. Add a declared state-drift contract before
accepting the NInfer backend for service use. Keep MTP and adaptive residency
out of this comparison until the static resident-backend state behavior is
understood. E5, E6 and E7 remain open.

## Held-out executable code task

Date: 2026-11-05. A second functional screen used the same Coder IQ1_M two-shard
model, pack, binary, static profile, cache and service settings. The prompt
asked for a Python `is_even(n)` function. Its 44-token chat-formatted prompt
was followed by a maximum of 64 generated tokens. The independent executable
oracle checked `0`, `1`, `2`, `3`, `-2` and `-3`.

Strata and strict NInfer each generated the same 21 token IDs and the exact
code `def is_even(n): return n % 2 == 0`; all six oracle cases passed. All 21
accepted-prefix token IDs matched, but the persistent-state fingerprints first
differed after the first accepted token and remained different at all 21
captured boundaries. Final GDN, PLE, tail, dead, pooled, pooled-full and KV
fingerprints differed. NInfer dispatched all seven observed mixed-codec
tuples. Each arm offered two speculative drafts and accepted zero, so this run
did not commit drafted tokens.

The supervised pair completed in 42.16 seconds with 21.08 GiB minimum
available physical RAM; the pre-existing cgroup OOM-kill count stayed at one.
Clocks were observed but uncontrolled, EMC readback was denied, and energy was
not measured. The request order was sequential (Strata then NInfer), and
hashing/trace instrumentation was enabled. The per-request timings are
diagnostic only and must not be read as a backend performance comparison. The
one initial launch attempt with `--spec 0` exited before model loading because
this native pack requires a verifier window of at least two; the recorded
result uses `--spec 2`.

This adds one executable code-quality point with exact answer-token parity,
while reinforcing that matching text does not imply matching recurrent state.
It neither sets a numerical drift tolerance nor establishes broader code
quality. Raw supervised logs and the state comparator output are in
`even-pair-retry/` and `supervisor-even-pair-retry/`.

### First accepted-token GDN state

A supervised follow-up captured both backends' raw GDN arrays at the first
accepted token of the same `is_even(n)` prompt (engine state boundary `L=44`).
Both emitted token ID `71093`. The 36 GDN state slices contain 29,417,472 FP32
values total. Strata slice 0 was bit-identical; slice 1 first differed at
relative L2 `1.71e-9`; slice 2 reached `9.32e-4`. Drift then grew across the
remaining recurrent state, reaching `3.03e-2` at slice 18 and a maximum
per-slice relative L2 of `9.19e-2` at slice 26. Overall, 28,242,042 values
(96.0%) differed and global relative L2 was `5.41e-2`. The maximum absolute
delta was `3.093` at slice 33. Slice numbers here are the serialized GDN
state ordinals, not a causal attribution to a specific operator.

The same binary, profile and cache were used in a sequential Strata-then-NInfer
service pair with greedy sampling and prefill CPU share disabled. The
supervisor passed in 23.29 seconds with 20.93 GiB minimum available physical
RAM; the pre-existing cgroup OOM-kill count stayed at one. Clocks were
observed but uncontrolled, EMC readback was denied, and energy was not measured.
Raw 113 MiB state arrays are local and excluded from Git. Their hashes, logs
and the per-slice comparison are retained under `even-gdn-pair-retry/`.

This confirms that substantial downstream recurrent-state divergence is
already present after the first generated token, even though that token and
the completed function match. It does not determine whether the difference
arises during prompt prefill, at a particular expert operator, or in a later
state update. An opt-in prefill-state hook did not produce a capture in this
service path and is not used as evidence. The numerical tolerance and user-
visible impact remain open.

### Prompt-position 41 layer boundary capture

A follow-up captured every prompt row through GDN layer 1 and MoE bundles at
layers 0, 1, 2, 12, 17, 21 and 47 for the same 44-token `is_even` prompt. The
binary was built from source `910b3e1b` (SHA-256
`42fbb0afd69eb11979884352584a5f14f141b3e3ed5a6e87eef4a780aa721b2c`); the
temporary 256-slot profile SHA-256 was
`c1e66c2e60ae8e7880befa303fb6bb79da1ccdd59895053eb95d433c648ef047`.
The run used greedy sampling, the same IQ1_M two-shard artifact, profile and
cache, 4 workers, prefill chunk 64 and 512-token context. At position 41
(token ID 271), layer 0 had identical route IDs, route weights and inputs.
Its ten expert parts differed by relative L2 `6.31e-8`, and the combined
output by `3.50e-8`. At layer 1, route IDs still matched, while route
weights and inputs differed by `2.36e-7` and `3.80e-7`; expert parts differed
by `1.18e-3`, shared output by `1.57e-4`, and combined output by `1.334e-3`.
The GDN raw output at layer 1 remained close (`7.55e-8` relative L2) at that
position. Later sampled MoE boundaries show the difference growing through
the remaining network; layer 21 and layer 47 also had changed route IDs.

The owner capture corrects the initial CPU-miss interpretation: all ten layer-1
routes at position 41 have owner kind `0` (primary VRAM/foresight), and the
captured activation is marked invalid because there are no CPU-owned experts.
The engine log reports 391 allocated slots; the `--expert-cache 256` request
was raised by memory sizing. Thus the row did run through GPU expert execution,
and the layer-1 dispatch marker corresponds to actual work in this prompt
prefill.

Independent same-input checks cover all ten routed layer-1 experts for both
service activations (20 checks total). In every case the service expert output
is bit-identical to Strata's native grouped GPU oracle, and the NInfer
grouped-kernel oracle is bit-identical to that same reference (`0/2560` output
values changed; hidden Q8_1 bytes also match). Yet replaying the native grouped
GPU operation on the two slightly different service inputs changes each
expert output by relative L2 `2.36e-4` to `1.75e-3`, matching the direction and
scale of the service bundle differences. This is strong evidence that the
layer-1 divergence is driven by the changed activation entering the experts,
not an NInfer-versus-Strata kernel mismatch for a fixed input. A follow-up on
layer 1 / position 41 / expert 198 found that the two input activations differ
by relative L2 `3.80e-7`, yet one of 80 input Q8_1 blocks stores a different
FP16 scale while all integer codes match. The actual CUDA quantizer agrees
with the independent Q8_1 oracle for both rows, and same-input NInfer/native
expert replays are bit-identical. This proves a local input-quantization scale
boundary, but does not assign all layer-1 output or later state drift to that
one block or define an acceptable state tolerance. See the [expert-198
quantization report](layer1-expert198-service-input-oracle/README.md). The
source of the small upstream activation difference, numerical tolerance and
user-visible impact remain open.

The follow-up layer-0 capture now identifies the first numerical delta in this
trace. With identical layer-0 inputs/routes, five CPU-owned expert outputs
matched exactly while all five GPU-owned rows differed by relative L2
`8.39e-8`–`8.54e-8`. Gate/up values and hidden Q8_1 bytes matched the native
CUDA oracle; the discrepancy is isolated to the IQ4_NL down projection's
different floating-point accumulation order. See the [layer-0 first-divergence
report](layer0-first-divergence/README.md). This explains the observed small
delta for this sampled row, not every request or the acceptable state budget.

The layer-1 GDN stage capture further narrows that boundary at position 41:
incoming `x` differs by relative L2 `7.75e-8`, while `qkv` and recurrent `h`
are bit-identical. Captured `gdn_out` is also bit-identical; the later `ffn_x`
passed into MoE differs by `3.80e-7`, followed by `ffn_y` at `1.334e-3`.
Thus the expert-input delta is present before MoE dispatch, and this layer's
recurrent update does not add a state/output delta at this row. The capture does
not identify which preceding residual or normalization operation created the
`x`/`ffn_x` movement, or why the quantized projections amplify it.

The owner-capture service pair passed with minimum available RAM 20.88 GiB;
the independent grouped-kernel oracle retained 24.32 GiB minimum. The
pre-existing cgroup OOM-kill count remained one. The GPU clock was observed at
306 MHz, CPU clocks varied, EMC readback was denied, and energy was not
measured. These functional diagnostics' timings are excluded. Structured data
are in [`moe-comparison.json`](moe-cpu-owner-pos41/moe-comparison.json),
[`owner.jsonl`](moe-cpu-owner-pos41/strata.moe-owner.jsonl),
[`layer1-gpu-input-oracle/results.json`](layer1-gpu-input-oracle/results.json),
[`diag-comparison.json`](gdn-layer1-diag/diag-comparison.json) and the
[single-expert check](layer1-expert198-service-input-oracle/results.json).
Supervisor metadata is in
[`supervisor-moe-cpu-owner-pos41/result.json`](supervisor-moe-cpu-owner-pos41/result.json)
and [`supervisor-layer1-gpu-input-oracle/result.json`](supervisor-layer1-gpu-input-oracle/result.json).
Reproduction helpers are [`run_gdn_layer_diag_pair.py`](run_gdn_layer_diag_pair.py),
[`run_layer1_expert_input_oracle.py`](run_layer1_expert_input_oracle.py),
[`run_layer1_gpu_input_oracle.py`](run_layer1_gpu_input_oracle.py), and
[`compare_gdn_layer_diag.py`](../../../tools/integration/compare_gdn_layer_diag.py).
Large GDN/MoE captures and generated weight/output arrays remain local and are
excluded from Git.

### Independent oracle for a resident mixed-codec service row

To distinguish resident NInfer arithmetic from CPU fallback, the recorded
profile was decoded: layer 0 / expert 25 is rank 281 and was in the 391 loaded
cache slots; expert 143 is rank 399 and was not resident, so its exact CPU
match is excluded as NInfer operator evidence. At prompt position 2, expert 25
was selected at route rank 3 for token ID `3`.

The existing `native_expert_parity` harness replayed that exact service input
and actual expert weights. GGML `to_float` decoded all 4,915,200 gate/up/down
weight values bit-for-bit. The harness's FP64 full projection and native CUDA
reference were compared with the captured Strata and strict-NInfer rows:
Strata matched native CUDA bit-for-bit, while strict NInfer differed by
relative L2 `8.76e-8` (maximum absolute delta `1.86e-8`, zero invalid values).
Against the unquantized FP64 projection, both service rows differed by about
`1.1211e-2` relative L2; this reference does not apply activation or hidden
Q8_1 quantization, so the difference is not a universal tolerance or a
standalone accuracy failure. It does verify actual weight decoding and one
resident service row against independent arithmetic.

The supervised oracle command passed in 1.07 seconds with 24.93 GiB minimum
available physical RAM and no increase to the pre-existing cgroup OOM-kill
count. Clocks were uncontrolled, EMC readback denied, and energy was not
measured. The reproducible comparison is
[`comparison.json`](layer0-expert25-oracle/comparison.json), generated by
[`compare_layer0_expert25_oracle.py`](compare_layer0_expert25_oracle.py).
The large dequantized weight and raw output arrays remain local and are
excluded from Git; command output and telemetry are retained alongside the
report.

This qualifies one IQ3_XXS/IQ4_NL expert row only. It does not establish a
whole-model numerical budget, other tuple coverage, or task-level quality.
