# Scoped-I/O launch attempt — Orin — 2026-10-10

This first attempt used `systemd-run --scope --uid=calvin` to obtain
`IOAccounting=yes` while launching the real-model transfer harness. The system
manager did not preserve the user's supplemental device groups. The engine
exited during startup with `NvRmMemInitNvmap failed with Permission denied`,
before serving a request. The run is a launcher setup failure, not an inference
failure, and is excluded from all transfer comparisons. Minimum host
`MemAvailable` was 29,660,151,808 bytes. Raw supervisor output is retained in
`supervisor/`.

The successful launcher runs a temporary system scope and uses `setpriv` inside
it to preserve the ordinary UID and device groups; see the
[seven-pair report](../2026-10-10-phase3-transfer-cgroupio-confirmation7/README.md).
