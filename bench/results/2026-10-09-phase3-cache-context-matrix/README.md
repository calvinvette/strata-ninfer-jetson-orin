# Phase 3 requested cache × context admission screen

This Orin AGX screen exercised the Phase 3 cache-cap × context-reservation matrix with the integrated Strata runtime. It answers whether the four configured combinations initialize, complete a small API request, and retain the required physical-memory headroom. It is not a performance or quality comparison.

## Method

Each cell ran in its own server process, in this seeded order (`10092026`): 3000/8192, 5000/4096, 5000/8192, 3000/4096. Each used the Qwen3.8-Flash-Next Coder IQ1_M Orin validation model and MTP runtime pack under `~/models/strata-orin-validation`, CUDA 12, FP16 KV, speculation 4, prefill 64, mmap experts, 3072 MiB VRAM reserve, and PCIe fraction 0.55. The same exact formatted 172-token prompt was sent once as warmup and once as the measured request with an eight-token generation cap. The owner trace was enabled. `run_control.py` supervised each process with a 6,442,450,944-byte (six-GiB) minimum `MemAvailable` floor. Clocks were not changed. Energy was not measured.

## Results

| Requested cache lower bound | Context reservation | Actual expert slots | Reported cache | Free VRAM after init | Minimum system `MemAvailable` | Workload |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 3000 | 4096 | 3903 | 7615 MiB | 13944 MiB | 13.34 GiB | pass |
| 3000 | 8192 | 3903 | 7615 MiB | 13853 MiB | 13.10 GiB | pass |
| 5000 | 4096 | 6519 | 12695 MiB | 8895 MiB | 8.36 GiB | pass |
| 5000 | 8192 | 6519 | 12695 MiB | 8823 MiB | 8.35 GiB | pass |

The requested cache values are lower bounds in the current device-sizing policy, not exact capacities: requesting 3000 yielded 3903 slots, and requesting 5000 yielded 6519. The 8192 context setting increased the observed session owner's requested payload from about 224 MiB to 327 MiB, while the large cache setting dominated the system-memory headroom difference. Trace totals are scoped to instrumented owners and requested payload bytes; they are not a process-wide or physical-backing ledger. At log end, session payload remains live as expected for the server lifetime. Planned reservation events were empty in these runs, so this screen does not validate reservation accounting.

Each cell had one measured request. The harness emitted prompt and generation rates, but those single-request values are not independent replicates and are not compared here. The request completion status does not establish numerical quality, accepted-prefix state parity, long-context recall, sustained behavior, or performance. No failure or floor breach occurred. GPU/EMC clocks and energy are not part of this screen.

## Reproduction and artifacts

`matrix.json` records cell order, configuration, command, exit status and minimum available memory. Each cell directory contains its exact server config, capability response, request result, supervisor telemetry, engine log, and parsed owner summary. `workloads.json` retains the formatted prompt and tokenizer file hashes. Model files remain under `~/models` and are not copied into this repository. `SHA256SUMS` covers the preserved screen artifacts.
