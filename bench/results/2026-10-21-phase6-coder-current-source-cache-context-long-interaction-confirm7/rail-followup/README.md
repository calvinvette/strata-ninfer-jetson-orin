# Named-rail energy follow-up for the Coder cache × context confirmation

This analysis retrospectively integrates the retained Orin tegrastats readings
over the 28 measured request windows from the seven-block 2×2 cache × context
confirmation. The source campaign excludes its original block 7, which crossed
local midnight, and uses the same-day block-07 replacement. All 28 windows had
bracketing one-second rail samples with no gap over 2.5 seconds. Each request
returned the exact 48-token answer.

At 8K context, the 3,000 MiB requested-cache arm used median per-output-token
rail readings of 46.58 J on `VIN_SYS_5V0`, 58.24 J on `VDD_GPU_SOC`, and 6.40 J
on `VDD_CPU_CV`, versus 50.60 J, 61.16 J and 8.32 J at 1,500 MiB. The paired
median changes were −7.42% (95% block-bootstrap interval −11.41% to −6.88%),
−4.64% (−7.38% to −4.56%) and −22.97% (−31.82% to −22.49%), respectively.

At 16K context, the corresponding 3,000 MiB medians were 46.68 J, 58.41 J and
6.50 J, versus 50.21 J, 61.05 J and 8.25 J at 1,500 MiB. Paired changes were
−7.05% (−7.15% to −6.61%) on `VIN_SYS_5V0`, −4.32% (−4.43% to −4.13%) on
`VDD_GPU_SOC`, and −20.52% (−23.02% to −19.74%) on `VDD_CPU_CV`. The median
cache-by-context energy ratio-of-ratios was +0.39% (+0.29% to +4.85%) for
`VIN_SYS_5V0`, +0.51% (+0.31% to +3.30%) for `VDD_GPU_SOC`, and +3.72%
(+2.85% to +15.89%) for `VDD_CPU_CV`.

These are separate named-rail integrals, not summed and not process-attributed;
they include board idle and other background activity. `VIN_SYS_5V0` is one
input rail and is not presented as whole-device energy. The 3,000 MiB cache was
faster in the source campaign (median client latency reductions of 7.95% at 8K
and 7.71% at 16K), so this adds a complementary energy observation for the
same workload and profile. It does not establish a whole-device energy Pareto
frontier or change a default. Source data, exact pairing, rail values and
bootstrap results are in [`rail-energy-analysis.json`](rail-energy-analysis.json);
rerun with `python analyze_rail_energy.py`.
