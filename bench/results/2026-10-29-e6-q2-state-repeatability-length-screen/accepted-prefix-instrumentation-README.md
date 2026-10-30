# 64K accepted-prefix instrumentation diagnostic

Date: 2026-10-29. Hardware: Jetson AGX Orin. Model: the same Q2_0 cohort as
the [64K no-trace API screen](no-trace-api-pp65536-cap131072-README.md).

## Purpose and method

The no-trace screen used greedy decoding (`temperature=0`) and found that the
first Strata/NInfer pair shared only 52 characters between measured responses.
The warmup response text matched across backends. To locate a state divergence,
we compared Strata and strict NInfer with accepted-prefix state fingerprints at
the 65,536-token prompt and 131,072-token context. Both arms used the original
65,536-token prompt and 128-token generation as warmup, then the same prompt
with a 32-token measured generation. The measured cap was shortened to bound
the diagnostic while covering the initial divergence window.

The server ran with `STRATA_TRACE=1`,
`STRATA_ACCEPTED_PREFIX_TRACE=1`, and `STRATA_STATE_HASH=1`. Both runs passed.
At every one of the 32 measured commit checkpoints, the accepted token ID and
all ten persistent-state fingerprints matched across backends. Both measured
responses also matched for all 32 tokens. Minimum available RAM was 8.65 GiB
for each arm; peak sampled swap was 1.15 GiB for NInfer and 1.12 GiB for Strata;
cgroup OOM counters remained zero. The traced requests took about 76 minutes
per arm, and their measured rates are excluded from performance analysis.

## What this shows

Accepted-prefix tracing did **not** reproduce the no-trace response divergence
within the first 32 generated tokens. In a separate NInfer comparison, the
first generated token ID was still 32 after either a 512-token/one-token
warmup or the 65K/128-token warmup, but the first measured state fingerprints
differed in GDN, pooled state, pooled-full state, and KV. This shows that
warmup history changes the captured state while the visible first token stays
the same. The two warmups differ in both prompt length and generated length, so
this does not isolate which setting changed the state.

The no-trace block-0 responses still differ after a 52-character common prefix:
Strata continues with “synchronized dance,” while NInfer continues with
“coordinated sequence.” The instrumented pair instead matched. Therefore this
trace is not a faithful explanation of the no-trace divergence. Its heavy
synchronization and logging may change execution behavior; the result leaves
the no-trace cause unresolved. Fingerprints show equality only, not numerical
error magnitude, and no semantic quality oracle was used.

## Next diagnostic

Replace per-commit synchronous logging with an opt-in buffered or sampled
checkpoint capture, then repeat the same no-trace workload with matched
warmup and measured requests. First verify that the diagnostic preserves the
no-trace output path. Do not use these instrumented rates as performance
evidence. E6 and E7 remain open, and no backend performance claim or release
profile is justified.

Sanitized paired results and the first-checkpoint state comparison are in
[accepted-prefix-instrumentation-summary.json](accepted-prefix-instrumentation-summary.json).
Full server logs, memory samples and trace captures remain local-only.
