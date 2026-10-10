# Phase 3 larger owned prefill chunks

This follow-up extended the supervised Orin resource screen to 1024- and 2048-token owned prompt-buffer configurations. It evaluates initialization, reservation sizing, automatic expert-cache response and the six-GiB host-memory admission floor. It does not claim that the configured chunk was fully exercised.

## Method and results

Each setting ran in a separate process with Qwen3.8-Flash-Next Coder IQ1_M from `~/models/strata-orin-validation`, automatic expert cache, context 4096, FP16 KV, speculation 4, `--no-prefill-borrow`, `--vram-reserve-mib 3072` and PCIe fraction 0.55. The same formatted 172-token prompt ran as warmup and once measured with an eight-token generation cap. Owner tracing was enabled. Each process was supervised with a 6,442,450,944-byte six-GiB `MemAvailable` floor; clocks were unchanged and energy was not measured.

| Chunk | Prefill workspace hold | MTP bind hold | VRAM slack hold | Actual expert slots | Cache reported | Minimum `MemAvailable` | Workload |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1024 | 840 MiB | 219 MiB | 3072 MiB | 6684 | 13016 MiB | 7.72 GiB | pass |
| 2048 | 1520 MiB | 219 MiB | 3072 MiB | 6338 | 12339 MiB | 8.03 GiB | pass |

The prefill holds match the current automatic-sizing estimate (160 MiB plus 680 MiB per 1024 chunk tokens). The 3 GiB workspace slack remains separate. Automatic expert-cache sizing reduced actual slots as the owned-workspace hold grew. The measured host-memory minimum did not monotonically fall with the larger hold because cache sizing and system sampling are not an additive ledger.

Both short API requests completed without a floor breach. Since the actual prompt was 172 tokens, neither run filled its configured chunk. This is not a late allocation-failure test, full-chunk validation, process-wide physical ownership accounting, numerical qualification, or a performance comparison.

## Artifacts

`matrix.json` records settings, observed slots, reservations and minimum availability. Each cell retains its explicit configuration, capability response, request result, engine log, parsed owner summary and supervisor telemetry. `workloads.json` contains the exact workload and tokenizer hashes. Model files remain in `~/models`; no model or build products are included here. `SHA256SUMS` covers the preserved artifacts.
