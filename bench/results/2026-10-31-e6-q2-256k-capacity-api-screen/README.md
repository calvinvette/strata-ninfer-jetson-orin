# No-trace API screen at 256K configured capacity

Date: 2026-10-31. Device: Jetson AGX Orin (`orin1`). Model: Qwen3.8-Flash-Next GSQ-RCO Q2_0, same GGUF artifacts as the [64K no-trace screen](../2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-pp65536-cap131072-README.md). Source revision: `12d82c92de7e5e1dee173c33a90ea9e9da3e7445`; the CUDA executable required no rebuild (`ninja -n strata`: no work), SHA-256 `0b8eadf1f3894efe449d9b96082f7e83cd9aa2bf616f6161625b95f7001ccf37`.

## Setup

Three randomized same-day independent-process pairs compared Strata with strict NInfer at `--max-context 262144`. Each measured request used a 512-token prompt and 64 generated tokens; each process sent the same workload once as warmup, then once measured. Both arms used the same cache size (3,000 experts), 6 GiB resident budget, 3 GiB workspace reserve, MTP-2, prefill 128, eight workers, prompt cache off, and PCIe staging off. Tracing was disabled. CPU/GPU clocks were observed read-only and remained dynamic; no clock controls were used. EMC readback was unavailable. Energy was not measured.

The six measured requests and six warmups passed. Warmup and measured text matched across arms in every pair (3/3 each); this is output equivalence for the synthetic cell, not an independent quality oracle. Prompt/output token counts were 512/64 in all requests.

## Paired results

Candidate changes are NInfer relative to Strata; positive TPS is faster and positive latency is slower.

| Metric | Strata median | NInfer median | Median paired change | Paired bootstrap 95% interval |
|---|---:|---:|---:|---:|
| Prompt TPS | 17.12 tok/s | 16.99 tok/s | -0.23% | -2.26% to +14.44% |
| Decode TPS | 6.96 tok/s | 6.98 tok/s | -0.68% | -4.24% to +4.31% |
| First-visible TTFT | 30.28 s | 30.52 s | +0.27% | -12.71% to +2.24% |
| Client total | 39.17 s | 39.33 s | +0.33% | -10.60% to +2.81% |

No median reached the 5% useful-effect threshold, and every interval includes no effect. The large prompt/latency interval widths come from one faster NInfer block; that block did not repeat in the other two. This is screening evidence and does not justify seven-pair confirmation or profile promotion. The added cell is included in the [combined paired-effect chart](../2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-effects-chart/paired-effects.svg).

## Resources and limitations

Minimum available physical RAM during measured requests was 7.07 GiB, above the six-GiB floor; sampled cgroup OOM and OOM-kill counters remained zero. Peak sampled swap use was 2.70 GiB. GPU clocks ranged from 306 to 1,300.5 MHz and observed CPU clocks from 729.6 to 2,201.6 MHz; dynamic variation remains a limitation. The campaign is a short-workload capacity screen, not near-limit ingestion, broad model-quality validation, or a performance qualification. Raw request bodies, server logs, memory traces and tegrastats captures remain in `/tmp/e6-no-trace-api-pp512-cap262144/` and were not added to Git.

Sanitized paired measurements are in [`paired-summary.json`](paired-summary.json); the combined chart source data was extended without copying raw responses.
