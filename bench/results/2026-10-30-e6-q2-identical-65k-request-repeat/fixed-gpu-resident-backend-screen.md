# Fixed-GPU resident-backend screen

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is a three-pair
screening result, not performance qualification.

## Setup

Three fresh-process pairs used the same strict-NInfer build, Q2_0 Flash-Next
model, 65,536-token prompt, 32-token generation, 131,072 context, 128-token
prefill chunk, 3,000-entry cache, and static profile. The profile ranked
layer-1 expert 320 into GPU slot 0. Adaptation, PCIe staging, prompt caching,
and tracing were disabled. Backend was the only arm setting changed. Pair
orders were NInfer/Strata, NInfer/Strata, and Strata/NInfer; the sequence
was mixed but not balanced. All six requests
emitted the same 32 token IDs (SHA-256
`39ee5b12b699554c28d18b3c152a3003a2b268860c616ea64a808519dd211670`) and
reported 1,870/15,360 cache hits (12.2%).

## Results

| Pair | Order | NInfer prefill | Strata prefill | NInfer decode | Strata decode | Paired NInfer change: prefill / decode |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | NInfer first | 86.6 | 87.0 | 3.9 | 4.1 | -0.46% / -4.88% |
| 2 | NInfer first | 85.2 | 86.1 | 4.1 | 0.9 | -1.05% / +355.56%* |
| 3 | Strata first | 86.9 | 86.4 | 4.1 | 4.1 | +0.58% / 0.00% |
| Median paired change |  |  |  |  |  | **-0.46% / 0.00%** |

Rates are tokens/s. *Pair 2's Strata decode rate is a large unexplained
outlier. In that arm CPU median frequency was about 729 MHz versus 2,201 MHz
in the NInfer arm; both reported 99% GR3D utilization and temperatures stayed
near 60 C. The available telemetry did not include GPU clock, so the cause is
not established. The opposite-order third pair returned to 4.1 tok/s for both
backends. Do not interpret the pair-2 difference as an NInfer gain.

The three-pair median does not meet the preregistered 5% improvement screen
for either metric. Do not proceed to seven-pair confirmation on this
fixed-GPU resident path. This limited result does not test other cache hit
rates, ownership patterns, prompt sizes, or workloads, and exact token
equality is not an independent quality oracle. Minimum available RAM was
8.44–8.77 GiB; peak sampled swap was 1.45–6.72 GiB; sampled cgroup OOM kills
were zero. Energy was not measured, clocks were dynamic, and TTFT was not
collected. Raw logs and supervisor telemetry remain under `/tmp/e6-fixed-gpu-backend-ablation*`.
