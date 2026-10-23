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

Reproduce from the repository root:

```sh
python3 bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/rail-followup/analyze_rail_energy.py
```

The source campaign is pinned by its parent
[`SHA256SUMS.txt`](../SHA256SUMS.txt). The script reads only the retained
compressed request, memory and tegrastats records.
