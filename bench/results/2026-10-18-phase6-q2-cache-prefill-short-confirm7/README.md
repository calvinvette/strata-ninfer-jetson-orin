# Q2_0 short-task cache × prefill confirmation — Orin — 2026-10-18

This seven-block randomized confirmation tests whether the cache × prefill result changes on a short workload. It uses a newly generated exact 512-token retrieval-plus-arithmetic prompt, distinct from the near-limit prompt in the sibling [7,506-token confirmation](../2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/README.md). Each block crosses exact expert-cache capacities of 3,000 and 3,500 slots with prefill chunks of 32 and 128. Every cell starts a fresh service, runs a separate 512-token warmup, then one measured request under `MemoryMax=28G` and the six-GiB headroom guard.

The new held-out answer was checked against the independent suffix oracle `593 + 248 + 761 = 1602`. All 28 measured requests read exactly 512 prompt tokens and returned all three markers plus `SUM=1602`. All 28 supervisors passed and verified exact cache slots. The analyzer retained 3,002 memory samples; minimum host availability was 17.39 GiB and minimum effective admission availability was 9.33 GiB. Cgroup low/high/max/OOM/OOM-kill counters were zero. GPU clocks ranged from 306 MHz to 1,300.5 MHz; CPU clocks ranged from 729.6 MHz to 2,201.6 MHz; `tj` ranged from 47.88 to 57.75 °C. EMC readback was unsupported. Clocks remained dynamic and energy was not analyzed.

| Exact expert slots | Prefill chunk | Median request time | Median prompt rate | Median decode rate |
| ---: | ---: | ---: | ---: | ---: |
| 3,000 | 32 | 54.67 s | 10.3 tok/s | 9.0 tok/s |
| 3,000 | 128 | 29.23 s | 21.4 tok/s | 8.9 tok/s |
| 3,500 | 32 | 53.65 s | 10.6 tok/s | 9.1 tok/s |
| 3,500 | 128 | 28.72 s | 21.8 tok/s | 9.1 tok/s |

Within paired blocks, chunk 128 reduced median total request time 46.79% at 3,000 slots (95% paired-block bootstrap interval −47.86% to −45.90%) and 46.53% at 3,500 slots (−47.23% to −45.52%). Prompt-processing time fell 51.82% and 51.55%, respectively. The cache 3,500 versus 3,000 effect was −1.96% at chunk 32 (−4.48% to −0.12%) and −2.11% at chunk 128 (−2.22% to −1.19%). The cache-by-prefill interaction was +0.29 percentage points (−0.58 to +1.74), which includes no interaction. These are effects for this one prompt and profile; no default or profile is promoted.

The independent seven-block near-limit confirmation measured a larger chunk-128 benefit: median request-time changes were −59.54% at 3,000 slots and −59.74% at 3,500. A separate-block bootstrap comparing chunk effects across the two task campaigns estimated that the near-limit task's benefit was 12.75 percentage points larger at 3,000 slots (95% interval 7.67–13.80 points) and 13.21 points larger at 3,500 (12.36–14.57 points). For prompt time alone, the corresponding differences were 8.25 points (3.57–9.27) and 8.71 points (7.80–9.76). This shows a workload interaction between these two retrieval tasks: chunk 128 helped both, with a larger percentage effect on the near-limit task. Prompt content and completion length also differ, so this does not isolate prompt length as the only cause. The independent-block analysis and raw timings are retained in `workload-interaction-analysis.json`; it does not establish a general workload model or justify a default change.

The model is Q2_0 from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, pinned at revision `5348543e0147355ac9cbcb031184a3546350988e`. Shard hashes, config, workload, warmup, binary identity and source revisions are retained in this directory. Models and supporting pack files remain under `~/models/strata-orin-validation/`. Telemetry is losslessly gzip-compressed. `SHA256SUMS.txt` covers all retained files.

Reproduce on Orin with a fresh result directory:

```sh
out=/tmp/q2-cache-prefill-short-confirm7
mkdir -p "$out"
cp bench/results/2026-10-18-phase6-q2-cache-prefill-short-confirm7/{config.json,workload.json,warmup-workload.json} "$out/"
bench/results/2026-10-18-phase6-q2-cache-prefill-short-confirm7/run_confirm7.sh "$out"
python3 bench/results/2026-10-18-phase6-q2-cache-prefill-short-confirm7/analyze_confirm7.py --root "$out"
```

Run `analyze_workload_interaction.py` from the repository copy to compare the resulting seven-block short campaign with the retained near-limit confirmation. Phase 6 remains open for other workload, KV and interaction cells.
