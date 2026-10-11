# Current-binary Q2_0 configured-context admission screen — Orin — 2026-10-11

Five supervised one-token runs vary only `--max-context` from 4K to 64K. Every
run used the same current CUDA candidate
(`facca01aaf48730f0098fb67b254dd0f42cc063403b03834ed84fa41211dbb83`), Q2_0
native pack and PLE table shard, 512-token prompt, requested 3,000-slot expert
cache, prefill chunk 512, spec2, mmap experts, disabled prompt cache, 3-GiB
workspace reserve and greedy output. Integration allocation tracing was enabled
for owner counts; read-only CPU/GPU/EMC clocks were sampled with the standard
memory supervisor. No clocks were controlled.

| Configured context | Actual cache slots | Session backing requested | Peak unique device requests | Minimum host `MemAvailable` | Result |
| ---: | ---: | ---: | ---: | ---: | --- |
| 4,096 | 3,000 | 235,034,112 B (224.1 MiB) | 5,913,564,928 B | 18.51 GiB | Pass, token 32 |
| 8,192 | 3,000 | 343,102,976 B (327.2 MiB) | 6,021,650,176 B | 18.29 GiB | Pass, token 32 |
| 16,384 | 3,000 | 559,240,704 B (533.2 MiB) | 6,237,820,672 B | 18.20 GiB | Pass, token 32 |
| 32,768 | 3,000 | 991,516,160 B (945.1 MiB) | 6,670,161,664 B | 17.88 GiB | Pass, token 32 |
| 65,536 | 3,000 | 1,856,067,072 B (1.73 GiB) | 7,534,843,648 B | 17.12 GiB | Pass, token 32 |

The six-GiB physical-availability floor was maintained in all five runs. Every
owner summary balanced 278 allocation/free events and ended with zero observed
live requested bytes on host and device. Session backing increased linearly at
216,137,728 requested bytes per additional 8,192 context positions in this
configuration. The device-request peaks are unique live requested payloads from
instrumented owners, not physical GPU totals; driver and graph-pool allocations
are excluded. Host `MemAvailable` is the sole physical-memory authority and is
not added to CUDA or cgroup capacity.

This validates configured-context startup/admission for one short Q2_0 request
with a fixed cache. It does not ingest a long prompt, test long-context recall
or quality, measure concurrency, establish supported maximum context, or price
CUDA graph pools. Per-cell supervisor samples, owner summaries, raw engine logs
and clock observations are retained under `4k/`, `8k/`, `16k/`, `32k/` and
`64k/`. Model files remain under `~/models/`.
