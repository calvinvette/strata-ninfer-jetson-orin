# Phase 3 prefill chunk × workspace admission screen

This Orin AGX screen exercises two prompt chunk sizes with the existing choice to borrow prompt buffers from the expert cache or allocate them separately. It records the resulting automatic cache sizing, explicit reservation holds and physical-memory headroom. It is not a speed or quality comparison.

## Method

Four independent server processes ran in this seeded order (`10092027`): chunk 512 borrowed, chunk 512 owned, chunk 64 owned, chunk 64 borrowed. Each process used the same Qwen3.8-Flash-Next Coder IQ1_M Orin validation model and MTP pack under `~/models/strata-orin-validation`; CUDA 12; FP16 KV; speculation 4; context 4096; automatic expert cache; `--vram-reserve-mib 3072`; and PCIe fraction 0.55. The owned-buffer cells added `--no-prefill-borrow`. Each sent the same formatted 172-token API prompt once as warmup and once measured, capped at eight generated tokens. `STRATA_INTEGRATION_TRACE=1` was enabled. Every process ran under `run_control.py` with the required 6,442,450,944-byte six-GiB `MemAvailable` floor. Clocks were not changed; energy was not measured.

## Results

| Chunk | Prompt buffers | Actual expert slots | Cache reported | Prefill workspace hold | MTP bind hold | VRAM slack hold | Minimum system `MemAvailable` | Workload |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 64 | Borrowed | 7113 | 13859 MiB | 0 MiB | 219 MiB | 3072 MiB | 7.47 GiB | pass |
| 64 | Owned | 7011 | 13655 MiB | 202 MiB | 219 MiB | 3072 MiB | 7.69 GiB | pass |
| 512 | Borrowed | 7088 | 13809 MiB | 0 MiB | 219 MiB | 3072 MiB | 7.49 GiB | pass |
| 512 | Owned | 6857 | 13353 MiB | 500 MiB | 219 MiB | 3072 MiB | 7.72 GiB | pass |

The owned workspace reservation matches the current sizing formula for these chunks (202 MiB at 64; 500 MiB at 512). The auto-cache path emitted the separately priced 3 GiB VRAM slack and about 219 MiB MTP bind hold in every cell. Borrowed prompt buffers emitted no separate workspace hold. In this short workload, the minimum observed host availability was not lower in owned-buffer cells; this does not mean owned buffers use less total memory. Cache sizing changes in response to the workspace price, and sampled `MemAvailable` is process/system telemetry rather than an additive accounting ledger.

Every cell completed its API request without crossing the floor. The trace reports requested payload at instrumented owners and does not cover all process allocations or CUDA graph-pool backing. One measured request per cell cannot support timing conclusions. This screen does not create late-workspace pressure, force allocation failure, establish numerical quality, or qualify sustained service.

## Reproduction and artifacts

`matrix.json` records the seed, order, actual reported resources, reservation events and per-cell result. Each cell directory retains its config, capability response, request data, engine log, parsed owner summary and supervisor telemetry. `workloads.json` retains the exact workload and tokenizer file hashes. Model files remain under `~/models` and are not included. `SHA256SUMS` covers the preserved screen artifacts.
