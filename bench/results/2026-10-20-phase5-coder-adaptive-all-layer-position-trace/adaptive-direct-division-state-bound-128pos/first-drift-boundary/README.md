# Raw layer-32 state before the first differing token — Orin — 2026-10-22

This adaptive-only supervised replay used the exact direct-division 128-token
sequence from the parent campaign: same binary, pinned IQ1_M shards, prompts,
MTP and adaptive settings. It captured layer-32 committed GDN state at
positions 515, 534, 557, 558, 574 and 638. The 128-token paired campaign's
initial/recovery output IDs first diverged at index 47 (`449` versus `264`).
The shared IDs immediately before it were index 45=`11` and index 46=`466`,
which align with captured state input IDs at positions 557 and 558.

At position 557, recurrent/convolution relative L2 was 0.01355/0.00964; at
position 558 it was 0.01319/0.00986. Both captures therefore show non-bitwise
persistent state before the first differing output token, while the token IDs
consumed through index 46 still agree. The first token mismatch is consistent
with a small accumulated state difference crossing the next-token decision
boundary. This capture does not identify the earlier layer or operator that
introduced the state difference. Positions 574 and 638 occur after the token
histories differ, so their large deltas are not attribution evidence.

All 12 raw state records matched the service accepted-prefix hashes. The
supervisor passed with minimum host/admission availability 14.25 GiB and zero
cgroup memory events. Dynamic clocks were observed without control; energy was
not measured. Raw arrays and logs remain local. `gdn-commit-state-summary.json`
contains the checked measurements.
