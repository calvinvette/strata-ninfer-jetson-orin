# Q2_0 prefill-chunk admission confirmation at a 12 GiB cgroup cap — Orin — 2026-10-11

Three independent paired blocks compare prefill chunks 32 and 512 under a
12-GiB transient cgroup-v2 cap. Each cell used the same current CUDA candidate
(`facca01aaf48730f0098fb67b254dd0f42cc063403b03834ed84fa41211dbb83`), Q2_0
model and PLE pack, 512-token prompt, requested 3,000-slot cache, 4K context,
`--spec 2`, mmap experts, disabled prompt cache, 3-GiB workspace reserve and
one greedy output. Pair order alternated 32→512, 512→32, 32→512. The supervisor
kept the effective cgroup floor at six GiB; host `MemAvailable` remained the
physical-memory authority.

| Pair | Chunk 32: cache slots | Min effective availability | Outcome | Chunk 512: cache slots | Min effective availability | Outcome |
| ---: | ---: | ---: | --- | ---: | ---: | --- |
| 1 | 2,037 | 5.78 GiB | Pressure-aborted | 1,744 | 8.06 GiB | Pass, token 32 |
| 2 | 1,879 | 8.29 GiB | Pass, token 32 | 913 | 7.28 GiB | Pass, token 32 |
| 3 | 1,745 | 8.61 GiB | Pass, token 32 | 1,938 | 9.10 GiB | Pass, token 32 |

The 12 GiB chunk-32 case passed in two of three processes; all chunk-512 cells
passed. Admitted slot counts varied substantially within both arms (chunk 32:
1,745–2,037; chunk 512: 913–1,938), so the one pressure abort does not support a
general chunk-specific admission rule. Successful cells emitted token ID 32,
but this one-token screen does not establish output quality or persistent-state
parity. No timing comparison is made and no default changes.

Pair 1 raw data is retained in the one-shot screen's
`../2026-10-11-phase3-q2-cgroup12G-prefill32/` and
`../2026-10-11-phase3-q2-cgroup12G-prefill512-current/` directories. Pairs 2
and 3 are retained under `repeat2/` and `repeat3/` here. The earlier multi-cap
screen remains the source for 8/10/16-GiB cells. Starting file-cache charge and
cgroup memory state varied, so capacity qualification still needs repeated
workloads with state/quality checks and broader request lengths.
