# Q2_0 under an 8 GiB cgroup cap with a smaller cache request

This follow-up repeats the failed 8 GiB Q2_0 cgroup cell with a requested
256-slot expert cache rather than 3,000 slots. It uses the same current
candidate binary (`3e1e003c` SHA256 prefix), Q2_0 artifacts, 512-token prompt,
one greedy output, 4K context, PLE mmap, no MTP, 3 GiB workspace reserve and
six-GiB effective-availability supervisor. The complete command and raw
telemetry are in `supervisor/`; artifact identity is in
`artifact-identities.json`. The model and generated pack remain under
`~/models/`.

The request again failed after prefill: cache admission remained at zero slots,
so native speculative decode rejected the missing device residency table.
The process exited with code 2 after 12.58 seconds; this was not an OOM or a
supervisor abort. Minimum effective availability was 6.78 GiB, minimum host
`MemAvailable` was 22.11 GiB, and peak scope `memory.current` was 1.22 GiB.
The 8 GiB result therefore does not become viable simply by requesting a
smaller cache. This single repeat does not identify a general minimum cap or
rule out other engine configurations.

The matched [10 GiB/256-slot follow-up](../2026-10-11-phase3-q2-cgroup10G-cache256/README.md) passed and admitted all 256 slots. Thus this configuration succeeds at 10 GiB and fails at 8 GiB; the 10 GiB/3,000-slot cell separately contracted to 296 slots. These are observed points, not a general capacity threshold. No serving behavior or default changed.
