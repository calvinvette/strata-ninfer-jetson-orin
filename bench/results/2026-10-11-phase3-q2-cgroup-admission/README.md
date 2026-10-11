# Q2_0 model under active cgroup caps — Orin — 2026-10-11

The same 512-token Q2_0 Coder model request was run in independent transient
cgroup-v2 scopes capped at 12, 20 and 24 GiB. Each run used 3,000 cache slots,
4,096 context, one greedy generated token, no MTP, the Q2_0 PLE mmap path and
the existing three-GiB workspace reserve. `run_control.py` remained inside the
scope and enforced the six-GiB minimum effective-availability floor. Every
request completed and emitted token ID 32.

| Cgroup memory cap | Peak scoped `memory.current` | Minimum effective availability | Minimum host `MemAvailable` | Result |
| ---: | ---: | ---: | ---: | --- |
| 12 GiB | 5.01 GiB | 6.99 GiB | 21.57 GiB | Pass |
| 20 GiB | 7.08 GiB | 12.92 GiB | 18.81 GiB | Pass |
| 24 GiB | 10.27 GiB | 13.73 GiB | 18.48 GiB | Pass |

The 12-GiB scope was the tightest observed cell and stayed about 0.99 GiB above
the supervisor floor. Scoped `memory.current` includes that unit's charged
process and file-cache pages; its peak varied across runs, so these rows are not
a minimum-capacity threshold or an allocation-demand comparison. Host
`MemAvailable` remained the physical-memory authority and was never added to
cgroup or device counters. The raw per-sample scope/host observations,
`tegrastats`, commands and outputs are in the three linked run directories;
[`analysis.json`](analysis.json) summarizes the measured minima and peak scope
current.

This extends the earlier IQ1_M cgroup screen to the actual Q2_0 model, but only
for this cache, context and one-token workload. It establishes successful
admission under these three caps, not a general support claim or recovery under
an engine allocation failure.
