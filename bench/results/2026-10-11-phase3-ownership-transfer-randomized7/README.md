# Randomized 64 MiB ownership-transfer screen — Orin — 2026-10-11

This repeats the earlier four-way CUDA transfer diagnostic in seven independent
processes, with a randomized mode order per process. All modes checksum the
same 64 MiB byte sequence, with CPU initialization outside the timed interval,
three warmups and ten measured iterations per mode. A process run passed only
when each checksum matched. The SM87 executable was built from
`ownership_transfer_randomized.cu` with CUDA 12.6 and `-O2 -arch=sm_87`.

| Ownership path | Median of seven process medians (ms) | Process-median range (ms) |
| --- | ---: | ---: |
| Persistent device allocation + pinned H2D copy | 13.676 | 13.564–13.909 |
| Mapped pinned-host reads | 5.218 | 5.187–5.375 |
| Sequential managed-memory reads | 5.634 | 5.568–5.759 |
| Per-iteration `cudaMallocAsync` + H2D copy + checksum + `cudaFreeAsync` | 14.934 | 14.815–14.961 |

The paired process-median deltas (bootstrap over seven whole process blocks)
were −61.76% for mapped versus pinned-copy (95% percentile interval −62.03%
to −61.41%), −58.80% for managed versus pinned-copy (−59.01% to −57.89%),
and +9.22% for async-pool versus pinned-copy (+8.67% to +9.41%). Mapped was
−6.99% versus sequential managed (−9.43% to −6.28%). These timings include
host dispatch, synchronization and checksum readback; they are not copy-only
measurements. The device reports `concurrentManagedAccess=0`, so the managed
case is strictly CPU-write then GPU-read with a synchronized ownership handoff.
The async case includes allocation and free on every iteration, unlike the
persistent-copy case.

All seven runs passed under the six-GiB supervisor. Minimum host
`MemAvailable` ranged from 30,079,807,488 to 30,154,919,936 bytes (27.99–28.09
GiB). Read-only frequency sampling observed GPU values from 306 to 1,300.5 MHz
and CPU values from 729.6 to 2,201.6 MHz; no clocks were changed, EMC sampling
was denied, and energy was not measured. The async pool reported 64 MiB used
and reserved high-water and zero current used bytes after frees in every run.

This establishes repeatability for these isolated memory paths, not a product
buffer or request-level effect. It does not justify changing Strata's current
ownership path. Raw samples, randomized order, checksums, telemetry, and
supervisor results are retained in `process-reps/`. `rep1-launch-error/`
records an initial harness invocation that was rejected because its output
directory already existed; it launched no benchmark process and is excluded
from the seven measured blocks. The binary remains in `/tmp`.

Reproduce:

```sh
/usr/local/cuda-12.6/bin/nvcc -std=c++17 -O2 -arch=sm_87 \
  bench/results/2026-10-11-phase3-ownership-transfer-randomized7/ownership_transfer_randomized.cu \
  -o /tmp/strata-ownership-transfer-randomized
python3 tools/integration/run_control.py \
  --output bench/results/NEW/supervisor --timeout 180 --sample-clocks -- \
  /tmp/strata-ownership-transfer-randomized
```
