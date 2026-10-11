# Q2_0 prefill-chunk admission screen under cgroup caps — Orin — 2026-10-11

This current-binary screen varies the prefill chunk at several active cgroup-v2
caps while holding the Q2_0 artifacts, 512-token prompt, requested 3,000-slot
cache, 4K context, `--spec 2`, workspace reserve, mmap path and one-token greedy
request fixed. The CUDA candidate SHA-256 is
`facca01aaf48730f0098fb67b254dd0f42cc063403b03834ed84fa41211dbb83`. All runs
used the standard six-GiB effective-availability supervisor. The effective
cgroup availability shown below is `admission_available_bytes` from the raw
sample stream; host `MemAvailable` remains the physical-memory authority and
was never added to cgroup or GPU capacity.

| Cgroup cap | Prefill chunk | Cache slots admitted | Minimum effective availability | Minimum host availability | Outcome |
| ---: | ---: | ---: | ---: | ---: | --- |
| 8 GiB | 32 | no cache admitted before abort | 5.03 GiB | 24.50 GiB | Supervisor pressure-aborted |
| 10 GiB | 32 | 447 | 6.00 GiB | 21.77 GiB | Supervisor pressure-aborted |
| 10 GiB | 512 | 295 | 5.99 GiB | 21.72 GiB | Supervisor pressure-aborted |
| 12 GiB | 32 | 2,037 | 5.78 GiB | 19.54 GiB | Supervisor pressure-aborted during prefill |
| 12 GiB | 512 | 1,744 | 8.06 GiB | 19.96 GiB | Passed; output token 32 |
| 16 GiB | 32 | 3,000 | 9.37 GiB | 18.33 GiB | Passed; output token 32 |
| 16 GiB | 512 | 3,000 | 8.23 GiB | 18.51 GiB | Passed; output token 32 |

These are single observations per cell, not a randomized replicated campaign.
The two 10-GiB runs both reached the guard floor. At 12 GiB, chunk 32 admitted
more cache but was stopped by the cgroup guard, while chunk 512 completed. At
16 GiB both chunks admitted the full requested cache and completed. The varying
starting file-cache state and cgroup charge, plus the small sample count, mean
these points do not establish a general capacity threshold or a chunk-size
performance effect. No timing or quality comparison is claimed, and no
configuration is promoted. The older 8-GiB/chunk-512 no-cache failure belongs
to a separate earlier screen and is not a same-binary pair.

A no-spec command was rejected before inference because this native Q2_0 pack
requires `--spec >= 2`; its command and setup error are retained in
`../2026-10-11-phase3-q2-cgroup8G-nospec/` and are not counted as a workload
cell.

Raw run-control samples, process logs and tegrastats are retained in the linked
per-cell directories: `../2026-10-11-phase3-q2-cgroup8G-prefill32/`,
`../2026-10-11-phase3-q2-cgroup10G-prefill32/`,
`../2026-10-11-phase3-q2-cgroup10G-prefill512-current/`,
`../2026-10-11-phase3-q2-cgroup12G-prefill32/`,
`../2026-10-11-phase3-q2-cgroup12G-prefill512-current/`,
`../2026-10-11-phase3-q2-cgroup16G-prefill32/`, and
`../2026-10-11-phase3-q2-cgroup16G-prefill512-current/`.
