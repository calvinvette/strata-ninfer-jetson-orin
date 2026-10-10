# CUDA async-pool transfer screen — Orin — 2026-10-10

This isolated diagnostic compares four sequential 64 MiB ownership paths on
Orin SM87: persistent `cudaMalloc` plus pinned H2D copy, mapped pinned host
reads, sequential managed-memory reads, and a transient `cudaMallocAsync` pool
allocation with H2D copy, checksum kernel and `cudaFreeAsync` each iteration.
CPU buffer initialization is outside the timed interval. Each path runs three
warmups and ten timed iterations with an exact checksum. CUDA pool telemetry
reported 64 MiB high-water used and reserved, and zero current used bytes after
all async frees. The device reports `concurrentManagedAccess=0`.

| Path | Median ms | Min–max ms | Checksum |
| --- | ---: | ---: | --- |
| Persistent `cudaMalloc` + pinned copy | 13.163 | 12.966–13.210 | Pass |
| Mapped pinned host | 5.197 | 5.143–5.465 | Pass |
| Managed sequential ownership | 5.692 | 5.527–5.966 | Pass |
| Transient async-pool alloc/copy/kernel/free | 14.926 | 14.744–14.958 | Pass |

The pool path is slower than the persistent-copy baseline in this one screen.
It also includes allocation and free work in every timed iteration, unlike the
persistent baseline, so it only screens a short-lived transient buffer class.
It does not justify changing Strata's allocation path. The fixed mode order,
single run, dynamic clocks and missing energy measurement make the timings
screening evidence only. No product or end-to-end performance conclusion is
claimed.

The compile command was `/usr/local/cuda-12/bin/nvcc -std=c++17 -O2
-arch=sm_87 memory_paths_async.cu`. The run used the six-GiB supervisor and
retained at least 24.45 GiB host availability. `run-final/` contains the
command, raw output, memory samples and tegrastats. The harness source is
`memory_paths_async.cu`.
