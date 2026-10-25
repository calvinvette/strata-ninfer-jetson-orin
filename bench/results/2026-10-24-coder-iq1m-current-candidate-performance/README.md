# Current candidate: Coder IQ1_M performance

Measured 2026-10-24 on the local Jetson AGX Orin with the Coder IQ1_M model
pair from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. Both local shard SHA256 values
match the repository manifest. The model and deployment pack remain under
`~/models/strata-orin-validation/`; see [artifacts.json](artifacts.json) for
checksums and identity.

The measured binary is `build/integration/candidate/strata`, SHA256
`ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df`, built
from source commit `348e6261ab3fa5f119ec3050637c01477fddaa78`. It used the
Coder expert profile, a requested 3,000-slot cache (3,903 realized slots),
128-token prefill chunk, eight pool workers, mapped experts, 3,072 MiB
workspace reserve, 8K context and FP16 KV. Prompt cache and MTP were off.
MAXN was selected by the existing system state; clocks remained dynamic and
were observed only. No service, clock, or power setting was changed.

Seven independently supervised server processes each ran one excluded warmup
and one measured request for each workload, in randomized workload order.
Every measured request passed fresh-prefill and exact requested-token-count
checks. Intervals below are 95% percentile intervals for the median from
20,000 bootstrap resamples of the seven process blocks.

| Prompt + generated tokens | Prompt rate (tok/s) | Generated rate (tok/s) | Client TTFT (s) | Full request (s) | Max of 7 request times (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 512 + 64 | 65.2 [64.3, 65.7] | 16.0 [15.9, 16.1] | 7.93 [7.87, 8.05] | 11.85 [11.79, 11.99] | 19.13 |
| 2,048 + 128 | 68.5 [65.4, 68.8] | 15.9 [14.7, 15.9] | 29.97 [29.83, 31.40] | 37.97 [37.81, 40.01] | 49.00 |

The maximum is shown as a descriptive tail observation, not a stable p95
estimate. Prompt/decode rates are engine reported; TTFT and full request time
are client measured. Output text had one SHA256 per workload across the seven
blocks. This is repeatability evidence for text, not an independent quality
oracle. No output-quality evaluation was performed.

Minimum sampled physical `MemAvailable` across the campaign was 14.18 GiB;
minimum admission availability was 9.69 GiB (the admission floor was 6 GiB).
Within measured requests, minima were 14.31 GiB physical and 12.86 GiB
admission availability. Swap use peaked at 2.81 GiB. The 28 GiB cgroup recorded
zero memory pressure/max/OOM events. These are measurements of Orin's one
shared physical memory pool; CUDA memory is not added to host RAM.

Host-wide NVMe read deltas had medians of 0.016 GB/request at 512/64 and
0.021 GB/request at 2,048/128. These counters are not process attributed and
include unrelated I/O/read-ahead. Energy was not measured; tegrastats rail
values are retained as raw telemetry only. CPU clocks ranged 0.730–2.202 GHz,
GPU clocks 306–1,301 MHz and reported temperature 49.1–63.7 C. EMC clock
readback was unsupported.

This is a standalone Coder IQ1_M cohort. It is not a same-day paired comparison
with the IQ3_S or Q2_0 model runs, and differences across those reports must
not be attributed to quantization or used to claim a speedup. It does not
change the bounded Q2_0 release profile. Raw per-process logs and telemetry,
the workloads, config template, summarizer, summary and artifact identity are
retained in this directory.
