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

## Next diagnostic

Compare the same accepted prefixes against a matched fixed-owner 65K request,
and capture per-layer state at the replay boundary to locate the first changed
component/layer. The selected layer-1 replay row is observable and its
route/owner record matches the short control, but the controlled toggle still
does not connect a specific expert transfer to the state delta.
