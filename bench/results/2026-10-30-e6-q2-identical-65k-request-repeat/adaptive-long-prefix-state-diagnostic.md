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

## Next diagnostic

Fix route capture so both requests are tagged by request ID, then capture
accepted-prefix state around the first adaptive swap and the corresponding
replay position. The controlled toggle supports adaptation as a factor but
does not connect a specific expert transfer to the state delta.
