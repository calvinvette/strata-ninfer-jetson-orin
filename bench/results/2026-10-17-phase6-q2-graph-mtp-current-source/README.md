# Q2_0 graph capture × MTP2 confirmation — current source — Orin — 2026-10-17

This seven-block randomized confirmation repeated the captured/eager CUDA graph × MTP-off/window2 comparison on the current candidate binary, using the task-quality-validated processor explanation prompt. Each of the 28 cells used a fresh service and a separate 512-token warmup. The measured prompt had 2,094 tokens; every response naturally stopped at 293 tokens, passed the task rubric, and was byte-identical across all 28 cells. MTP2 offered and accepted 153/97 drafts in every MTP2 request. Q2_0, FP16 KV, 3,000 exact expert slots, 8K context, prefill 512, accepted-only swap cadence 4 and eight workers stayed fixed.

| Condition | Median client time | Median TTFT | Median prompt rate | Median decode rate |
| --- | ---: | ---: | ---: | ---: |
| Captured, MTP off | 60.98 s | 25.43 s | 83.0 tok/s | 8.2 tok/s |
| Eager, MTP off | 62.02 s | 25.84 s | 81.7 tok/s | 8.1 tok/s |
| Captured, MTP2 | 64.25 s | 26.44 s | 79.8 tok/s | 7.7 tok/s |
| Eager, MTP2 | 64.13 s | 26.21 s | 80.6 tok/s | 7.7 tok/s |

Paired request-time effects use candidate/control ratios within each block and bootstrap the seven independent block effects:

| Contrast | Median change | Paired 95% interval |
| --- | ---: | ---: |
| Captured vs eager, MTP off | −1.57% | −3.07% to +0.63% |
| Captured vs eager, MTP2 | +0.10% | −1.15% to +2.43% |
| MTP2 vs off, captured | +5.46% | +4.46% to +7.07% |
| MTP2 vs off, eager | +3.39% | +2.17% to +5.54% |
| Capture × MTP request-time interaction | +2.82 points | −1.19 to +38.41 points |

Capture/eager latency effects and the interaction interval include zero. On this workload, MTP2 raised request time in both graph modes and reduced median decode throughput 6.10% in captured mode (95% interval −7.32% to −4.94%) and 3.75% in eager mode (−6.10% to −2.50%). The seven-block MTP × graph result does not establish a graph/MTP serving win, and no default changed.

The `block-05-captured-mtp2` cell had a 56.94-second TTFT and 95.80-second request, versus the 64.25-second condition median. It still produced the exact answer, passed its quality rubric and memory guard, and remains included. Its measured prompt rate was 36.9 tok/s versus 79.8 tok/s median; the run sampled dynamic GPU frequencies from 306 MHz to 1,300.5 MHz, but the observations do not establish the cause. Another eager/MTP-off cell had a 5.2 tok/s decode rate and 82.11-second request and is also retained. Minimum host availability was 16.95 GiB and effective admission availability was 11.58 GiB. Cgroup high/max/OOM/OOM-kill counters were zero; GPU clocks ranged 306 MHz–1,300.5 MHz, CPU 729.6 MHz–2,201.6 MHz, and `tj` 48.28–61.25 °C.

Request-window integration estimated all 28 windows on the named tegrastats rails. For `VIN_SYS_5V0`, medians were 1.520, 1.536, 1.546 and 1.542 J/output token in the table order. MTP2 changed this rail by +1.68% in captured mode (paired 95% interval +1.11% to +3.36%) and +0.31% in eager mode (−0.13% to +2.07%). Capture/eager energy changes included zero. These estimates include board idle/background activity; they are not process-attributed, do not isolate generation, and rails are never summed.

This campaign used the Q2_0 quantization from the pinned `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` repository snapshot. It is distinct from the `IQ1_M` Coder artifact used in the `2026-10-15-phase7-current-source-coder-iq1m` report. Both are quantizations from the same source repository; this is not a cross-quantization or cross-engine comparison.

`analysis.json` contains per-cell data and paired intervals; `paired-effects.svg` plots the measured timing effects. `rail-energy.json` and `rail-energy-pairs.csv` contain the separate request-window rail estimates. `artifact-identities.json` pins the model source/revision, binary and inputs. `run-confirmation/` retains the randomized commands, API responses and memory/clock/tegrastats logs; `SHA256SUMS.txt` covers the checked-in artifacts. Reproduce from the repository root:

```sh
python3 bench/results/2026-10-17-phase6-q2-graph-mtp-current-source/confirm7.py \
  --output bench/results/2026-10-17-phase6-q2-graph-mtp-current-source/run-confirmation \
  --blocks 7 --seed 202610173 --run
python3 bench/results/2026-10-17-phase6-q2-graph-mtp-current-source/analyze_confirm7.py
python3 bench/results/2026-10-17-phase6-q2-graph-mtp-current-source/plot_effects.py
python3 bench/results/2026-10-17-phase6-q2-graph-mtp-current-source/analyze_rail_energy.py
```

Phase 6 remains open for broader workloads and configuration domains. No serving default changed.
