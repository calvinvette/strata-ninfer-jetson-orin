# Q2_0 PLE direct-read versus mmap screen — Orin — 2026-10-10

This Phase 3 screen compares the Q2_0 PLE table's `--ple-io direct` and
`--ple-io mmap` modes on the exact 512-token prompt, with one generated token.
The native expert cache was held at 5,000 actual slots, the configured context
at 4,096, and MTP disabled. All six supervised runs passed, stayed above the
six-GiB host availability floor (minimum 15.96 GiB), and emitted token ID 32.
The 64-row independent reader parity and block oracle are separate evidence in
the [artifact-aware PLE report](../2026-10-10-phase3-q2-ple-artifact-aware/README.md).

| Pair | Order | Direct prompt ms | mmap prompt ms | mmap minus direct | Engine PLE counter direct/mmap ms |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | mmap, direct | 15,303.5 | 14,709.1 | -594.4 ms (-3.88%) | 0.3 / 0.2 |
| 2 | direct, mmap | 14,967.9 | 14,225.2 | -742.7 ms (-4.96%) | 0.2 / 0.3 |
| 3 | mmap, direct | 14,486.0 | 14,195.3 | -290.7 ms (-2.01%) | 0.3 / 0.3 |

The median CLI prompt times were 14,967.9 ms direct and 14,225.2 ms mmap.
Paired deltas ranged from -2.01% to -4.96%, with a median -3.88%. This is a
three-pair screening summary, not a confirmed benefit. The order was balanced
and predeclared but not randomized algorithmically. The page-cache state was
not reset, CPU clocks varied, GPU/EMC frequencies were unavailable, and no
energy attribution was made. The CLI prompt timing includes the whole prompt
path and cannot attribute the difference to PLE reads; the engine's own PLE
counter remained 0.2–0.3 ms in both modes. One token and no persistent-state
hashes do not establish model-quality or state parity. Neither mode is
promoted.

The engine SHA is `d3e8bcde3a430d7d5bb614fec8ba938398699b9abecd41965bb28fd6d465d721`;
prompt-token file SHA is
`c463143cd6cc684c29cba41efe832274e4cc040335b2338cce196d67c47d3cbf`. Each
run's `result.json` retains its exact command, raw stdout/stderr, tegrastats and
memory samples. The paired numeric summary is `results.json`, and the actual
balanced order is `order.json`.
