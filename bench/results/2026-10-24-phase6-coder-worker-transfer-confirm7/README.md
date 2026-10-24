# Coder worker × transfer confirmation — Orin — 2026-10-24

This held-out confirmation crossed four and eight CPU expert-pool workers with
mapped and `pread` transfer on Coder IQ1_M. Seven randomized blocks ran each
cell in a fresh service, after one same-length warmup. The task used the
held-out 512-token Coder retrieval/arithmetic prompt and generated 48 tokens.
Settings otherwise matched the screen: 8K context, 3,000 requested expert
cache slots, prefill chunk 128, FP16 KV and MTP off.

All 28 cells passed. API answer hashes were identical, the task oracle passed,
and every cell admitted 3,903 actual cache slots. Median latencies were:

| Workers / transfer | n | Median prompt | Median decode | Median TTFT | Median request |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4 / mapped | 7 | 15,029 ms | 4,726 ms | 15,116 ms | 19,770 ms |
| 8 / mapped | 7 | 14,882 ms | 3,588 ms | 14,955 ms | 18,470 ms |
| 4 / `pread` | 7 | 14,565 ms | 4,697 ms | 14,653 ms | 19,281 ms |
| 8 / `pread` | 7 | 14,447 ms | 3,704 ms | 14,519 ms | 18,154 ms |

Paired request-time deltas use the 8-worker result as baseline for the worker
effect and mapped as baseline for transfer. Across blocks, four workers were
slower than eight by a median 7.36% (mapped, paired bootstrap 95% interval
4.40–7.74%) and 6.50% (`pread`, 5.39–6.69%). `pread` reduced request time at
both worker counts: median −2.72% at four workers (95% interval −3.32 to
−1.74%) and −1.94% at eight workers (−3.34 to −0.84%). The worker × transfer
interaction was −0.78 percentage points (−1.44 to +1.79), so the data do not
show a reliable interaction. These paired intervals summarize the block
medians; successive tokens are not treated as replicates.

One 8-worker/mapped observation had a 22.5-second decode versus 3.5–3.7
seconds in its other six blocks; its prompt phase was ordinary and the output
still passed. During its approximate decode window, supervisor observations
showed the GPU at 1,300.5 MHz and `GR3D_FREQ` at 99%, with `tj` 54.8–60.3 °C;
the other six 8-worker/mapped decode windows also showed about 99% GPU use and
overlapping temperatures. This does not identify the cause or rule out outside
contention. The cell remains in the reported data. The paired-median summaries
are robust to that observation, but the result should be treated as a bounded
workload signal rather than a general profile recommendation. No default
changed. The result strengthens the four-versus-eight-worker signal seen on
the screening prompt and finds a small `pread` request-time benefit in this
held-out task; it does not qualify cold-disk behavior or sustained service.

The 1,742-second supervised run used a 28-GiB cgroup cap and no clock controls.
Minimum physical and admission availability were 13.99/9.60 GiB; cgroup
memory event counters stayed at zero. GPU/CPU clocks were observed dynamically;
EMC clock readback was denied. A retrospective one-second tegrastats integration
estimated each request's named rails. Median joules/output-token for
`VDD_CPU_CV` / `VDD_GPU_SOC` / `VIN_SYS_5V0` were 1.46 / 4.77 / 3.10 at four
workers with mapped reads; 1.58 / 4.74 / 3.06 at four workers with `pread`;
1.65 / 4.50 / 2.95 at eight workers with mapped reads; and 1.75 / 4.54 / 2.92
at eight workers with `pread`. The four-worker versus eight-worker CPU-rail
effect was −10.66% mapped and −9.33% `pread`; GPU/SOC and system-rail effects
went the other way. `pread` reduced system-rail joules/token by median 1.28%
at four workers (95% interval −1.86% to −1.17%) and 1.02% at eight workers
(−1.56% to +0.07%). The interaction intervals included zero. These rails
include background/idle energy, are not process-attributed and are not summed;
one-second sampling also limits request-window precision. The results are
rail-specific observations, not whole-board energy or a Pareto winner. Model
files remain in `~/models/strata-orin-validation/`.

Binary SHA256, source commit, model revision, workload identity, seed, all cell
timings and paired bootstrap intervals are recorded in `design.json`,
`config.json` and `campaign/results.json`. `analyze_named_rails.py` performs the
retrospective integration; `named-rail-energy.json` contains its per-request
estimates and paired summaries. Raw service logs and supervisor telemetry
remain local.

Reproduce on Orin from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-24-phase6-coder-worker-transfer-confirm7/supervisor \
  --timeout 7200 --interval 1 --sample-clocks -- \
  python3 tools/integration/pool_worker_screen.py \
  --config bench/results/2026-10-24-phase6-coder-worker-transfer-confirm7/config.json \
  --workloads bench/results/2026-10-21-phase6-coder-current-source-cache-context-confirm7/workloads.json \
  --output bench/results/2026-10-24-phase6-coder-worker-transfer-confirm7/campaign \
  --workers 4 8 --transfer-modes mapped pread --io-threads 8 \
  --repetitions 7 --seed 2026102431 --baseline-workers 8 --timing-only
```

This confirms one Coder worker × transfer workload interaction. Phase 6 remains
open for the broader Pareto, energy and remaining supported interaction scope.
