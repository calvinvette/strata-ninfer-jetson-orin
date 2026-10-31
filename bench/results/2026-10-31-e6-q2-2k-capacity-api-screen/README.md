# No-trace API screen at 2K configured capacity

Date: 2026-10-31. Device: Jetson AGX Orin (`orin1`). Model: Qwen3.8-Flash-Next GSQ-RCO Q2_0, same GGUF artifacts as the [64K no-trace screen](../2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-pp65536-cap131072-README.md). Source revision: `12d82c92de7e5e1dee173c33a90ea9e9da3e7445`; CUDA executable SHA-256: `0b8eadf1f3894efe449d9b96082f7e83cd9aa2bf616f6161625b95f7001ccf37`.

## Setup

Three randomized same-day independent-process pairs (orders: baseline then candidate, candidate then baseline, baseline then candidate for the 2K cell; candidate then baseline in all 8K pairs) compared Strata with strict NInfer at `--max-context 2048`. Each measured request used a 512-token prompt and 64 generated tokens; each process sent the same workload once as warmup, then once measured. Both arms used the same cache size (3,000 experts), 6 GiB resident budget, 3 GiB workspace reserve, MTP-2, prefill 128, eight workers, prompt cache off, and PCIe staging off. Tracing was disabled. CPU frequencies sampled in tegrastats varied from 729 to 2,201 MHz; GPU frequency and EMC readbacks were unavailable. Energy was not measured.

All six measured requests and six warmups passed. Warmup and measured text matched across arms in all three pairs; this is output equivalence on the synthetic workload, not an independent quality oracle.

## Paired results

Candidate changes are NInfer relative to Strata; positive TPS is faster and positive latency is slower. Intervals bootstrap whole paired processes; three pairs are screening only.

| Metric | Strata median | NInfer median | Median paired change | Paired bootstrap 95% interval |
|---|---:|---:|---:|---:|
| Prompt TPS | 30.20 tok/s | 30.49 tok/s | +1.31% | +0.39% to +1.61% |
| Decode TPS | 8.70 tok/s | 8.90 tok/s | -0.04% | -1.34% to +2.30% |
| First-visible TTFT | 17.11 s | 16.95 s | -1.22% | -1.53% to -0.50% |
| Client total | 24.22 s | 23.99 s | -0.83% | -0.95% to -0.63% |

No median reached the 5% useful-effect threshold. With only three pairs, these are screening estimates; some intervals exclude zero for small effects, which does not establish a practically useful gain. The cell is included in the [combined paired-effect chart](../2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-effects-chart/paired-effects.svg).

## Resources and limitations

Minimum available physical RAM during measured requests was 11.66 GiB, above the six-GiB floor; sampled cgroup OOM-kill counts were zero. Peak sampled swap use was 2.10 GiB. CPU frequencies varied from 729 to 2,201 MHz; GPU frequency and EMC readbacks were unavailable. Energy was not measured. This is screening evidence, not performance qualification or near-limit ingestion. Raw telemetry remains in `/tmp/e6-no-trace-api-pp512-cap2048/`; only sanitized paired summaries are committed. See [`paired-summary.json`](paired-summary.json).

