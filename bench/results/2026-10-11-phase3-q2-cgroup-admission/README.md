# Q2_0 model under active cgroup caps — Orin — 2026-10-11

The same 512-token Q2_0 Coder request ran in independent transient cgroup-v2
scopes capped at 10, 12, 20 and 24 GiB. Each used `--expert-cache 3000`, 4,096
context, one greedy output token, no MTP, Q2_0 PLE mmap and the existing
three-GiB workspace reserve. `run_control.py` remained inside each scope and
enforced the six-GiB minimum effective-availability floor. Every request
completed and emitted token ID 32.

The requested cache budget did not equal residency under the tighter caps:
Strata admitted 296 slots at 10 GiB and 805 at 12 GiB, while the 20/24-GiB
scopes admitted all 3,000. This adaptive cache size is central to interpreting
the lower-cap successes.

| Cgroup memory cap | Actual cache slots / reported cache | Peak scoped `memory.current` | Minimum effective availability | Minimum host `MemAvailable` | Result |
| ---: | ---: | ---: | ---: | ---: | --- |
| 10 GiB | 296 / 0.38 GiB | 2.15 GiB | 7.85 GiB | 21.81 GiB | Pass |
| 12 GiB | 805 / 1.04 GiB | 5.01 GiB | 6.99 GiB | 21.57 GiB | Pass |
| 20 GiB | 3,000 / 3.86 GiB | 7.08 GiB | 12.92 GiB | 18.81 GiB | Pass |
| 24 GiB | 3,000 / 3.86 GiB | 10.27 GiB | 13.73 GiB | 18.48 GiB | Pass |

The 12-GiB scope was the tightest effective-headroom cell and stayed about
0.99 GiB above the supervisor floor. Scoped `memory.current` includes that
unit's charged process and file-cache pages; its peak varied across runs, so
these rows are not a minimum-capacity threshold or an allocation-demand
comparison. Host `MemAvailable` remained the physical-memory authority and was
never added to cgroup or device counters. Per-sample scope/host observations,
`tegrastats`, commands and outputs are in the linked run directories;
[`analysis.json`](analysis.json) summarizes the measured minima, actual cache
residency and scope peaks.

This extends the earlier IQ1_M cgroup screen to the actual Q2_0 model for one
cache request, context and one-token workload. It demonstrates successful
admission with cache contraction under tighter limits, not a general supported
capacity or recovery claim.
