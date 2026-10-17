# Q2_0 long-prompt prefill chunk confirmation — current source — Orin — 2026-10-17

This seven-block randomized confirmation repeated the 7,501-token retrieval task on the current candidate binary after the earlier run's shared outer memory scope accumulated reclaimable file cache and caused two conservative admission aborts. Each measured arm now runs in its own 28-GiB `systemd-run --user --scope` with a fresh service, a separate 512-token warmup, and one measured prompt. The 14 measured requests used Q2_0, FP16 KV, MTP off, 8,192 context, exactly 3,000 expert-cache slots, eight workers, disabled prompt cache, no adaptive swaps, and prefill chunk 32 or 128. Only the prefill chunk changed within a pair. The exact two-shard model and all supporting files stayed under `~/models/strata-orin-validation`.

Every cell passed its supervisor and exact retrieval oracle: 7,501 prompt tokens, 36 completion tokens, with `EARLY=COPPER-FERN-482, MIDDLE=NORTH-EMBER-619, LATE=SILVER-OTTER-357`. No cgroup high/max/OOM/OOM-kill events occurred. Minimum host availability was 18.07 GiB and minimum effective admission availability was 11.39 GiB, both above the six-GiB host-headroom floor. Dynamic GPU frequency ranged from 306 MHz to 1,300.5 MHz; CPU frequency ranged from 729.6 MHz to 2,201.6 MHz. EMC readback was unsupported due to permission denial.

| Prefill chunk | Median request time | Median prompt rate |
| ---: | ---: | ---: |
| 32 | 668.1 s | 11.3 tok/s |
| 128 | 269.6 s | 28.4 tok/s |

Across the seven paired blocks, chunk 128 reduced request time by a median 59.71% (paired block bootstrap 95% interval −59.82% to −59.52%); all seven blocks favored chunk 128. Median prompt rate increased 151.33%. This confirms the direction on the tested long-prompt Q2_0 task and runtime profile; it does not establish a general default or justify changing one.

Request-window tegrastats integration produced complete estimates for all seven pairs. These are separate named rails, not process-attributed energy: they include prompt prefill and board idle/background activity, do not isolate generation, and must not be summed.

| Named rail | Chunk 32 median J / output token | Chunk 128 median J / output token | Paired median change (95% interval) |
| --- | ---: | ---: | ---: |
| `VIN_SYS_5V0` | 123.51 | 50.06 | −59.54% [−59.59%, −59.44%] |
| `VDD_GPU_SOC` | 147.90 | 61.98 | −58.09% [−58.20%, −58.02%] |
| `VDD_CPU_CV` | 13.74 | 10.33 | −25.13% [−25.82%, −24.40%] |

The first shared-outer-scope attempt is retained in `attempts/`; its first block passed, while the next two chunk32 cells safely aborted when the scope's accumulated file cache lowered effective admission below the guard despite healthy host availability. Those attempts are excluded from timing and energy effects. The per-cell scope retry completed all seven blocks. This demonstrates why the memory isolation belongs at the cell boundary for this campaign.

`analysis.json` contains per-block timings, paired effects, output checks, host/admission minima and clock ranges. `rail-energy.json` and `rail-energy-pairs.csv` contain the per-window estimates and paired rail analysis. `artifacts.json` pins source, binary, model and workload identities. `block-01/` through `block-07/` retain fresh-service outputs and telemetry; `SHA256SUMS.txt` covers the checked-in artifacts. Reproduce from the repository root with:

```sh
bench/results/2026-10-17-phase6-q2-prefill-long-workload-current-source/run_confirm7.sh /tmp/q2-prefill-long-current-source
python3 bench/results/2026-10-17-phase6-q2-prefill-long-workload-current-source/analyze.py --root /tmp/q2-prefill-long-current-source
```

Phase 6 remains open for its other interactions and workload domains. No serving profile or default changed.
