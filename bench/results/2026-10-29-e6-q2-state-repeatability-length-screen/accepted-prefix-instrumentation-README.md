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

## Sampled capture with full tracing disabled — 2026-10-30

The per-commit path was changed to support an opt-in stride while retaining the
first and final checkpoint. The API harness gained
`--accepted-prefix-trace`, which keeps this capture enabled alongside
`--no-trace` while leaving full `STRATA_TRACE` disabled. The default stride is
still one, preserving full accepted-prefix capture. The diagnostic used stride
8, `STRATA_STATE_HASH=1`, the same 65,536-token prompt and 128-token warmup,
then a 32-token measured request. It ran one NInfer arm and one Strata arm on
the current CUDA build. Both supervisor records passed.

Warmup outputs matched byte-for-byte, and all 17 sampled accepted-token IDs and
all persistent-state fingerprints matched across backends. On the measured
request, the first and eighth sampled token IDs still matched, but the state
fingerprints differed at the first sampled checkpoint, after the shared first
token. The differing fields were GDN, tail, pooled, pooled-full and KV. By the
16-token checkpoint, sampled token IDs also differed; the first visible text
difference followed 52 common characters. Strata's measured text matched its
warmup text, while NInfer's did not. This reproduces the divergence with full
tracing disabled and coarse state sampling enabled. The capture still performs
synchronization and state hashing at checkpoints, so it is not equivalent to a
completely uninstrumented run.

| Arm | Measured prompt tok/s | Measured decode tok/s | Elapsed | Minimum available RAM | Peak swap |
| --- | ---: | ---: | ---: | ---: | ---: |
| Strata | 85.8 | 0.3 | 2,012.4 s | 8.60 GiB | 0.73 GiB |
| NInfer | 86.0 | 0.3 | 2,009.7 s | 8.67 GiB | 1.83 GiB |

These are single-arm diagnostic readings, not a performance comparison: the
measured outputs diverged and there was one run per backend. Minimum available
RAM stayed above the 6 GiB floor, swap peaked at 1.83 GiB, and cgroup OOM-kill
counters remained zero. Energy was not measured. The sanitized comparison,
sampled token checkpoints and field-level state differences are in the
[updated summary JSON](accepted-prefix-instrumentation-summary.json); raw logs
and telemetry remain local-only.

The opt-in prompt-boundary hash records state after the first verifier window
has processed the final prompt token and before the first commit. The CUDA
build and a short API smoke passed; both 512-token requests emitted one
boundary record with full `STRATA_TRACE` disabled.

### Prompt-boundary pair — 2026-10-30

The matched high-context pair used the exact same 65,536-token prompt for both
the 128-token warmup and 32-token measured request. Both arms passed. The
warmup prompt-boundary fingerprints and final fingerprints matched across
backends. On the measured request, the Strata and NInfer prompt-boundary
fingerprints already differed before the first generated-token commit. The
different fields were GDN, tail, pooled, pooled-full and KV. Within each
backend, the boundary fingerprint also differed between the warmup and measured
requests despite identical prompt content: Strata changed those five fields;
NInfer changed GDN, pooled, pooled-full and KV. Both measured responses
differed from their warmup response and from each other; the cross-backend
responses shared 52 initial characters before diverging. This locates the
measured state difference before the first commit, but does not determine
whether it originates during prompt evaluation or in request-history/state
handling.

| Arm | Measured prompt tok/s | Measured decode tok/s | Elapsed | Minimum available RAM | Peak swap |
| --- | ---: | ---: | ---: | ---: | ---: |
| Strata | 86.2 | 1.4 | 1,637.1 s | 8.57 GiB | 4.72 GiB |
| NInfer | 86.1 | 1.4 | 1,638.2 s | 8.55 GiB | 1.92 GiB |

These are single-arm diagnostic readings, not a performance comparison: the
measured outputs differed and there was one run per backend. Cgroup OOM-kill
counters were zero; energy was not measured. The prompt-boundary hash
synchronizes the device, so the run is not entirely uninstrumented. The
sanitized per-request hashes, state fields and resource data are in the
[summary JSON](accepted-prefix-instrumentation-summary.json); raw logs and
telemetry remain local-only.

The next work should determine why an identical second prompt does not produce
the same boundary state after a long warmup, and whether request reset,
prompt-cache or persistent-state lifecycle explains the result. E6 and E7
remain open, and no backend performance claim or release profile is justified.

Sanitized paired results and the first-checkpoint state comparison are in
[accepted-prefix-instrumentation-summary.json](accepted-prefix-instrumentation-summary.json).
Full server logs, memory samples and trace captures remain local-only.
