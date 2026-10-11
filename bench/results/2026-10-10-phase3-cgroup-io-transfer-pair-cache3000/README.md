# Scoped-I/O capacity-controlled pilot — Orin — 2026-10-10

After the invalid 5,000-requested-capacity attempt, a randomized mapped/pread
pair used requested capacity 3,000. Both arms selected 3,903 actual slots,
emitted identical 64 token IDs and matched all nine persistent-state fields.
The systemd-scope `io.stat` deltas were 9.477 GB mapped and 11.349 GB pread.
The request times were 30,612.4 ms and 33,434.8 ms. Minimum host
`MemAvailable` was 13,971,959,808 bytes (13.01 GiB).

This is one pair and remains pilot evidence; it is superseded by the seven-pair
[scoped-I/O confirmation](../2026-10-10-phase3-transfer-cgroupio-confirmation7/README.md).
Raw arm logs, experiment JSON and supervisor telemetry are preserved here.
