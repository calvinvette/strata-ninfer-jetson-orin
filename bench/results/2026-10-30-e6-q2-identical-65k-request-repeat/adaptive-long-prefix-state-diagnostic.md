# Adaptive long-request then prefix state diagnostic

Date: 2026-10-30  
Host: Jetson AGX Orin 64 GB, CUDA 12.6  
Model: Qwen3.8-Flash-Next Q2_0, same local model and rendered token prefix as the E6 65K repeat runs  
Build/profile: current `feat/ninfer-expert-e0` Strata/NInfer binary, original Q2 expert profile, adaptive expert swaps enabled  
Purpose: determine whether an intervening long request changes persistent state for an identical short prompt prefix.

## Adaptive result and fixed-owner control

One process received the 65,536-token prompt with 32 generated tokens, followed
by the exact first 8,192 token IDs as a second request with one generated
token. The first request's state at position 8,192 was GDN
`96a8debe9d965ae8`, PLE `c776a56826340f95`, QSA tail `f72d24ad104300b7`,
dead state `ba4d730b89d297e5`, and pooled-full `fa799ae60931ddd9`. After the
long request, replaying the same 8,192 token prefix ended at GDN
`994f4c41001157d9`, PLE `8f834c5fe472a9e5`, QSA tail `2f18de91a9aab11b`,
dead state `40ccf57e6c30218e`, KV `94ed00cf754f7d1d`, and pooled-full
`f3ce497f5331f3e7`. The replay emitted token ID `248046`, the same first
generated token as the earlier short-prefix controls.

The adaptive long request ran at 86.7 prompt tok/s and 1.3 decode tok/s; its
GPU cache hit rate was 32.9% (5,052/15,360), with 117 expert exchanges and
8,939 file blob reads. The 8K replay ran at 75.0 prompt tok/s and 0.4 decode
tok/s, with 10.4% GPU cache hits (50/480), 129 exchanges and 9,288 cumulative
file reads.

The same 65K→8K sequence was repeated in a second process with adaptation
disabled, keeping the original Q2 expert profile, prompt tokens, generation
limits, reset path and binary. Its 65K boundary fingerprint exactly matched
the adaptive arm's 65K boundary. Its following 8K boundary was GDN
`6d34cf6a8ae091cd`, PLE `8f834c5fe472a9e5`, QSA tail `2f18de91a9aab11b`,
pooled `49c796bf956da6ea`, KV `e9f0ae23370d9ddb`, and pooled-full
`c3e68b858e40805f`. These fields exactly match the standalone 8K fixed-profile
controls, which repeated across three requests. The fixed arm also emitted
token ID `248046`.

This controlled toggle implicates adaptive residency history in the
post-65K state change: adaptation-on replay state differs, while adaptation-off
replay state returns to the standalone baseline. It does not identify the
specific swap or prove how that owner change affects state arithmetic. Route
instrumentation wrote one data row rather than one for each request, so the
owner map at the changed replay row remains unknown. Matching first-token IDs
do not establish matching persistent state or semantic quality.

With adaptation disabled, the 65K request ran at 86.6 prompt tok/s and 1.2
decode tok/s with 12.0% GPU cache hits (1,836/15,360), zero expert exchanges.
The 8K request ran at 77.0 prompt tok/s and 0.4 decode tok/s with 11.2% hits
(54/480), zero exchanges. These instrumented rates do not isolate the cost or
benefit of adaptation and are not performance evidence.

Both supervisors passed: minimum available physical memory was 8.58 GiB in
the adaptive arm and 8.68 GiB in the fixed-owner control, above the preserved
6 GiB floor; sampled OOM kills were zero. Adaptive raw material is in
`/tmp/e6-65k-long-then-prefix-layer1/` and
`/tmp/e6-65k-long-then-prefix-layer1-supervisor/`. Fixed-owner raw material is
in `/tmp/e6-65k-long-then-prefix-fixed/` and
`/tmp/e6-65k-long-then-prefix-fixed-supervisor/`. The incomplete owner dump
was not checked in.

### Adaptation-on repeat without route capture

A second adaptation-on process repeated the exact 65K→8K sequence with route
capture disabled. The full 65K prompt-boundary fingerprint matched the first
adaptive run byte-for-byte. The following 8K state also reproduced exactly:
GDN `994f4c41001157d9`, PLE `8f834c5fe472a9e5`, tail
`2f18de91a9aab11b`, pooled `1572532cee713cae`, KV `94ed00cf754f7d1d`, and
pooled-full `f3ce497f5331f3e7`. Both response hashes matched the first
adaptive run: long `2d5f3da8…` and 8K `201a8bab…`; the replay again emitted
token ID `248046`. Cache hits were again 32.9% for 65K and 10.4% for the 8K
replay, with 117 and 129 exchanges respectively. The supervisor passed with
8.50 GiB minimum available physical memory and zero sampled OOM kills. The
repeat confirms this same-process adaptive pattern without the owner-capture
hook; it still does not identify a particular expert transfer as the cause.
Raw run and telemetry are in `/tmp/e6-65k-long-then-prefix-adaptive-repeat/`
and `/tmp/e6-65k-long-then-prefix-adaptive-repeat-supervisor/` on the Orin.

### Repeated-position capture harness control

To check whether the one-row 65K→8K capture was caused by a global row limit,
two consecutive identical 8K requests were run with the same layer-1,
position-8191 capture filter. The hook emitted two data rows plus its header:
dispatches 1 and 49, stream rows 0 and 1. Both rows had token ID 2438, routed
experts `[155, 500, 67, 499, 12, 6, 439, 153, 232, 160]`, and owner kinds
`[-1, -1, -1, -1, 0, 0, -1, -1, -1, -1]`. Both requests also had the same
prompt-boundary state and generated token ID. The supervisor passed with
8.53 GiB minimum available memory and zero sampled OOM kills. Thus the capture
hook can record repeated matches; the missing second row is specific to the
long→prefix sequence or its layer-1 route-position path, not a general
single-row/global-limit behavior. Raw data is in `/tmp/e6-two8k-owner-capture/`
and `/tmp/e6-two8k-owner-capture-supervisor/` on the Orin.

### Long→prefix boundary position-window capture

The adaptive 65K→8K sequence was repeated with the layer-1 capture filter
widened to positions 8188–8195 and the row cap raised to 64. The state and
output hashes reproduced the prior adaptive runs exactly. The owner dump still
contained only one row: the first request's layer-1 record at position 8191,
dispatch 1537, stream row 32, with the same expert IDs and owner kinds as the
first long→prefix attempt. No layer-1 route row in that position window was
emitted for the replay request. Since the two-8K control emitted both rows,
raising the cap and widening the position filter do not explain the missing
replay record. This does not show whether the replay's selected-layer
`row_positions` shifted elsewhere or whether that dispatch used another path.
The supervisor passed with 8.54 GiB minimum available memory and zero sampled
OOM kills. Raw data is in `/tmp/e6-65k-long-prefix-owner-window/` and
`/tmp/e6-65k-long-prefix-owner-window-supervisor/` on the Orin.

### Request-tagged selected-layer position trace

An opt-in route-position trace was added for selected-layer MoE dispatches.
Unlike the owner capture filter, it records every observed dispatch position
and the request sequence number. On the adaptive 65K→8K rerun it recorded 32
layer-1 decode dispatches for request 0, at positions 65,535–65,566, then one
layer-1 row for request 1 at position 8,191 (dispatch 1,537). The owner capture
also emitted that replay row: token ID 2438, routed experts
`[155, 500, 67, 499, 12, 6, 439, 153, 232, 160]`, owner kinds
`[-1, -1, -1, -1, 0, 0, -1, -1, -1, -1]`. Thus the selected-layer replay
dispatch was present at the expected position; the earlier apparent omission
came from interpreting a capture that sampled late decode positions during
the 65K request as a complete per-request dispatch trace. The short two-8K
control and this long→prefix trace now both show the replay's layer-1 row.

The run reproduced the adaptive state and output hashes: 65K boundary GDN
`85907b6a2b85d24e`, PLE `df3795d240365f69`, tail `c4a5d96bb5c4e077`,
pooled-full `f2e8d94d3fe3944a`; replay GDN `994f4c41001157d9`, PLE
`8f834c5fe472a9e5`, tail `2f18de91a9aab11b`, pooled-full
`f3ce497f5331f3e7`; generated token IDs and hashes matched prior adaptive
runs. The replay route IDs/owner kinds therefore do not by themselves explain
the state change. A causal link to another layer, an earlier state update, or
an adaptive transfer remains unproven. The supervisor passed with 9.16 GiB
minimum available physical memory, above the six-GiB floor, and zero sampled
OOM kills. Instrumented prompt rates were 86.6 tok/s for 65K and 76.1 tok/s
for 8K; these are diagnostic observations, not comparable performance data.
Raw files are in `/tmp/e6-65k-long-prefix-request-trace/` and
`/tmp/e6-65k-long-prefix-request-trace-supervisor/` on the Orin.

The trace is opt-in via `STRATA_TRACE_MOE_POSITION_PATH` and
`STRATA_TRACE_MOE_POSITION_LAYER`. `STRATA_CAPTURE_MOE_PATH` now shares the
dispatch hook and adds a request sequence to its internal call, but the owner
JSON schema is unchanged. No default serving behavior or cache policy changed.

### Adaptive events and sampled accepted-prefix state

The request-tagged run was repeated with `STRATA_TRACE_ADAPT=1` and accepted
prefix hashes at stride eight, retaining the first and final checkpoints. The
65K request again produced the same 32-token hash
`2d5f3da8f9890f8c9262231bada2cfab088196528565a1c08ab685d86074c650` and the
same final state. During its generated-token phase, the log recorded adaptive
choice batches of 96 at rounds 4, 8, 12, 16, 20, 24, 28 and 32. The sampled
accepted prefixes were 1, 8, 16, 24 and 32; the first checkpoint's hash fields
matched the prompt-boundary hash, and the final checkpoint matched the prior
adaptive run. Exact long-request fingerprints at accepted prefixes 8, 16 and
24 are retained in the raw engine log. This trace shows update timing relative
to sampled commits, but it does not compare the same accepted prefix against a
fixed-owner arm and cannot attribute state changes to those updates.

After request reset, the 8K replay boundary again had GDN
`994f4c41001157d9`, PLE `8f834c5fe472a9e5`, tail `2f18de91a9aab11b`, KV
`94ed00cf754f7d1d`, pooled-full `f3ce497f5331f3e7`; its first accepted token
was `248046` and its first accepted-prefix hash matched the prompt-boundary
hash. The trace confirms repeatability at this sampled point, not equivalence
to the standalone 8K state. Minimum available memory was 9.15 GB (8.52 GiB),
above the six-GiB floor; sampled OOM kills were zero. State hashing slowed
decode to 0.3 tok/s on the 65K request and 0.2 tok/s on the replay, so these
rates are instrumentation artifacts and excluded from performance comparisons.
The supervisor took 1,034 seconds. Raw logs and checkpoints are in
`/tmp/e6-65k-adaptive-prefix-state-trace/` and
`/tmp/e6-65k-adaptive-prefix-state-trace-supervisor/` on the Orin.

### Matched adaptive/fixed accepted-prefix comparison

The accepted-prefix trace was then run with the same 65K→8K input, Q2 profile,
binary, and sampling in a matched adaptation-disabled arm (`--adapt-every 0
--adapt-swaps 0`). Both arms passed supervision and emitted identical full
32-token outputs for the long request (SHA256
`2d5f3da8f9890f8c9262231bada2cfab088196528565a1c08ab685d86074c650`) and the
same one-token replay (SHA256
`201a8bab084b2a57aa2f6a8ceb51b3609f4c5a297d952bf51dbf4cd321e16151`). Their
65K prompt-boundary state hashes matched exactly. At accepted prefix 1, the
state hashes also matched. At the first later sample, accepted prefix 8, all
eight generated token IDs still matched, but GDN, QSA tail, pooled, KV and
pooled-full hashes differed; PLE remained equal. The same five fields differed
at accepted prefixes 16 and 24. At accepted prefix 32, PLE also differed.
This locates the first *sampled* state divergence between accepted prefixes 1
and 8 while the generated text remains identical. In the adaptive arm,
96-choice update batches were scheduled/applied at rounds 4 and 8 before the
prefix-8 sample. This associates the first sampled divergence with the period
containing adaptation updates, but does not prove which transfer, owner
arithmetic, or state operation caused it. The round-4 batch was applied before
the prefix-8 checkpoint; the round-8 batch was scheduled at that checkpoint
and applied immediately afterward.

On the subsequent exact 8K replay, the fixed-owner boundary matched the
standalone fixed-profile state exactly (GDN `6d34cf6a8ae091cd`, PLE
`8f834c5fe472a9e5`, tail `2f18de91a9aab11b`, pooled `49c796bf956da6ea`, KV
`e9f0ae23370d9ddb`, pooled-full `c3e68b858e40805f`). The adaptive replay again
had the previously recorded state (GDN `994f4c41001157d9`, PLE
`8f834c5fe472a9e5`, tail `2f18de91a9aab11b`, pooled `1572532cee713cae`, KV
`94ed00cf754f7d1d`, pooled-full `f3ce497f5331f3e7`). Both replay prompts
returned token `248046`. Thus PLE and tail matched at this boundary; GDN,
pooled, KV and pooled-full did not.

The adaptive arm's minimum available memory was 8.52 GiB; the fixed arm's was
8.65 GiB. Both stayed above the six-GiB reserve, with zero sampled OOM kills.
The accepted-prefix hash instrumentation slowed decode to about 0.3 tok/s;
these are state-diagnostic runs, not performance comparisons. The fixed arm
took 1,030 seconds. Its raw logs and supervisor records are in
`/tmp/e6-65k-fixed-prefix-accepted-trace/` and
`/tmp/e6-65k-fixed-prefix-accepted-trace-supervisor/` on the Orin.

An additional attempt combined accepted-prefix tracing with
`STRATA_STATE_HASH_GDN=1` and `STRATA_STATE_HASH_QSA_LAYERS=1` for layer-level
localization. The fixed-owner process emitted its 65K boundary fingerprints,
then hit Strata's 60-second no-progress watchdog before its first generated
token; the supervisor failed with return code 1, minimum available memory
8.67 GiB and no OOM kills. This combination produced no accepted-prefix
result and is not evidence of state divergence. It is retained as a failed
instrumentation cell in `/tmp/e6-65k-fixed-per-layer-prefix-trace/` and
`/tmp/e6-65k-fixed-per-layer-prefix-trace-supervisor/`.

### Boundary layer summaries and direct GDN byte comparison

The fixed-owner and adaptive 65K→8K sequences were repeated with boundary-only
GDN and QSA layer summaries, without accepted-prefix hashing. Both passed
supervision and reproduced the same long-request token hash
`2d5f3da8f9890f8c9262231bada2cfab088196528565a1c08ab685d86074c650` and
8K replay token hash `201a8bab084b2a57aa2f6a8ceb51b3609f4c5a297d952bf51dbf4cd321e16151`.
The 65K prompt-boundary summary matched across arms. At the 8K replay boundary,
the QSA per-layer summaries matched across arms, while the aggregate state
fingerprints continued to differ in GDN, pooled state and KV. The per-allocation
GDN hashes differed beginning at allocation index 3 (zero-based); all 36
allocations were included in the capture.

Because the aggregate and layer summaries needed a direct cross-check, a
second matched pair wrote the complete GDN state at the replay boundary. Both
binary dumps have header `(cells=8192, layers=36, floats_per_layer=817152)`
and are 117,669,920 bytes including the 32-byte header. Their SHA256 values
are fixed-owner `8183e0c1bb3c0f95e97b0a53288ced28f38477d5e4469978a0e5266704aebd6e`
and adaptive `5ce9078c5101222ce0853f879d0c26a4044290a5d5edaae6fb006eb94c3a0c73`.
The first payload difference is 512 bytes into GDN allocation 3; allocations
0–2 match byte-for-byte and 33 of 36 allocations differ. Across the 113 MiB
payload, 56,754,088 byte positions differ. This confirms replay GDN divergence
and localizes its first observed allocation, but does not identify the model
operator, expert transfer, or arithmetic event that produced it. QSA per-layer
hashes are fingerprints rather than a byte-level proof; the aggregate QSA
fingerprint differences remain unresolved by this capture.

The fixed-owner direct-dump run passed with 9.30 GB minimum available physical
RAM; the adaptive run passed with 9.22 GB. Both remained above the 6 GiB floor
and recorded zero sampled cgroup OOM kills. Their raw GDN dumps, logs and
supervisor telemetry remain in `/tmp/e6-65k-fixed-gdn-dump/`,
`/tmp/e6-65k-fixed-gdn-dump-supervisor/`, `/tmp/e6-65k-adaptive-gdn-dump/`,
and `/tmp/e6-65k-adaptive-gdn-dump-supervisor/` on Orin. These synchronized
state diagnostics are not performance measurements.

### Direct GDN capture at accepted prefix 8

To compare raw GDN bytes at the first sampled divergence rather than only at
the later 8K replay boundary, the matched 65K requests were repeated with a
full GDN dump triggered at `cells=65543` (accepted prefix 8). Both runs passed
supervision, returned the same 32 tokens (SHA256
`2d5f3da8f9890f8c9262231bada2cfab088196528565a1c08ab685d86074c650`), and had
identical 65K prompt-boundary fingerprints. The dumps have the same header
`(cells=65543, layers=36, floats_per_layer=817152)` and 117,669,920-byte size.
Their fixed-owner and adaptive SHA256 values are respectively
`2c45c07ef046a4ae6cfd7693e280a80ff866cddca4ca186fa370da05e29db3d9` and
`2fdbc4708352215787fb71d4710fc32d07cb3c5539519a727da46378be619101`.

The first payload difference is byte 6,538,252, which is 1,036 bytes into
zero-based GDN allocation 2. Allocations 0–1 match; allocations 2–35 differ
(34 of 36 allocations), with 67,929,282 differing payload byte positions.
The session maps GDN allocations in model-layer order while omitting QSA
layers 3, 7, …; allocation 2 therefore belongs to zero-based model layer 2.
This is the earliest directly byte-localized divergence at the sampled prefix.
It complements, rather than replaces, the separate 8K replay-boundary result,
where the first differing allocation was index 3. These are distinct sequence
positions and do not identify a specific update, owner transition, expert, or
arithmetic operation as the cause.

The fixed-owner run passed with minimum available RAM of 9.28 GB; the adaptive
run passed with 9.11 GB. Both stayed above the six-GiB floor and recorded zero
sampled OOM kills. Raw files and supervisor data remain in `/tmp/e6-65k-fixed-prefix8-gdn-dump/`,
`/tmp/e6-65k-fixed-prefix8-gdn-dump-supervisor/`,
`/tmp/e6-65k-adaptive-prefix8-gdn-dump/`, and
`/tmp/e6-65k-adaptive-prefix8-gdn-dump-supervisor/` on Orin. These are
instrumented state diagnostics, not performance measurements.

### Layer-2 MoE input and route comparison

The same pair also captured layer-2 MoE inputs, routed expert IDs and final
owner kinds at positions 65,536–65,542 (the seven generated-token dispatches
after the first accepted token). All seven route-ID and owner-kind arrays
matched between fixed and adaptive arms. There were 61 CPU-owned and nine
GPU-owned expert rows across these seven dispatches in each arm. The captured
layer-2 input activations matched exactly at six positions. At position
65,540, 798 of 2,560 float values differed; maximum absolute difference was
`2.4e-7`, relative L2 was `5.12e-8`. The route IDs and owners at that dispatch
still matched. These activations enter layer 2's MoE, so this observation
places a small input delta before that layer's MoE output; it does not identify
where the upstream delta originated or explain the larger recurrent-state
difference at prefix 8. The paired output-token hash and raw prefix-8 GDN
hashes reproduce the prior capture exactly. Minimum available RAM was 9.28 GB
fixed-owner and 9.16 GB adaptive; both runs passed with zero sampled OOM kills.
Route/activation files and supervisor logs remain in the corresponding
`/tmp/e6-65k-{fixed,adaptive}-layer2-route*` paths on Orin.

### Layer-1 expert ownership and service-output oracle

The matched layer-1 captures at the same seven positions found identical
inputs and expert IDs throughout. At position 65,540, expert 3 alone changed
owner among the ten routed experts: fixed-owner assigned it to GPU (`route_kind
= 0`), while adaptation assigned it to CPU (`route_kind = -1`). The other
nine owner assignments matched. The complete service MoE bundles at that
position confirm byte-identical input, routes, weights and shared output. The
round-4 adaptation log records the layer-1 swap `1:320>3`: expert 320 was
loaded into expert 3's slot. The update was queued and applied at position
65,539; at the next layer-1 dispatch, position 65,540, expert 3 was CPU-owned.
This ties the observed owner change to that adaptive swap.

The expert-3 service output changed in 1,840/2,560 values (maximum absolute
`1.49e-8`, relative L2 `1.059e-7`); the combined MoE output changed in
737/2,560 values (maximum `3.73e-9`, relative L2 `4.345e-8`).

Using the exact same captured 2,560-value activation, `native_expert_parity`
reported a CPU/GPU output difference at relative L2 `9.51e-8`. More directly,
the fixed-owner service expert-3 row matched the independent native GPU row
bit-for-bit, and the adaptive service row matched the native CPU row
bit-for-bit. The shared output was identical. This identifies the local
service expert-row change with its CPU/GPU ownership transition for this
dispatch. At that same token position, the layer-2 MoE input had the small
`5.12e-8` relative-L2 delta recorded above; the prefix-8 raw GDN capture first
differed in allocation 2 (model layer 2). This links one changed active expert
to an observed downstream activation delta in the sampled commit interval.
It does not prove that this is the only adaptive owner change or the sole
cause of every differing recurrent-state byte.

Both complete-bundle runs passed supervision and reproduced the same 32-token
output hash. Minimum available RAM was 9.21 GB fixed-owner and 9.10 GB
adaptive, with zero sampled OOM kills. Their raw `STMOEBN1` bundles remain in
`/tmp/e6-65k-{fixed,adaptive}-layer1-bundle/`; the independent activation and
parity outputs remain in `/tmp/e6-layer1-position65540-*` and
`/tmp/e6-layer1-expert3-parity-output/`. These are correctness diagnostics,
not performance measurements.

### Layer-0 route and activation control

To check for an earlier owner transition, the same seven-position interval was
captured at model layer 0. At every position, fixed and adaptive runs had the
same routed expert IDs, owner kinds, and all 2,560 MoE input values. Both runs
reproduced the same output-token hash and prefix-8 raw GDN dump hashes. Minimum
available RAM was 8.57 GiB fixed-owner and 8.44 GiB adaptive; both passed with
zero sampled OOM kills. This rules out a layer-0 route, ownership, or input
difference at these seven sampled positions. It does not rule out differences
at unsampled positions or other model layers. Raw captures and supervisor logs
remain in `/tmp/e6-65k-{fixed,adaptive}-layer0-route*` on Orin.

### All-layer comparison at the changed dispatch

The fixed and adaptive runs were repeated with one all-layer MoE bundle at
position 65,540. The capture contains route IDs and weights, MoE inputs, each
selected expert's output, shared output and combined output for all 47 model
layers. Both runs passed and reproduced the same 32-token output hash
(`2d5f3da8…`). Minimum available RAM was 8.62 GiB fixed-owner and 8.44 GiB
adaptive, with zero sampled OOM kills. The raw bundles remain in
`/tmp/e6-65k-{fixed,adaptive}-all-layer-bundle/`; the compact numeric
comparison is checked in as
[`all-layer-position65540-comparison.json`](all-layer-position65540-comparison.json).

The first small MoE-output difference remains layer 1, where only expert 3's
row changes under the verified GPU→CPU transition. Layer 0 is exact. The
layer-2 MoE input first differs by relative L2 `5.11e-8`, and small input and
route-weight changes accumulate through layer 12. A larger change is present
by layer 13: its input differs by relative L2 `3.45e-4`; all 25,600 captured
expert-part values differ (combined relative L2 `6.92e-3`); shared output
differs by `4.29e-3`; and combined output differs by `5.47e-3`. The ten route
IDs still match there and continue matching through layer 16. Route IDs first
differ at layer 17 and also differ at layers 18, 22, 23, 24, 32, 39 and 42.
This identifies a second, later numerical transition after the layer-1 delta
has propagated, but does not yet attribute it to ownership, input
quantization, or a kernel. Same-token output does not establish accepted-state
parity.

At this point the all-layer bundle identifies where the larger row delta
appears, but cannot separate changed input from changed execution owner. The
following owner and oracle capture makes that distinction for the sampled
experts; the result remains limited to this prompt, build, profile and
dispatch.

### Active-owner service-row oracle comparison

The round-4 adaptive schedule also promotes active experts at layers 3, 6 and
11 (`3:229>8`, `6:285>0`, `11:234>3`), in addition to layer-13 experts 474,
385 and 250. At position 65,540, the fixed and adaptive route IDs match for
all these experts. For layers 3, 6 and 11, each fixed service row matches the
independent CPU oracle bit-for-bit and each adaptive service row matches the
GPU oracle bit-for-bit. The fixed-input CPU/GPU oracle difference is only
`1.12–1.14e-7` relative L2 for these rows. Their fixed/adaptive float inputs
differ slightly, but the same-owner oracle outputs remain byte-identical
across those inputs; the observed row change is therefore the small CPU/GPU
execution delta at these sampled dispatches.

At layer 13 the owner capture directly shows experts 474, 385 and 250 moving
CPU→GPU: fixed kinds are `-1`, adaptive kinds are `0`. Their service rows also
match the corresponding CPU and GPU oracle outputs bit-for-bit. On the exact
same input, CPU/GPU oracle differences remain about `1.1e-7` relative L2. But
the fixed/adaptive layer-13 input differs by `3.45e-4`; applying either CPU or
GPU oracle to the two different inputs changes each row by `5.99–6.68e-3`
relative L2, essentially the same as the actual service-row change. This
separates the large layer-13 row delta from the tiny same-input CPU/GPU numeric
delta: the changed layer-13 input is the dominant factor in these rows. The
trace does not yet identify which earlier small transition(s) cause that
input drift or prove a sole cause of the prefix-8 recurrent-state mismatch.

The direct owner capture, matched service rows and independent oracle metrics
are summarized in
[`active-owner-oracle-position65540.json`](active-owner-oracle-position65540.json).
Oracle output dumps and activations remain in `/tmp/e6-layer{3,6,11,13}-*` on
Orin. This is a numeric diagnostic, not performance or semantic-quality
evidence.

### Layer-13 GDN stages and committed state

A matched GDN capture at the same position shows the layer-13 input `x`
differing by only `1.56e-7` relative L2 while the projected `qkv` is
bit-identical. The recurrent `h` output already differs by `2.52e-5`; `y`
differs by `1.45e-5`, and the normalized `gdn_out` by `1.05e-3`. The resulting
MoE input is the `3.45e-4` delta from the all-layer bundle. The state committed
after position 65,540 differs in 795,106/817,152 values (relative L2
`2.35e-5`); its 786,432-value recurrent matrix differs by `1.28e-5`, and the
30,720-value convolution history by `2.35e-5`. Both runs still emit the same
32 tokens. This places the larger change inside the recurrent GDN computation
despite identical projected `qkv`; it does not say whether the GDN state was
already different before this token or how that difference arose.

The full stage and committed-state metrics are in
[`gdn-layer13-position65540-comparison.json`](gdn-layer13-position65540-comparison.json).
Raw dumps remain in `/tmp/e6-65k-{fixed,adaptive}-layer13-gdn/` on Orin. Next
capture pre/post recurrent state at layer 13 over the first generated positions
to determine whether the state delta is present before the sampled recurrent
update. Then trace its first appearance through the earlier GDN layers and
accepted prefixes. These remain correctness diagnostics; captured rates are
not performance evidence.

### Layer-13 state onset across generated positions (2026-10-31)

The fixed-owner and adaptive-owner captures now record layer-13 GDN state
immediately before and after selected token updates at positions 65,536–65,540.
Both supervised requests passed, emitted 32 identical token IDs (SHA256
`2d5f3da8f9890f8c9262231bada2cfab088196528565a1c08ab685d86074c650`), and
preserved the six-GiB host-memory floor. Minimum available memory was 8.53 GiB
fixed-owner and 8.39 GiB adaptive; elapsed times were 821.2 and 821.8 seconds.
These are instrumented diagnostic runs, not throughput measurements.

Layer-13 pre-state and post-state are bit-identical between arms through the
update at position 65,538. The pre-state at position 65,539 is also identical,
but the post-state first differs after processing token ID 1,928 at position
65,539: 786,870 of 817,152 values differ, with relative L2 `2.3215e-5` and
maximum absolute delta `3.4812e-4`. That exact state appears as the adaptive
pre-state at position 65,540. After the next update, the state difference is
795,106 values with relative L2 `2.3541e-5`. Within each arm, every captured
post-state exactly equals the next position's pre-state, validating alignment
and continuity of the dump.

This resolves the immediate timing ambiguity: layer 13 does not enter position
65,540 with a pre-existing cross-arm state difference; the first sampled
layer-13 divergence is created by the update at position 65,539. The earlier
position-65,540 stage capture's equal `qkv` but different recurrent `h` is
consistent with that changed pre-state. The sequence alone did not identify which layer-13 input or recurrent
operation creates the difference at position 65,539, nor whether it is the first
differing state anywhere in the model. The matched GDN stage capture at that
position is now recorded below. Raw state binaries remain in `/tmp` on Orin; the
compact numeric comparison is in
[`gdn-layer13-state-sequence-comparison.json`](gdn-layer13-state-sequence-comparison.json).

### GDN input and recurrent stages at the first layer-13 state divergence

The matched GDN capture at position 65,539 passed in both arms and again
produced the same 32 output tokens. Minimum available memory was 8.70 GiB
fixed-owner and 8.43 GiB adaptive; neither run crossed the six-GiB floor. The
layer-13 state entering this update was already shown bit-identical by the
pre/post sequence capture. At the GDN block input `x`, 2,143/2,560 values differ
(relative L2 `1.80e-7`, max absolute `4.77e-7`). The projected `qkv` then differs
in 10,236/10,240 values (relative L2 `4.26e-5`, max absolute `3.48e-4`), before
recurrent output `h` differs by relative L2 `3.03e-5`. The same position's
post-state differs by relative L2 `2.32e-5`; its convolution history differs
in 10,236/30,720 values. Gate and beta remain near `1e-7`; `z` differs by
`2.03e-5`, `y` by `4.23e-5`, and normalized `gdn_out` by `1.25e-3`. The layer's
MoE input differs by `3.07e-4` and its FFN output by `5.29e-3`.

This places a small input delta before a much larger `qkv` delta at the exact
update that first changes layer-13 state. The incoming recurrent state is
identical, so the state mismatch is generated during this update, not inherited
by layer 13. The capture alone cannot tell whether the qkv change is the
expected response to the slightly different `x`, a projection arithmetic
sensitivity, or another upstream execution effect; it also does not identify
the source of the `x` difference. A fixed-input projection oracle or matched
single-arm replay of both captured `x` rows is needed before assigning cause.
The compact comparison is in
[`gdn-layer13-position65539-comparison.json`](gdn-layer13-position65539-comparison.json).

#### Native projection replay and scale counterfactual

The captured layer-13 `x` rows were replayed through native CUDA
`native_quantize_q8_1` and `native_q3_k_mmvq` with the actual Q3_K
`blk.13.attn_qkv.weight` bytes. Both replay outputs match their corresponding
captured `qkv` vectors bit-for-bit. The Q8_1 integer codes match across arms;
only block 57's stored FP16 scale differs. Replacing just the adaptive block
57 scale with the fixed-owner value makes the adaptive replay bit-identical to
the fixed capture. This isolates the sampled layer-13 `qkv` difference to that
one activation scale. The result does not locate the earlier source of the
`x` delta and does not by itself explain the full recurrent-state difference.
See [`layer13-qkv-scale-counterfactual-position65539.json`](layer13-qkv-scale-counterfactual-position65539.json).

### Layer-12 boundary feeding the layer-13 GDN update

A paired boundary capture at position 65,539 confirms the layer-13 input delta
is already present at the layer-12/13 boundary. Both runs passed, produced the
same 32 tokens, and recorded zero sampled cgroup OOM kills; minimum available
memory was 8.45 GiB fixed-owner and 8.38 GiB adaptive. The layer-12 residual
stream differs by relative L2 `1.11e-7`, its MoE stream by `2.13e-7`, and the
next-layer post-read stream by `1.15e-7`. The next-layer `xn` bundle differs by
`1.53e-7`, close to the layer-13 GDN `x` difference of `1.80e-7` in the paired
capture. Thus the layer-13 projection is receiving a small upstream boundary
delta before its `qkv` projection expands it. All boundary fields are reported
in [`layer12-boundary-position65539-comparison.json`](layer12-boundary-position65539-comparison.json).
This one-layer boundary does not reveal where the layer-12 difference first
arose; an all-layer position-65,539 trace is the next localization step.

### All-layer MoE trace at position 65,539

The 47-layer bundle at the first layer-13 state-divergence token finds an
upstream first delta at model layer 5. Layers 0–4 have identical MoE inputs,
routes, weights, expert rows, shared outputs and combined outputs. At layer 5,
the input, ten route IDs and route weights are still exact, but expert 220's
row differs in 1,868/2,560 values (relative L2 `1.14e-7`, max absolute
`1.49e-8`); shared output remains exact and combined output differs by
`5.77e-8`. The adaptive round-4 schedule includes `5:220>8`, applied at
position 65,539 before this dispatch. This is a strong owner-transition match;
the direct owner capture and fixed-input CPU/GPU oracle are the next checks.

The layer-5 output delta appears in layer-6 input (relative L2 `7.54e-8`) and
then propagates. Routes first differ at layer 17. At layer 7, expert 225 also
changes row and the shared path changes, but layer-7 input has already drifted;
that later bundle delta is not an independent first cause. The identical token
hash persisted through both runs. Min available memory was 8.55 GiB fixed and
8.44 GiB adaptive, with zero sampled OOM kills. See
[`all-layer-position65539-comparison.json`](all-layer-position65539-comparison.json).

### Direct owner and independent oracle check for layer-5 expert 220

The focused owner capture confirms expert 220 is CPU-owned (`route_kind=-1`)
in the fixed arm and GPU-owned (`route_kind=0`) in the adaptive arm at position
65,539, exactly after round-4 swap `5:220>8`. Both captures have identical
activation bytes, route IDs and route weight for this expert. The service row
from the fixed all-layer bundle matches `native_expert_parity`'s CPU row
bit-for-bit; the adaptive service row matches its GPU row bit-for-bit.

The native CPU/GPU rows differ by relative L2 `1.14e-7` (1,868/2,560 values,
maximum absolute `1.49e-8`). An independent scalar Q2_0 decoder with Q8_1
activation quantization and FP64 accumulation differs from the native CPU and
GPU outputs by relative L2 `9.74e-8` and `6.14e-8`, respectively. The service
rows are therefore consistent with the independent Q2_0/Q8_1 arithmetic, and
the local layer-5 combined-output delta is attributable to the owner change at
this dispatch. This verifies the earliest changed expert row sampled at this
position; it does not prove that this is the sole owner transition contributing
to all subsequent state drift. See
[`layer5-expert220-owner-oracle-position65539.json`](layer5-expert220-owner-oracle-position65539.json).

### Layer-7 expert 225 after the layer-5 activation delta

The later round-4 promotion `7:225>1` also changes the layer-7 expert row.
Layer-7 inputs already differ by relative L2 `1.29e-7`, and this expert's route
weight changes by `1.49e-8`. Replaying each captured input through the native
CPU and GPU expert paths shows the input change alone produces bit-identical
expert-225 rows on each owner. The fixed service row matches CPU and the
adaptive row matches GPU bit-for-bit; the owner-specific row gap is relative
L2 `1.05e-7`, same as the observed service-row delta. However the shared output
also changes (`8.69e-8`), so the combined layer-7 MoE delta (`1.43e-7`) includes
both routed-owner and shared/weight effects. This is a later contributor after
the layer-5 onset, not the first cause. See
[`layer7-expert225-owner-oracle-position65539.json`](layer7-expert225-owner-oracle-position65539.json).
