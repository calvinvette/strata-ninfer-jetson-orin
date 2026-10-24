# MTP3 × KV × prompt-length screen — Orin — 2026-10-23

Three randomized paired blocks screened the planned 2×2×2 design: MTP off/MTP3,
FP16/INT8 KV, and 512/7,501-token prompts. The same synthetic Coder retrieval
and arithmetic task was used at both lengths, with exact expected answers
checked independently. All 24 fresh-process cells passed their request,
answer, actual KV, expert-residency and memory-floor checks. Each process had a
shared distinct 512-token warmup, prompt caching disabled, and a 28 GiB
systemd memory scope. No cell failed or aborted.

## Paired effects

| KV | Prompt | MTP3 decode throughput delta | Paired bootstrap 95% interval | TTFT delta | Total request delta |
| --- | --- | ---: | ---: | ---: | ---: |
| FP16 | 512 tokens | +8.42% | +7.62% to +9.48% | +0.19% | -0.75% |
| INT8 | 512 tokens | +8.47% | +6.00% to +9.00% | -0.03% | -0.73% |
| FP16 | 7,501 tokens | -3.53% | -3.73% to -3.34% | +0.49% | +0.51% |
| INT8 | 7,501 tokens | -4.73% | -4.98% to -4.18% | +0.64% | +0.67% |

MTP3 drafted/accepted 34/31 tokens on every short request and 28/24 on every
long request. The workload-length interaction in decode was -10.84% under FP16
KV (95% interval -12.07% to -10.37%) and -12.40% under INT8 (-12.60% to
-9.60%). The long-prompt MTP-by-KV decode interaction was -1.04% (-1.69% to
-0.67%); on the short task it was -0.44% (-1.51% to +0.05%). The three-way
decode interaction was -0.60% (-1.74% to +0.86%). These are screening
estimates from three blocks, not confirmation or a product profile. The
near-limit prompt is prefill-dominated: despite a repeatable decode loss,
total request time rose by only about 0.5–0.7% in this screen.

Minimum observed physical availability was 16.98 GiB; minimum admission
availability was 16.83 GiB, above the preserved six-GiB floor. Sampled cgroup
memory events remained zero. The runner sampled GPU clocks from 306 to
1,300.5 MHz; EMC clock readback was unavailable. Tegrastats retains CPU/GPU
utilization, temperatures and named rails. Rail energy was not integrated and
this was not sustained thermal qualification.

## Identity and limits

## Named-rail energy follow-up

The request windows were retrospectively integrated against bracketed
one-second tegrastats samples. All 24/24 windows were estimable. Each rail is
reported separately; these readings include idle/background activity, are not
process-attributed, and must not be summed or described as whole-device energy.
The comparison below is MTP3 versus MTP-off joules per output token across
three paired blocks; intervals are paired bootstrap 95% intervals.

| KV | Prompt | Rail | Median change | 95% interval |
| --- | --- | --- | ---: | ---: |
| FP16 | 512 | VDD_CPU_CV | +4.80% | +0.53% to +10.31% |
| FP16 | 512 | VDD_GPU_SOC | -7.37% | -7.66% to -6.59% |
| FP16 | 512 | VIN_SYS_5V0 | -3.23% | -4.67% to +1.65% |
| INT8 | 512 | VDD_CPU_CV | +4.14% | +2.61% to +8.87% |
| INT8 | 512 | VDD_GPU_SOC | -7.00% | -7.34% to -6.38% |
| INT8 | 512 | VIN_SYS_5V0 | -3.32% | -3.57% to -0.94% |
| FP16 | 7,501 | VDD_CPU_CV | +1.04% | +0.88% to +3.71% |
| FP16 | 7,501 | VDD_GPU_SOC | -0.22% | -0.69% to +0.04% |
| FP16 | 7,501 | VIN_SYS_5V0 | +0.52% | +0.48% to +0.84% |
| INT8 | 7,501 | VDD_CPU_CV | +4.31% | +3.12% to +5.36% |
| INT8 | 7,501 | VDD_GPU_SOC | -0.36% | -0.64% to -0.09% |
| INT8 | 7,501 | VIN_SYS_5V0 | +0.49% | +0.40% to +0.57% |

Short-prompt GPU-rail energy per output token fell while CPU-rail energy rose;
the named system rail was lower but its FP16 interval includes zero. At 7,501
tokens, system-rail energy per output token rose about 0.5% in both KV modes.
This supports the observed workload-length dependence, but is a small-screen
energy result, not a Pareto conclusion or sustained-power qualification. Raw
request estimates, paired rows and the reproducible integrator are in
`rail-energy.json`, `rail-energy-pairs.csv` and `analyze_rail_energy.py`.

- Source HEAD at campaign launch: `83e2d80166675d94540c5217189458e3eeebcb67`.
  The MTP3-capable factorial runner was implemented in `465056c6`.
- Device: Orin AGX, native aarch64, CUDA runtime path, shared physical RAM.
- Model: Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M Coder, with upstream
  base-checkpoint MTP weights. Model files remain in `~/models/strata-orin-validation`.
- Workloads: `coder-mtp-retrieval-short-512` and
  `coder-mtp-retrieval-near-limit-7501`; exact prompts and expected answers are
  in `campaign/selected-workloads.json`.
- Seed: 20261028. Every cell was randomized within each block.
- `campaign/campaign.json`, source config, all 24 cell configs/requests/logs,
  clock samples, memory traces, tegrastats, and the input workload file are
  retained. `SHA256SUMS.txt` covers this report tree.

This campaign checks output answers and performance, not accepted-prefix state.
It does not cover graph × speculation, adaptive long-chain state, multi-live
correctness, a broad quality suite or energy Pareto. Phase 5 and Phase 6 remain
open; no default changed.
