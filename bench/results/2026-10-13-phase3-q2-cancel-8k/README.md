# Q2_0 8K prefill cancellation and recovery — Orin — 2026-10-13

A supervised Qwen3.8 Flash-Next Q2_0 service received an exact 8,192-token
prompt with a 16,384-token configured context, 3,000 expert slots and a 28-GiB
systemd cgroup ceiling. The streaming client closed after 1.014 seconds. The
engine had read 512 of 8,192 prompt tokens when it recorded cancellation and
returned zero generated tokens. The same service then answered `Hello Orin!`
with five tokens; health stayed `ok` and the server remained alive.

The supervisor measured minimum host and effective-scope availability of
18,816,561,152 bytes (17.524 GiB), above the six-GiB floor. Cgroup OOM,
`oom_kill` and `oom_group_kill` counters remained zero. The observed requested
allocation ledger had 304 allocations and 303 frees; transient expert-cache,
staging, prefill, session and verifier owners had zero requested-live bytes at
log end. Only the 1,485,606,400-byte service-lifetime weight arena remained.
This owner trace excludes graph pools, driver-private allocations and other
unobserved backing, so it is not total physical-memory accounting.

The launch passed `--spec 2`; the engine's default suffix drafter expands that
to an effective four-token verifier window (`spec: 4`, `mtp_max: 2`,
`lookup: 3` in `/metrics`). The recorded engine log and metrics preserve this
distinction. CPU frequencies were observed dynamically from 729.6 to 2,201.6
MHz; tegrastats reported EMC at 3,199 MHz throughout and did not provide a GPU
frequency sample in its parsed format. The supervisor's initial sysfs sample
reported GPU 306 MHz. No clocks were changed and no energy-per-request claim is
made. The recovery took 17.08 seconds; timings are descriptive only.

The prompt's token-ID JSON SHA256 is
`58496e66b221de517df6c82bf6acec094894d19858aaab46b8d4fa09cf203efe`. The
candidate binary SHA256 is
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.
The workload JSON SHA256 is
`dcbea0a7e2f85f70566cb5b712cfe48522e3b384443770b32514dfeb0c6e4735`; the raw
engine log SHA256 is recorded in `SHA256SUMS.txt` (the local engine log remains
ignored by Git).

This extends cancellation/recovery evidence to an 8K prefill on the same
Q2_0 service configuration. It does not prove general cancellation cleanup,
in-place engine recovery, a capacity threshold, long-context quality, or a
performance benefit. Energy was not measured; raw tegrastats and supervisor
telemetry are retained. Reproduction uses the local model paths in
`server-config.json` and `workloads.json`, then `run_control.py` with
`cancel_long_prefill_recovery.py`; these model files remain outside Git.
