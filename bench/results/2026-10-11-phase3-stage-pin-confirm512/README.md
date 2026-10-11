# Pageable versus pinned expert staging confirmation — Orin — 2026-10-11

The current IQ1_M candidate completed three randomized pageable/pinned pairs
with a 512-token prompt and eight generated tokens. The engine binary SHA256
was `3ed52e6e0f845415b8fb2f2c15577f4b90efe49be72e2866d0dc961dbb0c95b0`.
The run held the requested expert cache at 3,000 slots, disabled CPU prefill
sharing, enabled owner and state tracing, and ran under the ordinary six-GiB
host-availability supervisor.

All three pairs produced identical token IDs and all nine persistent-state
fields. Pageable and pinned expert-stage host owners were each observed in all
their respective arms. Median requested staging backing was 181,043,200 bytes
for pageable and 170,393,600 bytes for pinned. Minimum sampled host
`MemAvailable` was 14,187,667,456 bytes (13.21 GiB); no headroom breach
occurred.

Median prompt time was 13,578.3 ms pageable and 13,405.8 ms pinned. Median
decode time was 2,374.8 ms pageable and 2,414.4 ms pinned, but one pageable
decode arm took 14,366.6 ms. Tracing, small sample size, and this outlier make
timing descriptive only. Energy and actual GPU/EMC clocks were not qualified.
The result confirms state parity and owner lifetime for this workload; it does
not establish a copy-latency or end-to-end benefit and promotes no mode.

Raw arms and logs are retained in `experiment/`; physical-memory telemetry is
in `supervisor/`. No model or build products are included.
