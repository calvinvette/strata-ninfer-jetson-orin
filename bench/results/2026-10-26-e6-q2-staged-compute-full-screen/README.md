# Full 8K staged Strata versus NInfer compute screen

Date: 2026-10-26. Hardware: Jetson AGX Orin 32 GB, CUDA 12.6, SM87. Model:
Qwen3.8-Flash-Next GSQ RCO Q2_0, using the same two GGUF shards, PLE pack and
expert profile as the [E6 retrieval run](../2026-10-26-e6-q2-staged-retrieval-2k/README.md).
Shard hashes, binary identity and compact per-process measurements are in
[`summary.json`](summary.json).

## Method

Three randomized process pairs compared Strata grouped compute with strict
NInfer grouped compute. Both arms enabled the same staged path
(`--pcie-frac 1.0`) and used identical model/profile flags, 3,000 expert slots,
6-GiB resident budget, 3-GiB workspace reserve, 8K context, MTP-2, prefill 128
and eight workers. Each process warmed up then measured five natural-generation
workloads: 512+64, 2,048+128, 172+64, 557+64 and 1,069+64. Pair orders were
Strata/NInfer, NInfer/Strata, Strata/NInfer. No trace or state hash was enabled.

All 30 measured responses passed API and token-count checks. Outputs matched
between compute backends for all 15 paired requests. The same 3,000-slot
resident-map hash matched in every arm. Positive TPS changes mean faster
NInfer; positive latency changes mean slower NInfer.

| Prompt + output | Prompt TPS Strata → NInfer; paired median change (range) | Decode TPS Strata → NInfer; paired median change (range) | First-visible TTFT change (range) | Client total change (range) | Hashes |
| --- | --- | --- | --- | --- | :---: |
| 512+64 | 33.9 → 33.9; **−1.13%** (−1.19 to 0.00) | 10.3 → 10.3; **0.00%** (0.00 to 1.96) | +0.87% (−0.11 to 1.01) | +0.52% (−0.20 to 0.71) | 3/3 |
| 2,048+128 | 57.6 → 58.2; **−0.51%** (−5.65 to 1.04) | 9.5 → 9.6; **0.00%** (0.00 to 1.05) | +0.62% (−1.19 to 5.82) | +0.38% (−1.16 to 4.16) | 3/3 |
| 172+64 | 17.0 → 16.3; **−4.12%** (−7.50 to −3.11) | 10.1 → 10.1; **0.00%** (−2.97 to 0.97) | +4.30% (2.89 to 7.97) | +3.59% (1.65 to 4.34) | 3/3 |
| 557+64 | 42.0 → 42.5; **+1.19%** (−3.97 to 2.91) | 11.5 → 11.7; **+0.86%** (−2.61 to 5.36) | −0.53% (−2.91 to 4.03) | +0.05% (−3.51 to 2.80) | 3/3 |
| 1,069+64 | 48.8 → 49.3; **+0.41%** (−2.14 to 1.02) | 12.2 → 12.1; **−0.82%** (−2.50 to −0.81) | −0.58% (−0.89 to 2.16) | −0.27% (−0.34 to 1.91) | 3/3 |

No workload's paired median reached the 5% useful-effect threshold, so no
seven-pair confirmation was triggered. The results show no repeatable useful
request-level gain from the active grouped NInfer path across these five 8K
shapes. Three pairs are a screening result; ranges are descriptive and no
95% interval or generalization claim is made.

Minimum available physical/admission memory was 11.48 GiB, above the 6-GiB
floor. Cgroup `high`, `max`, `oom` and `oom_kill` counters stayed zero. GPU
clocks were observed dynamically from 306 to 1,300.5 MHz; no clocks were
changed. EMC clock readback was denied, and energy was not measured. The
complete compact per-process measurements are in [`summary.json`](summary.json);
raw requests, engine logs, memory/clock samples and residency maps remain local
under this directory.

The [focused 2K+128 screen](../2026-10-26-e6-q2-staged-compute-screen/README.md)
reached the same conclusion. Together with the exact grouped-operator parity
and slower 64/128-token operator timings in the [layer-boundary report](../2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#oracle-check-cpu-fallback-versus-cuda-expert-arithmetic),
this confirms there is no demonstrated compute or service-speed win for the
active grouped implementation on the screened Q2_0 shapes. The staged-versus-
CPU-miss result remains a separate comparison and is not qualified by this
screen.
