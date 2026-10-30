# Fixed-GPU resident-backend ablation pilot

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is the first screening pair,
not performance qualification.

## Setup

One no-trace request per fresh process used the same Q2_0 Flash-Next model,
65,536-token prompt, 32-token generation, 131,072 context, 128-token prefill
chunk, 3,000-entry expert cache, and static profile. The experiment-only
profile ranked layer-1 expert 320 into GPU slot 0; adaptation and PCIe staging
were disabled. The backend was the only arm setting changed: `strata` versus
strict `ninfer`. Pair order was NInfer then Strata. The same strict-NInfer
build was used for both arms. Binary SHA-256:
`fc4fcd2268d8bc69bb55899a46af8ecf91723901f1944e9e7266da024beb2741`.

## Result

| Backend | Prompt rate (tok/s) | Decode rate (tok/s) | Decode GPU-cache hits | Generated tokens |
| --- | ---: | ---: | --- | ---: |
| Strict NInfer | 86.6 | 3.9 | 1,870 / 15,360 (12.2%) | 32 |
| Strata | 87.0 | 4.1 | 1,870 / 15,360 (12.2%) | 32 |

Both arms emitted identical token IDs (SHA-256
`39ee5b12b699554c28d18b3c152a3003a2b268860c616ea64a808519dd211670`). NInfer
was 0.46% slower on prompt rate and 4.88% slower on decode rate in this pair.
The prompt rates, token IDs and hit counts matched the intended profile and
workload. This is a single pair, so it does not estimate uncertainty or qualify
a performance effect. Matching token IDs is not a task-quality oracle.

The target expert's GPU ownership at the sampled prompt boundary was verified
in the same prompt/profile controls documented in the [owner repeat
report](layer1-moe-expert320-transition.md). This timing pair itself used no
trace or per-dispatch capture; it retained the engine's aggregate cache-hit
counter. Minimum available RAM was 8.68 GiB, peak sampled swap 1.69 GiB, and
sampled cgroup OOM kills were zero. Energy and clocks were not measured.

Raw outputs and telemetry remain under `/tmp/e6-fixed-gpu-backend-ablation*`.
The two follow-up pairs are complete; see the [three-pair screen](fixed-gpu-resident-backend-screen.md).
