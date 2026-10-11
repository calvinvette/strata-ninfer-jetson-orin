# Q2_0 model under active cgroup caps — Orin — 2026-10-11

The same 512-token Q2_0 Coder request ran in independent transient cgroup-v2
scopes capped at 8, 10, 12, 20 and 24 GiB. Each used `--expert-cache 3000`, 4,096
context, one greedy output token, no MTP, Q2_0 PLE mmap and the existing
three-GiB workspace reserve. `run_control.py` remained inside each scope and
enforced the six-GiB minimum effective-availability floor. The 10/12/20/24-GiB
requests completed and emitted token ID 32; the 8-GiB cell failed cleanly, as
described below.

The requested cache budget did not equal residency under the tighter caps:
Strata admitted 296 slots at 10 GiB and 805 at 12 GiB, while the 20/24-GiB
scopes admitted all 3,000. This adaptive cache size is central to interpreting
the lower-cap successes.

| Cgroup memory cap | Actual cache slots / reported cache | Peak scoped `memory.current` | Minimum effective availability | Minimum host `MemAvailable` | Result |
| ---: | ---: | ---: | ---: | ---: | --- |
| 8 GiB | 0 / 0 GiB | 1.26 GiB | 6.74 GiB | 22.31 GiB | Fail after prefill: no residency table |
| 10 GiB | 296 / 0.38 GiB | 2.15 GiB | 7.85 GiB | 21.81 GiB | Pass |
| 12 GiB | 805 / 1.04 GiB | 5.01 GiB | 6.99 GiB | 21.57 GiB | Pass |
| 20 GiB | 3,000 / 3.86 GiB | 7.08 GiB | 12.92 GiB | 18.81 GiB | Pass |
| 24 GiB | 3,000 / 3.86 GiB | 10.27 GiB | 13.73 GiB | 18.48 GiB | Pass |

The 12-GiB scope was the tightest successful effective-headroom cell and stayed
about 0.99 GiB above the supervisor floor. At 8 GiB, no expert-cache slots were
admitted; prefill completed, then the speculative route failed explicitly
because no device residency table existed. The supervisor still observed 6.74
GiB minimum effective availability and 22.31 GiB host availability. This is a
failed support cell, not an OOM or supervisor abort. Scoped `memory.current` includes that
unit's charged process and file-cache pages; its peak varied across runs, so
these rows are not a minimum-capacity threshold or an allocation-demand
comparison. Host `MemAvailable` remained the physical-memory authority and was
never added to cgroup or device counters. Per-sample scope/host observations,
`tegrastats`, commands and outputs are in the linked run directories;
[`analysis.json`](analysis.json) summarizes the measured minima, actual cache
residency and scope peaks. Artifact identities are in the sibling [Q2_0
admission report](../2026-10-11-phase3-q2-admission/artifact-identities.json).

This extends the earlier IQ1_M cgroup screen to the actual Q2_0 model for one
cache request, context and one-token workload. It demonstrates successful
admission at the four sampled caps from 10 to 24 GiB, and a clean route failure
at 8 GiB when no cache could be admitted. It is not a general supported
capacity or recovery claim.
