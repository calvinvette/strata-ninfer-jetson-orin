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

## Next diagnostic

Inspect the active-expert route, residency, and arithmetic path for model
layer 2 around accepted commits 2–8, using an independent oracle to distinguish
an owner-transfer effect from numerical or ordering variation. Keep causality
open until the state change is tied to a specific event. Matching QSA
fingerprints are not raw-byte parity; capture QSA bytes if their aggregate
mismatch becomes relevant to that causal trace.
