# Q2_0 locked PLE RAM-mode probe — Orin — 2026-10-12

`--ple-io ram` is intended to fault in and lock the PLE table. The earlier three-pair screen fell back because the inherited process memlock ceiling was about 3.75 GiB. This probe used transient systemd **service** limits (no system-wide change) to test 8-GiB and 12-GiB `RLIMIT_MEMLOCK` values. It retained the normal six-GiB physical headroom guard. The exact launch properties and all raw telemetry are recorded here.

The first 8-GiB attempt used a 22-GiB cgroup cap and was supervisor-aborted during startup when effective cgroup headroom reached 6,280,151,040 bytes (5.85 GiB). Host `MemAvailable` remained at least 22.95 GiB and the scope reported no OOM kills. The process did not complete the request.

Two uncapped processes then completed the Q2_0 512-token request at 3,000 cache slots and emitted token ID 32. Minimum physical availability was 18.67 GiB with the 8-GiB lock limit and 18.60 GiB with the 12-GiB limit; no OOM kills occurred. In both cases the engine logged `PLE table mlock failed (Cannot allocate memory; raise ulimit -l)` and explicitly reported `loaded (not locked)`. It faulted the table pages in, but they remained reclaimable. A test service confirmed the configured hard/soft memlock limits reached an unprivileged child process.

These runs show that the current Q2_0 PLE table does not enter locked-RAM mode under a 12-GiB process limit. The reason may be the table's locked-byte requirement or another kernel admission limit; the result does not distinguish them. The uncapped completions qualify fallback behavior only. No RAM-mode timing comparison is valid, no default changed, and larger lock limits were not attempted because their physical headroom cost is unknown.

[`analysis.json`](analysis.json) summarizes the three attempts. `supervisor/`, `supervisor-uncapped/` and `supervisor-memlock12g/` retain samples and engine output. This closes no Phase 3 gate; locked RAM is unsupported for this configuration under the tested limits.
