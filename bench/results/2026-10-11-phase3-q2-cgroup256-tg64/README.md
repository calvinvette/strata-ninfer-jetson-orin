# Q2_0 64-token decode under cgroup caps — Orin

This follow-up tests the same Q2_0 configuration at longer generation length:
512-token prompt, up to 64 greedy output tokens, requested 256 expert slots,
4K context, native spec2, no MTP, PLE mmap, 3 GiB workspace reserve and the
six-GiB effective-availability supervisor. Each cap ran in a fresh transient
cgroup-v2 scope. Exact commands, actual cache slots, host/cgroup telemetry and
terminal status are in the linked raw run directories. Artifacts are
identified in `artifact-identities.json` and stay under `~/models/`.

| Cgroup cap | Actual slots | Outcome | Minimum effective availability | Minimum host `MemAvailable` | Peak scope `memory.current` |
| ---: | ---: | --- | ---: | ---: | ---: |
| 9.5 GiB | 248 | Supervisor abort before prefill | 5.41 GiB | 23.15 GiB | 4.09 GiB |
| 10 GiB | 256 | Supervisor abort before prefill | 5.82 GiB | 21.74 GiB | 4.18 GiB |
| 12 GiB | 256 | Supervisor abort before prefill | 5.78 GiB | 21.67 GiB | 6.22 GiB |
| 16 GiB | 256 | Prefill completed; supervisor abort before request completion | 5.94 GiB | 21.62 GiB | 10.06 GiB |
| 18 GiB | 256 | Pass; emitted 64 tokens (token IDs recorded) | 11.35 GiB | 21.59 GiB | 6.65 GiB |
| 20 GiB | 256 | Pass; emitted 64 tokens (token IDs recorded) | 7.70 GiB | 21.72 GiB | 12.30 GiB |

The 64-token request passed at 18 and 20 GiB, while the 16 GiB request was
aborted after prefill. These are cell outcomes, not a supported-capacity
threshold. Observed cgroup `memory.current` varied substantially between
independent runs, consistent with cgroup file-cache charging; do not infer
incremental engine allocation or compare these peaks as process-only RAM.
Host `MemAvailable` remained above 21.5 GiB in every cell, so the aborts were
from the effective cgroup guard, not physical host pressure. Cgroup and host
memory measurements are distinct and are never added.

Raw cells: [9.5 GiB](../2026-10-11-phase3-q2-cgroup9p5G-cache256-tg64/supervisor/),
[10 GiB](../2026-10-11-phase3-q2-cgroup10G-cache256-tg64/supervisor/),
[12 GiB](../2026-10-11-phase3-q2-cgroup12G-cache256-tg64/supervisor/),
[16 GiB](../2026-10-11-phase3-q2-cgroup16G-cache256-tg64/supervisor/),
[18 GiB](../2026-10-11-phase3-q2-cgroup18G-cache256-tg64/supervisor/), and
[20 GiB](../2026-10-11-phase3-q2-cgroup20G-cache256-tg64/supervisor/).
