# Current candidate: Q2_0 performance on Orin

Measured 2026-10-25 on the local Jetson AGX Orin using the Q2_0 shards from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. Both model shard hashes match the
Phase 7 artifact manifest and [qualified profile record](../../../docs/integration/RELEASE_PROFILE.md).
The model and pack remain in `~/models/strata-orin-validation/`.

Before testing, the Release build tree was cleaned and `strata` rebuilt with
two parallel jobs under a 24 GiB build cgroup. The resulting executable hash
is `ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df`,
matching the current candidate used for the preceding Coder IQ1_M campaign.
Build checkout was `3774a9de`; the runtime source tree matches
`348e6261ab3fa5f119ec3050637c01477fddaa78`.

The run used the documented Q2_0 profile: 8K context, FP16 KV, MTP drafts off,
3,000 exact profile-ranked expert slots, 128-token prefill chunk, eight workers,
mapped experts, 3,072 MiB workspace reserve, prompt cache and adaptive swaps
off. MAXN was already selected; clocks were observed dynamically and never
changed. Full model, pack and configuration identity is in
[artifacts.json](artifacts.json).

Seven independently supervised server processes each performed one excluded
warmup and one measured request per workload; workload order was randomized.
All 14 measured requests passed fresh-prefill and exact requested-token-count
checks. Intervals are 95% percentile intervals for the median from 20,000
bootstrap resamples of the seven independent process blocks.

| Prompt + generated tokens | Prompt rate (tok/s) | Generated rate (tok/s) | Client TTFT (s) | Full request (s) | Max of 7 request times (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 512 + 64 | 32.6 [32.0, 37.3] | 10.2 [9.8, 10.6] | 15.88 [13.91, 16.20] | 22.00 [20.28, 22.11] | 22.73 |
| 2,048 + 128 | 54.2 [53.8, 54.4] | 10.4 [10.3, 10.5] | 37.97 [37.83, 38.21] | 50.10 [50.03, 50.30] | 50.92 |

The maximum is descriptive and is not a stable p95 estimate. Prompt/decode
rates are engine-reported; TTFT and full request duration are client-measured.
Output text had one hash across the seven short-workload blocks and two hashes
across the long-workload blocks. This is repeatability evidence only; no
independent output-quality oracle was run.

Minimum sampled physical `MemAvailable` during the campaign was 17.74 GiB and
minimum admission availability was 7.36 GiB, above the required 6 GiB floor.
Within measured requests the minima were 18.30/18.58 GiB physical and
8.91/8.89 GiB admission availability for the long/short cells. Swap use peaked
at 2.79 GiB. The 28 GiB runtime cgroup recorded zero memory pressure/max/OOM
events. These values describe Orin's shared physical-memory pool; host RAM and
CUDA capacity are not added together.

Host-wide NVMe read deltas were about 4.95 GB per request for both workloads.
They are not process-attributed and include other I/O and read-ahead. Energy
was not measured; tegrastats rails are retained only as raw telemetry. Observed
CPU clocks ranged 0.730–2.202 GHz, GPU clocks 306–1,301 MHz and reported
temperature 48.1–61.3 C. EMC clock readback was unsupported.

This Q2_0 run is a standalone model/format cohort. It is not a same-day paired
comparison with the separate Coder IQ1_M or IQ3_S runs, so differences between
their numbers do not establish a quantization speedup. This performance report
does not expand the bounded Q2_0 functional qualification. Raw process logs,
telemetry, requests, campaign metadata, config, workloads and summarizer are
retained alongside this report.
