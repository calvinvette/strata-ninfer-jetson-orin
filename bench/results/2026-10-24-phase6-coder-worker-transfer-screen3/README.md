# Coder worker × transfer screen — Orin — 2026-10-24

This three-block randomized screen crossed four and eight CPU expert-pool
workers with mapped and `pread` transfer on Coder IQ1_M. All other settings
were held fixed: 8K context, 3,000 requested expert-cache slots, prefill chunk
128, FP16 KV and MTP off. Each fresh service ran one same-length warmup and one
measured request. The measured task used a 512-token retrieval-and-arithmetic
prompt and returned 45 tokens.

All 12 cells passed the API correctness and cache-capacity checks. Every answer
had the same output hash, and every cell admitted 3,903 actual expert-cache
slots. The worker and transfer effects below are paired within randomized
blocks; three blocks are screening evidence only.

| Workers / transfer | Requests | Median prompt | Median decode | Median request |
| --- | ---: | ---: | ---: | ---: |
| 4 / mapped | 3 | 15,171 ms | 4,481 ms | 19,652 ms |
| 8 / mapped | 3 | 14,991 ms | 3,416 ms | 18,394 ms |
| 4 / `pread` | 3 | 14,989 ms | 4,562 ms | 19,551 ms |
| 8 / `pread` | 3 | 14,602 ms | 3,539 ms | 18,140 ms |

With mapped reads, four workers took 6.43%, 6.84% and 13.97% longer than eight
workers across the three blocks. This is a consistent screening signal to
confirm on a held-out prompt. With `pread`, the four-versus-eight-worker
contrasts were −14.24%, +8.27% and +8.32%, so that worker effect is not stable
yet. The `pread`-versus-mapped differences and the worker × transfer
difference-in-differences also varied by block. No worker or transfer default
changes from this screen; the four-cell interaction will be confirmed with
seven held-out blocks before drawing a conclusion.

The supervised run used a 28-GiB cgroup cap and no clock controls. Across 758
memory/clock samples, minimum physical and admission availability were
13.88/9.12 GiB; cgroup low/high/max/OOM counters were all zero. CPU clocks ranged
729.6–2,201.6 MHz, GPU clocks 306–1,300.5 MHz, and `tj` 48.8–60.0 °C. EMC
readback was denied. No energy result was collected. Model files remain under
`~/models/strata-orin-validation/`.

The engine binary SHA256 is recorded in `design.json`; model revision is
`5348543e0147355ac9cbcb031184a3546350988e`. Prompt identity, fixed settings,
random seed, per-cell outputs and timings are in `design.json` and
`campaign/results.json`. Raw engine logs and telemetry remain local.

Reproduce from the repository root on Orin:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-24-phase6-coder-worker-transfer-screen3/supervisor \
  --timeout 7200 --interval 1 --sample-clocks -- \
  python3 tools/integration/pool_worker_screen.py \
  --config bench/results/2026-10-24-phase6-coder-worker-transfer-screen3/config.json \
  --workloads bench/results/2026-10-21-phase6-coder-current-source-cache-context-screen3/workloads.json \
  --output bench/results/2026-10-24-phase6-coder-worker-transfer-screen3/campaign \
  --workers 4 8 --transfer-modes mapped pread --io-threads 8 \
  --repetitions 3 --seed 2026102424 --baseline-workers 8 --timing-only
```

This adds Coder worker × transfer screening to the existing Q2_0 interaction
evidence. It does not qualify cold-disk behavior, sustained service, energy or a
general worker profile. Phase 6 remains open.
