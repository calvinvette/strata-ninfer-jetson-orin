# Q2_0 cache × prefill named-rail energy follow-up — Orin

This retrospective analysis integrated the named tegrastats power rails over
the 28 measured API request windows from the seven-block held-out cache ×
prefill confirmation. It adds an energy dimension to those existing request
measurements; it does not rerun the model or change the original performance
analysis.

All 28 windows were bracketed by telemetry samples with no gap over 2.5
seconds. Each request used the exact 7,506-token retrieval prompt and returned
41 tokens. Power was integrated linearly over the API request's monotonic time
window, mapped to wall time with the first supervisor memory sample. Effects
are paired within each randomized block; confidence intervals bootstrap the
seven blocks. Energy is reported both per completion token and per total input
plus output token. Since token counts are fixed across cells, relative effects
are equal for both normalizations.

For `VIN_SYS_5V0`, the median was 0.592 J per total token at cache 3,000 /
prefill 32, and 0.241 J at cache 3,000 / prefill 128. At cache 3,500, it was
0.583 J at prefill 32 and 0.237 J at prefill 128. Chunk 128 reduced the paired
median energy per total token by 59.43% at cache 3,000 (95% block-bootstrap
interval: 56.53%–59.68% lower) and 59.41% at cache 3,500 (59.23%–60.26%
lower). The cache effect at chunk 32 was −1.16% (interval −2.19% to +1.09%);
at chunk 128 it was −1.79% (−7.86% to −0.57%). The cache × prefill
ratio-of-ratios was −1.79% (−6.99% to +0.68%), so this energy analysis does
not resolve an interaction.

`VDD_GPU_SOC` and `VDD_CPU_CV` results, per-window energies, both token
normalizations, and paired interaction estimates are in
[`rail-energy-analysis.json`](rail-energy-analysis.json). Each named rail
includes board idle/background activity. These are not process-attributed
energy, are not summed into a whole-device total, and support no universal
energy-per-token claim. This is a Q2_0 model/workload/profile result only.

## Descriptive Pareto view

The follow-up also combines the seven-block medians for TTFT, client total
time, decode rate, minimum observed host availability, `VIN_SYS_5V0` energy
per total token, and engine logical mapped-file bytes. All 28 cells returned
the exact answer. Every profile is nondominated across these selected
dimensions; the table is descriptive and does not substitute for the paired
latency intervals in the parent report.

| Expert slots | Prefill chunk | Median TTFT (s) | Median request (s) | Decode (tok/s) | Minimum host available (GiB) | `VIN_SYS_5V0` (J/total token) | Logical file reads (MB/request) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3,000 | 32 | 668.0 | 673.1 | 7.2 | 18.16 | 0.592 | 10,113.6 |
| 3,000 | 128 | 267.6 | 273.3 | 7.2 | 18.10 | 0.241 | 10,094.3 |
| 3,500 | 32 | 659.6 | 664.8 | 7.2 | 17.49 | 0.583 | 9,790.2 |
| 3,500 | 128 | 263.0 | 268.2 | 7.2 | 17.47 | 0.237 | 9,704.4 |

The larger cache was slightly faster and had fewer engine logical file reads,
with less host availability. Chunk 128 lowered latency and named-rail energy,
with a small reduction in worst observed host availability. `file_mb` is an
engine logical mapped-file counter, not physical disk traffic; per-request
physical disk I/O was not attributed. The Pareto set is scoped to these four
cells and the tested held-out task.

Reproduce from the repository root:

```sh
python3 bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/rail-followup/analyze_rail_energy.py
```

The source campaign is pinned by its parent
[`SHA256SUMS.txt`](../SHA256SUMS.txt). The script reads only the retained
compressed request, memory and tegrastats records.
