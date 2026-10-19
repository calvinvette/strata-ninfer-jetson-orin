# Current-source Q2_0 worker × transfer confirmation — Orin — 2026-10-19

This randomized seven-block confirmation repeated the 4/8 CPU-worker × mapped/
`pread` expert-transfer interaction on the current candidate binary. Each of
28 cells used a fresh service, one exact 512-token warmup and one measured
512-token retrieval-plus-arithmetic request. The run used Q2_0, 8K context,
3,000 exact expert slots, prefill chunk 512, eight `pread` I/O threads, FP16
KV and no MTP model. The four cells in every block were randomized.

All 28 measured answers returned the same three planted codes in order and the
independently specified suffix sum `1428`; each returned exactly 46 completion
tokens. All cells held 3,000 expert slots and the output hashes matched. The
campaign runner passed every cell and its cache/output checks. Instrumentation
was disabled during measurement to avoid trace overhead; this is response and
cache correctness evidence, not accepted-prefix state evidence.

| Workers / transfer | Requests | Median prompt | Median decode | Median request |
| --- | ---: | ---: | ---: | ---: |
| 4 / mapped | 7 | 17,921 ms | 9,641 ms | 28,400 ms |
| 8 / mapped | 7 | 18,079 ms | 8,745 ms | 27,543 ms |
| 4 / `pread` | 7 | 15,191 ms | 10,639 ms | 25,792 ms |
| 8 / `pread` | 7 | 15,015 ms | 10,648 ms | 26,050 ms |

Within-block paired request-time effects had wide intervals that included no
change. Four versus eight workers changed request time by +2.48% under mapped
reads (paired bootstrap 95% interval −23.29% to +6.84%) and +4.74% under
`pread` (−22.61% to +10.48%). `pread` versus mapped changed request time by
−8.63% at four workers (−10.53% to +141.74%) and −6.55% at eight workers
(−11.91% to +13.55%). The worker × transfer difference-in-differences was
1.03 percentage points (−24.08 to +18.45). Several decode-time outliers
inflate uncertainty, including slow mapped cells in blocks 1/4 and slow
`pread` cells in blocks 5/6. These seven pairs do not establish a reliable
worker, transfer or interaction effect, so no setting changed. Full paired
values and intervals are in `campaign/results.json` and
`paired-effects.csv`.

The current candidate binary SHA256 is
`b09ed0b5774de235d145bff869950730a78cbf5ddc6b4057098d70b981130eaa`, built
from engine source commit `b6ea61888cb1ffb0bf92e79217d6a88d46178111`. The
model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, Q2_0, revision
`5348543e0147355ac9cbcb031184a3546350988e`; shard, PLE-pack and expert-profile
hashes are in `artifacts.json`. Models and packs remained under
`~/models/strata-orin-validation/`.

The supervised 28-GiB run took 2,344 seconds. Across 2,237 samples, minimum
host/admission availability was 17.47/6.25 GiB, above the six-GiB guard. Cgroup
low/high/max/OOM/OOM-kill counters were zero. CPU/GPU clocks were observed
dynamically (CPU 729.6–2,201.6 MHz; GPU 306–1,300.5 MHz); EMC readback was
denied. Junction temperature ranged from 49.2 to 58.8 °C. The raw schedule,
per-cell API outputs, engine logs, memory samples, tegrastats and supervisor
result are retained in `campaign/` and `supervisor/`. The independent response
and memory review is `verification.json`.

Reproduce on Orin from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-19-phase6-q2-worker-transfer-current-source-confirm7/supervisor \
  --timeout 7200 --interval 1 --sample-clocks -- \
  python3 tools/integration/pool_worker_screen.py \
  --config bench/results/2026-10-19-phase6-q2-worker-transfer-current-source-confirm7/config-mtp-off.json \
  --workloads bench/results/2026-10-19-phase6-q2-worker-transfer-current-source-confirm7/workloads.json \
  --output bench/results/2026-10-19-phase6-q2-worker-transfer-current-source-confirm7/campaign \
  --workers 4 8 --transfer-modes mapped pread --io-threads 8 \
  --repetitions 7 --seed 2026101919 --baseline-workers 8 --timing-only

python3 bench/results/2026-10-19-phase6-q2-worker-transfer-current-source-confirm7/verify.py
```

This confirms the worker × transfer cells only for this Q2_0 workload and
current binary. The interaction is inconclusive, and it does not qualify cold
disk behavior, other prompts or serving profiles. Phase 6 remains open for
other supported interactions and process-attributed energy/Pareto work.

The retained one-second tegrastats samples were also integrated over each
request window in `rail-energy.json` (reproduce with
`python3 bench/results/2026-10-19-phase6-q2-worker-transfer-current-source-confirm7/analyze_rails.py`).
All 28 windows were bracketed and estimated. These are separate named board
rails, include idle/background activity, are not process-attributed, and must
not be summed. Median `VIN_SYS_5V0` estimates were 3.823, 3.730, 3.584 and
3.550 J/output token for 4/mapped, 8/mapped, 4/`pread` and 8/`pread`,
respectively. The paired 4-vs-8 worker effects were +1.10% (mapped; 95%
interval −19.49% to +4.91%) and +3.25% (`pread`; −15.50% to +8.94%). The
`pread`-vs-mapped effects were −4.61% at 4 workers (−8.10% to +100.04%) and
−6.83% at 8 workers (−8.43% to +7.72%). These broad intervals and background
load make the rail estimates descriptive only; they do not establish an energy
winner or close process-energy attribution.
