# Q2_0 worker and file-tier correctness screen — Orin — 2026-10-11

This randomized 2×2 screen exercised CPU expert-pool workers 4/8 and mapped/
pread file-tier reads with Q2_0, a 3,000-slot actual expert cache, 8,192
configured context, speculation 2, a 512-token prompt, and 64 generated tokens.
The candidate binary SHA256 was
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.
The 12 cells ran in randomized order under the six-GiB availability supervisor
with read-only CPU/GPU/EMC sampling. The original order and per-cell raw request,
trace, service log, and supervisor telemetry are retained in `correctness/` and
`correctness-supervisor/`.

All 12 requests completed and returned the same output hash and 3,000 actual
cache slots. One cell (repetition 1, four workers, mapped reads) had intermediate
and final persistent-state hashes that differed from the other cells, despite
identical generated token IDs. Its accepted-prefix trace differed in `gdn`,
`tail`, `pooled`, `pooled_full`, and `kv` state hashes; the token IDs still
matched. The script therefore failed its cross-cell state gate. The supervisor
recorded a failed command exit, not a memory-floor or OOM failure; minimum host
`MemAvailable` was 19,048,636,416 bytes.

A focused three-process repeat held the setting at four workers with mapped
reads. All three outputs, full state-hash sequences, and accepted-prefix traces
matched exactly. Its six-GiB supervisor passed with minimum host availability
19,077,373,952 bytes. This did not reproduce the mismatch or identify its cause.
Both results are retained; the focused repeat does not erase the matrix failure.

The matrix was run with state tracing enabled, so its request times are not used
as performance evidence. A trace-free timing screen was not run because the
cross-cell correctness gate did not pass. No worker or transfer default is
changed. Before using these factors for optimization, repeat the complete
correctness matrix and resolve or bound the intermittent state divergence.

## Reproduction

The experiment uses `base-config.json` and `workloads.json` in this directory.
The first command below is the failed full matrix; the second is its focused
repeat. The downloaded weights and tokenizer remain under `/home/calvin/models/`.

```sh
python tools/integration/run_control.py --sample-clocks --privileged-emc \
  --output "$PWD/bench/results/2026-10-11-phase6-q2-worker-transfer-screen/correctness-supervisor" \
  --timeout 3600 -- /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  tools/integration/pool_worker_screen.py \
  --config "$PWD/bench/results/2026-10-11-phase6-q2-worker-transfer-screen/base-config.json" \
  --workloads "$PWD/bench/results/2026-10-11-phase6-q2-worker-transfer-screen/workloads.json" \
  --output "$PWD/bench/results/2026-10-11-phase6-q2-worker-transfer-screen/correctness" \
  --workers 4 8 --transfer-modes mapped pread --io-threads 8 --repetitions 3 \
  --seed 20261012 --baseline-workers 8
```

```sh
python tools/integration/run_control.py --sample-clocks --privileged-emc \
  --output "$PWD/bench/results/2026-10-11-phase6-q2-worker-transfer-screen/correctness-repeat-4mapped-supervisor" \
  --timeout 1800 -- /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  tools/integration/pool_worker_screen.py \
  --config "$PWD/bench/results/2026-10-11-phase6-q2-worker-transfer-screen/base-config.json" \
  --workloads "$PWD/bench/results/2026-10-11-phase6-q2-worker-transfer-screen/workloads.json" \
  --output "$PWD/bench/results/2026-10-11-phase6-q2-worker-transfer-screen/correctness-repeat-4mapped" \
  --workers 4 --transfer-modes mapped --io-threads 8 --repetitions 3 \
  --seed 20261013 --baseline-workers 4
```
