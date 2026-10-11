# Eight-slot session admission and teardown — Q2_0 Orin — 2026-10-11

The batch owner smoke now accepts an explicit slot count (2–8). With `--batch-slots 8`, the Q2_0 engine admitted all eight supported slots under the ordinary six-GiB supervisor. Two concurrent requests still matched their serial output tokens and all nine state fingerprints by prompt; six admitted slots remained idle during the two-request exercise.

The primary session and all eight batch-slot sessions each requested 235,034,112 bytes. Every backing emitted a free at orderly shutdown. The owner ledger balanced 287 allocation/free events and ended with zero live requested bytes on host and device. Minimum host availability was 14,986,944,512 bytes (13.96 GiB), above the six-GiB floor. The request/state results, per-owner summary and raw telemetry are under `run/` and this directory.

This checks the full supported slot-count teardown, not behavior when memory admission reduces the requested slot count. That cleanup branch is implemented but remains unforced at runtime. The run does not establish eight-client throughput or per-request state isolation at concurrency eight.
