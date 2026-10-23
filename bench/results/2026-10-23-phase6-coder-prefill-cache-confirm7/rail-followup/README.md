# Named-rail energy follow-up

This retrospective analysis integrates the retained Orin tegrastats samples
over the 28 measured API request windows in the seven-block Coder prefill
chunk × expert-cache confirmation. It uses the same monotonic-to-wall mapping
and piecewise-linear `request_telemetry.window_energy` method as the earlier
cache/context rail analyses. Each window had bracketing rail samples with no
gap above the supported 2.5-second limit. All cells returned the exact
46-token answer.

The table reports median joules per output token for each named rail and the
paired-block change for chunk 128 versus chunk 32:

| Rail | Requested cache slots | Chunk 32 J/output token | Chunk 128 J/output token | Median change | Paired-block bootstrap 95% interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| `VIN_SYS_5V0` | 1,500 | 90.54 | 30.67 | −66.27% | −66.50% to −66.00% |
| `VIN_SYS_5V0` | 3,000 | 84.03 | 27.60 | −67.15% | −67.29% to −66.92% |
| `VDD_GPU_SOC` | 1,500 | 106.77 | 40.88 | −61.73% | −61.77% to −61.67% |
| `VDD_GPU_SOC` | 3,000 | 101.12 | 39.00 | −61.40% | −61.52% to −61.29% |
| `VDD_CPU_CV` | 1,500 | 11.74 | 6.82 | −42.24% | −43.40% to −40.61% |
| `VDD_CPU_CV` | 3,000 | 9.95 | 4.95 | −50.18% | −51.58% to −49.39% |

The `VIN_SYS_5V0` cache-by-chunk ratio-of-ratios was −3.38% (−4.11% to
−1.95%). The corresponding `VDD_GPU_SOC` interaction was +1.00% (+0.28% to
1.26%); `VDD_CPU_CV` was −14.60% (−16.32% to −12.07%). The rails are kept
separate and not summed.

These readings cover the whole request window and include board idle and other
background activity. They are not process-attributed, and `VIN_SYS_5V0` is not
presented as whole-device energy. Normalizing by output tokens does not mean
the rails represent energy used by the model process. This supports only a
workload-specific named-rail observation; it does not establish an energy
Pareto frontier or recommend a general setting. Energy is not used to adjust
the latency conclusion.

Rerun from the repository root with:

```sh
python3 bench/results/2026-10-23-phase6-coder-prefill-cache-confirm7/rail-followup/analyze_rail_energy.py
```

The script writes [`rail-energy-analysis.json`](rail-energy-analysis.json),
including all window estimates, sample counts, pairing and interval outputs.
Raw `tegrastats.txt` and memory traces remain local and are not committed.
