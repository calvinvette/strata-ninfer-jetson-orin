# Q2_0 graph owner check at 32K configured context — Orin — 2026-10-11

This extends the Q2_0 graph-owner startup check to a configured context of
32,768 tokens. It uses the same model artifacts, executable, 256-slot
expert-cache request, prefill and speculation settings, and six-GiB supervisor
as the 4K, 8K and 16K points. The model and pack remain under
`~/models/strata-orin-validation/`.

All seven API, streaming, cancellation and recovery scenarios passed.
Minimum host `MemAvailable` was 20.50 GiB. The session, expert-cache and
verifier device allocations balanced with frees; the 16 mapped verifier host
buffers and 256 pageable expert-stage buffers also balanced. The trace ended
with zero observed live requested bytes. Four successful graph instantiations
(three verifier windows and one commit graph) matched four graph owner events.

The session owner requested 991,516,160 bytes (945.1 MiB), compared with
559,240,704 bytes (533.1 MiB) at 16K. Session backing at 4K/8K/16K/32K was
235,034,112 / 343,102,976 / 559,240,704 / 991,516,160 bytes. The increases
per context doubling were 108,068,864 / 216,137,728 / 432,275,456 bytes
(103 / 206 / 412 MiB). These four observations show the increment doubling
with each context doubling for this runtime configuration; do not extrapolate
that relationship beyond these measurements.

NVMap client totals sampled every 100 ms were stable at 5,993,865,216 bytes
before the first graph call and 6,066,290,688 bytes after the fourth, a
72,425,472-byte (69 MiB) increase. It matches the 4K, 8K and 16K intervals.
This spans graph capture/instantiation and adjacent synchronous device
allocations, not an isolated graph-executable size. The 32K value is a
configured reservation only: the run did not ingest a 32K prompt or qualify
32K request capacity, quality, energy, pressure or performance.

Raw config, protocol, owner, NVMap and supervisor telemetry are retained here.
