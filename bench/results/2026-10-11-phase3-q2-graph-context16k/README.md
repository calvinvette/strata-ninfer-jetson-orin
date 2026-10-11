# Q2_0 graph owner check at 16K context — Orin — 2026-10-11

This repeats the Q2_0 graph-owner service check at a configured context of
16,384 tokens. It uses the same artifacts, executable, 256-slot expert-cache
request, prefill and speculation settings, and six-GiB supervisor as the 4K
and 8K checks. The model and pack remain under `~/models/strata-orin-validation/`.

All seven API, streaming, cancellation and recovery scenarios passed.
Minimum host `MemAvailable` was 21.04 GiB. Session, expert-cache and verifier
device owners balanced allocation/free pairs; the 16 mapped verifier buffers
and 256 pageable expert-stage buffers also balanced. The owner trace ended with
zero observed live requested bytes. Four successful graph calls (three
verifier windows and one commit graph) matched the four graph owner events.

The session owner requested 559,240,704 bytes (533.1 MiB), compared with
343,102,976 bytes (327.1 MiB) at 8K and 235,034,112 bytes (224.1 MiB) at 4K.
Each context doubling added 108,068,864 bytes (103.0 MiB) to this session
backing in the measured configurations. The 100 ms NVMap samples were stable
at 5,561,524,224 bytes before graph instantiation and 5,633,949,696 bytes after
the fourth call, a 72,425,472-byte (69 MiB) increase. This matches the 4K and
8K graph intervals. As in those runs, the NVMap interval includes synchronous
device allocations alongside graph capture and is not an isolated graph
executable size.

This is a startup/protocol memory result, not long-context ingestion, quality,
energy, cgroup-pressure or performance qualification. Raw config, protocol,
owner, NVMap and supervisor telemetry are retained in this directory.
