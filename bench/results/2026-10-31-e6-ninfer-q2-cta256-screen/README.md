# Q2_0 grouped CTA schedule screen

Date: 2026-10-31. Device: Jetson AGX Orin Developer Kit (SM87), CUDA 12.6. The tested artifact was `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf`; activation input was layer 3, position 520, expert 94. The harness used CUDA-event timelines for one-token resident and grouped 64/128-token Q2_0/Q8_1 operators. It compares the default 128-thread CTA mapping with an opt-in 256-thread mapping (`STRATA_NINFER_Q2_CTA256=1`); arithmetic and 16-lane row grouping are unchanged. This is operator evidence, not request-level performance.

## Results

The combined six paired blocks show the 256-thread mapping increased median NInfer operator latency by **2.46%** for one token, **2.92%** for grouped 64 tokens and **2.50%** for grouped 128 tokens. Paired bootstrap 95% percentile intervals were +1.78% to +3.27%, +1.90% to +3.57%, and +2.39% to +2.57%, respectively. Latency is lower-is-better. It therefore loses on all three measured shapes and misses the plan's 5% useful-effect threshold. The 128-thread default remains the only qualified schedule.

| Shape | Default NInfer median | 256-thread median | Candidate latency change (95% paired interval) | Default NInfer/Strata | 256-thread NInfer/Strata |
| --- | ---: | ---: | ---: | ---: | ---: |
| One token | 24.06 us | 24.64 us | +2.46% (+1.78%, +3.27%) | about 0.97x | about 1.00x |
| Grouped 64 | 4,516.54 us | 4,632.51 us | +2.92% (+1.90%, +3.57%) | about 1.14x | about 1.17x |
| Grouped 128 | 9,151.02 us | 9,377.77 us | +2.50% (+2.39%, +2.57%) | about 1.15x | about 1.18x |

Ratios to Strata are descriptive ratios of displayed medians, not paired effect estimates. The source hypothesis was that doubling rows per CTA would reduce CTA scheduling overhead while preserving 16-lane row work. The observed grouped slowdown provides no evidence that CTA count was the limiting factor at these shapes. No end-to-end confirmation was run because the operator screen rejected the candidate.

## Correctness and protocol

All 12 process runs exited successfully. Independent scalar Q2_0/Q8_1 D3/D4 oracle checks passed (relative L2 `2.0533e-7`, maximum absolute error `1.4897e-8`); grouped gate/up/SwiGLU bytes matched exactly; grouped resident outputs matched Strata exactly; fixed-input repeated calls were stable; and grouped 3, 64 and 128 token boundaries passed. All output files had the same SHA256 (`adcf17a835454a6cfbb24c1a2acd9e088d5d962fc060b607a548da94ff424f40`).

The first three-pair screen accidentally placed the candidate first in every pair; it is retained as order-confounded screening evidence. A further three pairs used the explicit counterbalanced order candidate→baseline, baseline→candidate, candidate→baseline. The estimates above combine all six blocks; the counterbalanced follow-up alone showed the same slowdown direction. Small sample size and the imperfectly balanced combined order mean the intervals are screening uncertainty, not a formal confirmation. Timing blocks are operator-level repetitions nested inside each independent process and are not treated as independent paired samples.

Minimum sampled available RAM across runs was 24.33 GiB; no run hit the six-GiB physical-memory floor or reported OOM. CPU observations ranged 729.6–2,201.6 MHz, GPU 306–1,300.5 MHz, and EMC readback was denied. Clocks were dynamic. Energy was not measured. No clock or service settings were changed.

The experiment is reproducible from the current source with the `STRATA_NINFER_Q2_CTA256` environment variable set for the candidate. The candidate source SHA256 was `b80472993ebef296be7f754ea16e9b79bbe4e34275f0204c48e3cd3977754c3d`; tested parity executable SHA256 was `698658343adc50c41ca73aa157c1ddc3049bd8a5307921c6a2f93e37383fc0c5`. Build was the Orin CUDA integration build with one-job memory-bounded compilation. Detailed per-pair timings, output hashes, resources and interval calculations are in [`paired-summary.json`](paired-summary.json). Raw supervisor traces and output tensors remain under `/tmp` and are not committed.
