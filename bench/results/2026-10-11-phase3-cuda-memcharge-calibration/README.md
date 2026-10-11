# CUDA allocation visibility calibration — Orin — 2026-10-11

The prior graph probe observed graph instantiation but no public Driver
allocation calls, so this test checked whether the available platform memory
gauges react to a known CUDA allocation. A small standalone program created a
CUDA context, requested 512 MiB with `cuMemAlloc`, filled it using
`cuMemsetD8`, synchronized, held it for eight seconds, then freed it. Two
supervised repetitions passed the six-GiB host `MemAvailable` floor. The
second repetition also sampled `cuMemGetInfo` before, during and after the
allocation.

The CUDA calls returned success, but none of the gauges sampled by these two
runs showed a 512 MiB change. In the second run, `cuMemGetInfo` reported total memory fixed at
32,187,883,520 bytes; free memory changed from 26,466,254,848 bytes before to
26,464,190,464 bytes while the allocation was live, then to 26,463,412,224
bytes after free. Host `MemAvailable` moved by about 2 MiB between the direct
before/during samples and drifted further after free. Across the supervised
sample window, `tegrastats` reported 5,218–5,235 MiB system RAM and the
interactive session cgroup varied by about 13 MiB; these gauges include
unrelated system activity. The first repetition likewise showed only
background-sized movement in host availability, session-cgroup usage and
`tegrastats` RAM.

This was an instrumentation-boundary result, not a measurement of the
allocation's physical backing or CUDA graph memory. These gauges, as sampled
here, did not independently attribute the known CUDA request to the process.
A later [NVMap calibration and service trace](../2026-10-11-phase3-graph-nvmap-calibration/README.md)
validated the root-readable IOVMM client table against an exact 512 MiB live
allocation and measured the graph-startup owner increment for three service
processes. The earlier readings remain useful as global pressure context but
are not per-allocation measures.

The source is `cuda_memcharge_calibration.cpp`; no binary is stored in Git.
Both supervisor outputs, memory samples and tegrastats logs are retained here.
Rebuild and run on Orin with:

```sh
g++ -O2 -I/usr/local/cuda-12.6/targets/aarch64-linux/include \
  bench/results/2026-10-11-phase3-cuda-memcharge-calibration/cuda_memcharge_calibration.cpp \
  -L/usr/local/cuda-12.6/targets/aarch64-linux/lib \
  -Wl,-rpath,/usr/local/cuda-12.6/targets/aarch64-linux/lib \
  -lcuda -pthread -o /tmp/strata_cuda_memcharge_calibration
python tools/integration/run_control.py \
  --output bench/results/2026-10-11-phase3-cuda-memcharge-calibration/supervisor \
  --timeout 90 --interval 0.25 -- /tmp/strata_cuda_memcharge_calibration
```
