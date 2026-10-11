# Q2_0 256-slot cgroup admission bracket — Orin

Four one-token Q2_0 requests used the same candidate binary and model/pack,
512-token prompt, requested 256 expert slots, 4K context, native spec2, no MTP,
PLE mmap, 3 GiB workspace reserve and six-GiB effective-availability guard.
Only the transient cgroup-v2 `MemoryMax` differed. Each result is an independent
process. Raw supervisor commands, stdout/stderr, host and cgroup samples, and
tegrastats are retained in the referenced cell folders. Artifact identities
are in `artifact-identities.json`; models remain under `~/models/`.

| Cgroup cap | Actual slots | Result | Min effective availability | Min host `MemAvailable` | Peak scope `memory.current` |
| ---: | ---: | --- | ---: | ---: | ---: |
| 8 GiB | 0 | Fail after prefill: missing residency table | 6.78 GiB | 22.11 GiB | 1.22 GiB |
| 9 GiB | 0 | Fail after prefill: missing residency table | 7.77 GiB | 22.00 GiB | 1.23 GiB |
| 9.5 GiB | 256 | Pass; emitted token 32 | 7.93 GiB | 21.14 GiB | 1.57 GiB |
| 10 GiB | 256 | Pass; emitted token 32 | 8.45 GiB | 21.44 GiB | 1.55 GiB |

The exact 256-slot configuration transitions between failure at 9 GiB and
success at 9.5 GiB in these observations. Failures were clean route errors,
not OOMs or supervisor aborts. This is an observed bracket for one model,
prompt, context, cache request and engine revision; it is not a generally
supported capacity threshold. Cgroup use and host availability are distinct
measurements and are never summed.

The cell runs are [8 GiB](../2026-10-11-phase3-q2-cgroup8G-cache256/README.md),
[9 GiB](../2026-10-11-phase3-q2-cgroup9G-cache256/supervisor/result.json),
[9.5 GiB](../2026-10-11-phase3-q2-cgroup9p5G-cache256/supervisor/result.json),
and [10 GiB](../2026-10-11-phase3-q2-cgroup10G-cache256/README.md). The 9 and
9.5 GiB cells use the same command as their neighboring reports with only
`MemoryMax` and output path changed; their exact commands are in
`supervisor/result.json`.
