# Isolated pinned H2D copy timing — Orin — 2026-10-10

This CUDA-only diagnostic measures one existing ownership path: a 64 MiB
`cudaMemcpyAsync` from a pinned host allocation to a persistent device
allocation. CUDA events bracket only the copy on a nonblocking stream. Each
process performs five warmups and 25 measured copies, then checks the copied
buffer with a GPU checksum. Seven independent, six-GiB-supervised processes
passed all checks. This is an operator transfer measurement, not an expert
cache comparison or an end-to-end result.

| Process | Median ms | Min–max ms | Effective decimal GB/s |
| --- | ---: | ---: | ---: |
| 1 | 2.909120 | 2.908608–7.750816 | 23.068 |
| 2 | 2.909376 | 1.837920–2.934656 | 23.066 |
| 3 | 2.909408 | 1.830400–2.909728 | 23.066 |
| 4 | 2.908960 | 2.215680–7.750720 | 23.070 |
| 5 | 2.908864 | 2.908032–7.750592 | 23.070 |
| 6 | 2.909280 | 1.831392–2.913664 | 23.067 |
| 7 | 2.909600 | 2.908704–7.751936 | 23.065 |

The median of the seven process medians is 2.909280 ms (range 2.908864–
2.909600 ms), or 23.067 GB/s at 64 MiB. Several individual samples were much
slower, up to 7.75 ms; all 175 raw event samples are retained in the process
stdout files and must not be hidden by the stable process medians. The lowest
physical `MemAvailable` was 29,862,322,176 bytes (27.82 GiB), above the six-GiB
floor.

This does not compare pinned copy against mapped reads on matched data and
clocks, and it does not measure storage reads, cache-fill overlap, copy stalls
inside a request, energy, GPU frequency, or product benefit. `tegrastats`
sampled near the end of these short runs and showed 0% GR3D utilization then;
it did not provide a useful active GPU-clock sample. No clocks were changed.

The test source SHA256 is
`ff9eeb0d37ff94ab1c564d9a1d91b37d4770ae4180601424373b571f2711c474`; the linked
SM87 executable SHA256 is
`92b3970c0513eb3d1cb8f77cbce38ea7d1f4cd23096a4b959847e32d12212d41`.
Build with CUDA 12.6:

```sh
/usr/local/cuda-12.6/bin/nvcc -O2 -arch=sm_87 \
  bench/results/2026-10-10-phase3-copy-latency/pinned_h2d_copy_bench.cu \
  -o /tmp/strata-pinned-h2d-copy-bench
python3 tools/integration/run_control.py \
  --output bench/results/NEW-phase3-copy-latency/rep1/supervisor \
  --timeout 120 -- /tmp/strata-pinned-h2d-copy-bench
```

`pilot-reps/` retains the first seven-process pass made before raw per-sample
printing was added. `process-reps/` contains the seven documented runs used in
the table, including stdout, supervisor result, memory samples and tegrastats.
The compiled binary remains outside Git.
