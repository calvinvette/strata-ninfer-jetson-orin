# Q2_0 8K prefill cancellation and recovery at 22 GiB — Orin — 2026-10-13

This repeats the exact 8,192-token Q2_0 cancellation/recovery workload from the
[28-GiB run](../2026-10-13-phase3-q2-cancel-8k/README.md) under a
`MemoryMax=22G` systemd scope. The client disconnected after 1.015 seconds,
when 512 of 8,192 prompt tokens had been read. The service then returned
`Hello Orin!` (five tokens) in 15.17 seconds and remained healthy. Both checks
passed.

Minimum host availability was 18,800,857,088 bytes (17.510 GiB); minimum
effective cgroup headroom was 14,126,792,704 bytes (13.157 GiB). Both exceed
the six-GiB guard. The cgroup recorded zero OOM and OOM-kill events. The owner
trace recorded 304 allocation events and 303 frees; only the 1,485,606,400-byte
service-lifetime weight arena remained requested-live. Graph pools, driver
allocations and uninstrumented sites are outside this ledger.

The request used the same candidate binary, model, token-ID prompt, cache and
context settings as the paired 28-GiB run. CLI `--spec 2` yielded effective
`spec:4` and `mtp_max:2` because default suffix drafting expands the verifier
window. Runtime observations showed dynamic clocks; no clock or energy changes
were made. This is one repeat at a second cgroup limit, not a general capacity
threshold, product timing result, or long-context quality test.

Raw cancellation, engine, supervisor and telemetry records are retained here.
The local engine log is ignored by Git; its hash appears in `SHA256SUMS.txt`.
Model artifacts remain in `~/models/`.
