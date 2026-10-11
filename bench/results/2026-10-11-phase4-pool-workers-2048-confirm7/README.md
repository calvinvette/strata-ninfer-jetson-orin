# Seven-pair CPU expert-pool worker confirmation — Orin — 2026-10-11

This randomized seven-block confirmation compares 4 versus 8 CPU expert-pool
workers on the held-out 2,048-token prompt with 128 generated tokens. It uses
the IQ1_M Coder model with Q2_0 MTP, CPU prefill sharing disabled, requested
3,000-slot expert cache (3,903 admitted slots), prefill chunk 64, and 4,096
context. Each worker-count process had a separate warmup before the timed API
request. Timing runs disabled engine, state and allocation tracing. The engine
SHA-256 was
`facca01aaf48730f0098fb67b254dd0f42cc063403b03834ed84fa41211dbb83`.

All 14 requests passed. Every request admitted 3,903 cache slots and produced
the same output digest; the exact prompt contained 2,048 tokens and every
request generated 128 tokens. Eight workers had a 69,955.1 ms median request
time versus 71,642.5 ms for four workers (2.36% lower). Median prompt time was
61,544.2 versus 62,307.2 ms, and median decode time was 8,303.4 versus 9,332.9
ms. The seven paired request-time deltas for four relative to eight workers
were `+6.41, +3.54, +1.86, +2.41, −4.81, +1.16, +1.84%`; the runner's paired
bootstrap 95% interval for the median was +1.16% to +3.54%. Eight workers were
faster in six of seven pairs. This confirms a modest request-time benefit for
one 2,048/128 workload under this fixed cache and CPU-prefill policy.

The six-GiB physical-memory supervisor completed all 14 cells. Minimum host
`MemAvailable` was 14,191,742,976 bytes (13.22 GiB). Read-only sampled CPU
frequencies ranged from 729 to 2,202 MHz, GPU from 306 to 1,300.5 MHz, and EMC
was 3,199 MHz. Tegrastats reported junction temperature from 50.1 to 61.6 C
and GR3D utilization from 0 to 99%. Clocks remained dynamic; the whole-board
energy rail was not integrated into this campaign. These factors and one
four-worker paired outlier limit causal attribution and generalization.

This is timing-only evidence. Persistent state and accepted-prefix commits
were not traced in these 14 cells; separate state checks exist for the shorter
worker screen. Task-level quality, other cache sizes, prefill-sharing policies,
and additional held-out workloads remain open. No default changed, and this
does not close Phase 4.

Reproduce with the integration venv using the command recorded in
`supervisor/result.json`. `config.json`, `workloads.json`, `experiment/`, and
`supervisor/` retain the effective configuration, exact tokenized workload,
all per-cell API/engine records, paired samples, memory/clock observations and
raw tegrastats. The model and build remain outside Git. The candidate binary
was built from repository revision `1d2ce479eec1adc17b76095bbfb42251db3f9385`.
