# MTP cancellation state parity with corrected engine environment — Orin — 2026-10-12

This rerun corrected a harness control issue: `serve.server.child_env()` uses
the config's `env` mapping for engine overrides, so setting
`STRATA_PREFILL_CPU_SHARE=0` only in the parent process did not override the
source config's value of `0.5`. The updated harness writes the effective
instrumentation and prefill settings into every generated server config. The
cancel config records CPU prefill share `0`.

The cancellation request, same-process recovery, and all three fresh
exact-length reference requests completed under the six-GiB supervisor. The
references produced the same output tokens as cancellation and were token- and
state-repeatable with each other. Cancellation state hashes still differ from
all three references at accepted lengths 48 and 52. The accepted-prefix state
parity gate therefore fails under the corrected configuration; no timing
comparison is made. This is a Phase 5 correctness issue, not Phase 3 evidence.

Minimum host availability was 9.68 GiB. Dynamic CPU/GPU/EMC clocks were
sampled; energy was not measured. The reference processes independently chose
expert-cache sizes because they ran sequentially with automatic sizing; this
does not affect the comparison of accepted-prefix fingerprints but limits
interpretation of their resource observations.

Earlier repeat-3 and float-state diagnostic runs used the inherited `0.5`
config override and must not be treated as zero-CPU-prefill controls. Their
raw state dump binaries were removed after deriving the retained JSON numeric
comparisons to avoid storing 338 MiB of generated diagnostics. The original
result JSON/logs and numeric summaries remain available.
