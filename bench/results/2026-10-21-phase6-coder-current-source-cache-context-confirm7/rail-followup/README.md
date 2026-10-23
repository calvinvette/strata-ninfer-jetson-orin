# Named-rail energy follow-up for the short Coder cache confirmation

This analysis integrates the retained tegrastats readings over 42 measured
request windows from the seven-block 8K-context Coder cache confirmation. Each
fresh-service cache cell had one warmup and three measured requests; all 42
returned the exact 47-token answer. All request windows had bracketing one-second
rail samples with no gap over 2.5 seconds.

Each cell's rail estimate is the median energy per output token across its three
requests. With the 3,000 vs 1,500 MiB requested cache, paired median changes
were −11.19% on `VIN_SYS_5V0` (95% block-bootstrap interval −11.45% to −10.16%),
−2.90% on `VDD_GPU_SOC` (−3.75% to −2.44%), and −14.65% on `VDD_CPU_CV`
(−17.39% to −13.15%). The `VIN_SYS_5V0` medians were 3.58 J/output token at
3,000 MiB and 4.03 J/output token at 1,500 MiB.

These are separate named-rail integrals, not summed or process-attributed;
they include idle/background activity. `VIN_SYS_5V0` is one input rail, not a
whole-device energy measure. The result adds a short-task energy observation at
8K to the same-day long-task cache × context rail analysis, but does not support
a general cache setting or close Phase 6. Full windows and bootstrap results
are in [`rail-energy-analysis.json`](rail-energy-analysis.json); rerun with
`python analyze_rail_energy.py`.
