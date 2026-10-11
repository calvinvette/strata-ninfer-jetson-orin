# Q2_0 PLE I/O owner-traced diagnostic — Orin — 2026-10-11

Seven randomized process pairs compare `--ple-io direct` and `--ple-io mmap`
on the downloaded Q2_0 Coder model, using the same 512-token `pp512+tg64`
prompt, one greedy output token, 5,000 cache slots and 4,096 context. All
fourteen requests passed the six-GiB supervisor, emitted token ID 32 and used
exactly 5,000 actual cache slots. Minimum host `MemAvailable` was
17,211,617,280 bytes (16.03 GiB).

`STRATA_INTEGRATION_TRACE=1` was enabled to check ownership. Each run recorded
276 allocations and 276 frees, with zero live observed owner bytes at log end.
Median unique observed owner peaks were 7,192,758,528 requested device bytes and
354,389,880 host bytes. These counters cover instrumented owners only and do
not include graph executable/driver pools or other uninstrumented allocations.
They are not added to `MemAvailable`.

The instrumented prompt-time medians were 13,401.0 ms direct and 13,538.3 ms
mmap; paired deltas varied from −20.51% to +8.43%. Since owner tracing logs
allocation/view events on the prompt path, these timings are retained for
completeness but excluded from any transfer-performance conclusion. The PLE
counter stayed at 0.2–0.3 ms in both modes. Raw tegrastats had CPU frequencies
from 729 to 2,201 MHz, but no GPU or EMC clock values; request-scoped energy and
per-request disk bytes were unavailable. The tracing-off follow-up is reported
separately in [`../2026-10-11-phase3-q2-ple-mmap-untraced3/README.md`](../2026-10-11-phase3-q2-ple-mmap-untraced3/README.md).

The randomized order, commands, samples, raw output and owner summaries are
retained in this directory. [`analysis.json`](analysis.json) contains all seven
paired values and the bootstrap interval for reference only; it must not be
interpreted as an untraced transfer effect. Model and pack identities are
recorded in the sibling [Q2_0 admission report](../2026-10-11-phase3-q2-admission/artifact-identities.json).
This is owner-lifetime evidence, not an endorsement of either PLE read mode.
