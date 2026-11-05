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

The pair used the same 256-slot static profile. Its top 256 entries cover
layer 0, so all ten layer-1 experts at position 41 were CPU misses; the
service's layer-1 NInfer dispatch line does not mean those expert rows ran on
the NInfer GPU kernels. A separate actual-weight oracle for layer 1/expert
198, run on each backend's captured layer-1 input, dispatched the NInfer CUDA
operator and matched the Strata grouped reference bitwise for both inputs,
including all hidden Q8_1 bytes. That oracle checks the operator on fixed
inputs, not the service's CPU-miss path. The evidence therefore places a
small difference at the resident layer-0 output and a much larger change at a
subsequent CPU-owned MoE boundary, but does not yet prove the mechanism. Input
quantization sensitivity is a candidate explanation, not a demonstrated
cause; do not attribute this amplification to an NInfer kernel defect.

The supervised boundary pair passed with minimum available RAM 21.36 GiB;
the pre-existing cgroup OOM-kill count remained one. The GPU clock was observed
at 306 MHz, CPU clocks varied, EMC readback was denied, and energy was not
measured. These are functional diagnostics; their timings are excluded. The
structured data are in [`moe-comparison.json`](moe-boundaries-pos41/moe-comparison.json),
[`diag-comparison.json`](gdn-layer1-diag/diag-comparison.json) and
[`layer1-expert198-service-input-oracle/results.json`](layer1-expert198-service-input-oracle/results.json).
Supervisor memory/clock evidence is in
[`supervisor-moe-boundaries-pos41/result.json`](supervisor-moe-boundaries-pos41/result.json)
and [`supervisor-layer1-expert198-service-input-oracle/result.json`](supervisor-layer1-expert198-service-input-oracle/result.json).
Reproduction helpers are [`run_gdn_layer_diag_pair.py`](run_gdn_layer_diag_pair.py),
[`run_layer1_expert_input_oracle.py`](run_layer1_expert_input_oracle.py), and
[`compare_gdn_layer_diag.py`](../../../tools/integration/compare_gdn_layer_diag.py).
Raw GDN, MoE and activation captures remain local and are excluded from Git.

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
