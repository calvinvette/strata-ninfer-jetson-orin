# No-trace API screen at 128K configured capacity

Date: 2026-10-31. Device: Jetson AGX Orin (`orin1`). Model: Qwen3.8-Flash-Next GSQ-RCO Q2_0, same GGUF artifacts as the [64K no-trace screen](../2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-pp65536-cap131072-README.md). Source revision: `12d82c92de7e5e1dee173c33a90ea9e9da3e7445`; current CUDA executable SHA-256: `0b8eadf1f3894efe449d9b96082f7e83cd9aa2bf616f6161625b95f7001ccf37`.

## Setup

Three randomized same-day independent-process pairs compared Strata with strict NInfer at `--max-context 131072`. Each measured request used a 512-token prompt and 64 generated tokens; each process sent the same workload once as warmup, then once measured. Both arms used the same cache size (3,000 experts), 6 GiB resident budget, 3 GiB workspace reserve, MTP-2, prefill 128, eight workers, prompt cache off, and PCIe staging off. Tracing was disabled. CPU/GPU clocks were observed read-only and remained dynamic; no clock controls were used. EMC readback was unavailable. Energy was not measured.

All six measured requests and six warmups passed. Warmup and measured text matched across arms in all three pairs; this is output equivalence on the synthetic workload, not an independent quality oracle. Each measured request used 512 prompt and 64 completion tokens.

## Paired results

Candidate changes are NInfer relative to Strata; positive TPS is faster and positive latency is slower.

| Metric | Strata median | NInfer median | Median paired change | Paired bootstrap 95% interval |
|---|---:|---:|---:|---:|
| Prompt TPS | 21.95 tok/s | 22.77 tok/s | +0.29% | -5.28% to +7.62% |
| Decode TPS | 8.08 tok/s | 8.01 tok/s | -2.92% | -3.38% to +6.99% |
| First-visible TTFT | 23.57 s | 23.03 s | -0.27% | -7.02% to +5.57% |
| Client total | 31.07 s | 30.65 s | +0.56% | -6.93% to +5.05% |

No median reached the 5% useful-effect threshold; all intervals include no effect. The cell is included in the [combined paired-effect chart](../2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-effects-chart/paired-effects.svg). The 128K and 256K capacity screens both use short prompts and do not measure near-limit ingestion.

## Resources and limitations

Minimum available physical RAM during measured requests was 8.40 GiB, above the six-GiB floor; sampled cgroup OOM-kill counts were zero. Peak sampled swap use was 4.78 GiB. GPU clocks ranged from 306 to 1,300.5 MHz and observed CPU clocks from 729.6 to 2,201.6 MHz. These dynamic clocks and unmeasured energy limit the result. This is screening evidence, not performance qualification. Raw logs and telemetry remain in `/tmp/e6-no-trace-api-pp512-cap131072/`; only sanitized paired summaries are committed. See [`paired-summary.json`](paired-summary.json).
