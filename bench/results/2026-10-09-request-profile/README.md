# First request profile — Jetson Orin, 2026-10-09

The pinned Strata control completed one warmup and one measured pp512+tg64 API
request under Nsight Systems 2024.5.4.34. Exact formatted counts are 512 prompt /
64 generated with zero cache reuse; actual context4096, prefill64, 6519 expert
slots/12695 MiB, fp16 KV, native spec6 and MTP max4 match the ordinary controls.
The bounded supervisor passes with minimum MemAvailable 7.8669 GiB, retaining
the six GiB floor and separate engine3072 MiB reserve. Clocks, services and
JetPack are unchanged. This is profiling preparation, not a paired performance
measurement, kernel promotion, Phase 4 completion or numerical/state pass.

## Observed candidate for further qualification

| Profiled request | Client duration ms | Summed GPU kernel duration ms | Q6_K→FP16 dequant summed ms | Fraction of summed kernel duration |
| --- | --- | --- | --- | --- |
| Warmup | 24068.321 | 14263.608 | 3292.411 | 23.08% |
| Measured | 14689.299 | 10172.476 | 2407.189 | 23.66% |

Q6_K dequantization is the largest named kernel by summed duration in each
request window, with 1024 instances each. The measured next entries are Q5_K
materialization (~748 ms), prefill MMQ copy16 (~653 ms), Q4_K materialization
(~509 ms) and IQ4_XS materialization (~462 ms). This makes represented-weight
materialization a measured hypothesis to investigate rather than selecting a
kernel from historical NInfer wins alone. A future change must qualify Q6_K
math/packing, prove memory/lifetime behavior, and demonstrate held-out request
benefit. The existing IQ4_NL exact-bit diagnostic does not qualify Q6_K/FP16.

Summed kernel duration includes concurrent streams and spin waits. It is not
GPU utilization, a share of wall time or the request's critical-path fraction.
The warmup's wait_flag_ge spin kernels account for ~1815 ms; those events can
represent waiting on CPU work, not useful GPU arithmetic. CPU IP sampling and
context-switch collection are disabled, so this trace cannot establish CPU
compute attribution. No speedup or optimal CPU/GPU split is concluded.

## Boundaries and retained evidence

The whole-process CSV summaries include startup and teardown. In particular,
CUDA library loading and allocation dominate several API aggregates; they must
not be relabeled as request costs. Request windows in `window-summary.json`
use the export's session UTC epoch and the median adjacent wall/monotonic pairs
from the memory sampler. Sampled offset spread is ~0.00143 ms. Absolute alignment
error is not independently bounded and there are no request NVTX markers.
The ±50 ms boundary check is sensitivity, not a confidence interval. Q6_K remains
top-ranked: measured dequant duration2396.071–2407.189 ms and warmup3292.411–
3298.764 ms across contracted/expanded windows. No exact prefill/decode split
is inferred from approximate request boundaries.

The Nsight capture traces CUDA/NVTX/OSRT, CUDA graph nodes and memory events in
the launched process tree. Raw profiler reports and SQLite stay in ignored
build storage; hashes identify them without adding binary build products or
process metadata to Git. Text kernel/API/copy summaries, requests, capabilities,
commands, memory and engine logs are retained here. Tegrastats rails are raw;
no integrated or whole-board energy claim is made. Model artifacts remain under
`~/models/`, identified by the paired control manifest. `identities.json`
records the exact pinned binary and analysis source.

## Reproduce

The retained supervisor command in `result.json` profiles an owned loopback
server with the explicit pinned config and one workload. It uses no global
service or clock changes. Export and summarize locally:

```sh
nsys stats --report cuda_gpu_kern_sum,cuda_api_sum,cuda_gpu_mem_time_sum \
  --format csv --output NEW_STATS --force-export=true PROFILE.nsys-rep
python3 bench/results/2026-10-09-request-profile/analyze_windows.py \
  --sqlite PROFILE.sqlite --requests REQUESTS.json --memory MEMORY.jsonl \
  --output NEW_WINDOW_SUMMARY.json
```

The script opens SQLite read-only and creates exclusive output. It requires one
session epoch and successful request records with observed GPU kernels. Its
interval union is reported separately from summed durations to preserve overlap
semantics. New profiler runs remain diagnostic; use the independent unprofiled
paired harness for performance confirmation. All later integration gates remain
required.
