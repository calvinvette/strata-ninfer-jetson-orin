# Adaptive long-request then prefix state diagnostic

Date: 2026-10-30  
Host: Jetson AGX Orin 64 GB, CUDA 12.6  
Model: Qwen3.8-Flash-Next Q2_0, same local model and rendered token prefix as the E6 65K repeat runs  
Build/profile: current `feat/ninfer-expert-e0` Strata/NInfer binary, original Q2 expert profile, adaptive expert swaps enabled  
Purpose: determine whether an intervening long request changes persistent state for an identical short prompt prefix.

## Result

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

The long request ran at 86.7 prompt tok/s and 1.3 decode tok/s; its GPU cache
hit rate was 32.9% (5,052/15,360), with 117 expert exchanges and 8,939 file
blob reads. The 8K replay ran at 75.0 prompt tok/s and 0.4 decode tok/s, with
10.4% GPU cache hits (50/480), 129 exchanges and 9,288 cumulative file reads.
These are instrumented diagnostic rates and must not be compared as a backend
performance result.

The 8K prefix is known to repeat exact persistent state over three requests
with adaptation enabled when run alone; it also repeats exact state over three
requests with adaptation disabled using the original profile. Thus the long
request history is associated with this state change, but the run does not
identify whether adaptation, expert ownership, request reset/commit ordering,
or another long-context path caused it. Route instrumentation wrote one data
row rather than a row for both requests, so owner-map change is unproven. The
single replay's matching first token is not evidence of matching state or
semantic quality.

The supervisor passed: minimum available physical memory was 8.58 GiB,
above the preserved 6 GiB floor; sampled OOM kills were zero. Raw run material
is in `/tmp/e6-65k-long-then-prefix-layer1/` and supervisor telemetry in
`/tmp/e6-65k-long-then-prefix-layer1-supervisor/` on the Orin. The owner dump
was intentionally not checked in because its one-row capture is incomplete.

## Next diagnostic

Fix the route-capture harness so it records both requests with explicit request
IDs and no global row cap, then repeat the long→prefix sequence. If ownership
is unchanged, localize state movement by comparing accepted-prefix checkpoints
and reset/commit operations; do not infer a cache-owner cause from cache-hit
rates alone.
