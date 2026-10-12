# Q2_0 32K prompt at 64K context, 20-GiB scope, 5,000 slots — Orin — 2026-10-12

This repeats the 5,000-slot cell from the [22-GiB cache/context screen](../2026-10-12-phase3-q2-actual32k-context64k/README.md) under a transient 20-GiB cgroup `MemoryMax`. It used the same exact 32,768-token prompt (SHA-256 `705dea47aafbfc991d0616621f3a13bf0136a43c546d60c7693c2efdced4d3a3`), Q2_0 artifacts, 65,536-token configured context, 3,072 MiB workspace reserve, 512-token prefill chunks, two-token speculation window, and 5,000 requested expert-cache slots. No model was copied into the repository.

The request consumed the full prompt and emitted token ID 32. The final persistent-state fingerprint and all 36 per-layer GDN fingerprints exactly match the prior 22-GiB/5,000-slot process. This is an exact state repeat across these two memory-cap runs; it does not resolve the separate cache-capacity-dependent state difference between the 3,000- and 5,000-slot configurations.

| Result | Value |
|---|---:|
| Supervisor | pass; 6-GiB effective-headroom floor retained |
| Minimum host `MemAvailable` | 14,893,555,712 B (13.87 GiB) |
| Minimum effective cgroup availability | 10,067,988,480 B (9.38 GiB) |
| Prompt-stage time | 164,134.2 ms (descriptive only) |
| File-cache hits | 111/480 |
| Requested device allocation peak | 10,649,721,344 B (9.92 GiB) |
| Owner events | 304 allocations / 303 frees; 1,485,606,400 B service-lifetime weight arena live at log end |
| Cgroup OOM / OOM-kill events | 0 / 0 |

The lower configured cap did not imply lower effective headroom than the 22-GiB run: measured cgroup/page-cache charges differed. This single sequential repeat does not establish a minimum RAM requirement or cap monotonicity. Requested owner bytes omit driver-private and graph-pool backing; host availability and cgroup ancestry remain the admission measures. Timing is not compared because this was not a randomized paired campaign. Raw supervisor samples, engine log, workload record and parsed owner summary are retained here.

Reproduce from the repository root with the matching config and runner shown in `supervisor/result.json`; the exact launch was a `systemd-run --scope -p MemoryMax=20G -p MemoryAccounting=yes` invocation around `tools/integration/run_control.py --timeout 1800 --privileged-emc`, retaining its six-GiB floor. The executable SHA-256 was `bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.
