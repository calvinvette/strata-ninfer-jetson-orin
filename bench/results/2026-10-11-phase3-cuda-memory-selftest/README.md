# CUDA memory primitive self-test — Orin — 2026-10-11

Built the existing model-free `strata-cuda-memory-test` from
`tools/cuda_memory_selftest.cu` using CUDA 12.6.68, GNU 11.4.0, ARM64 and
SM87. It was configured in the ignored `build/integration/cuda-memory-selftest`
build tree with `STRATA_BUILD_CUDA_PROBE_ONLY=ON` and
`STRATA_CUDA_MEMORY_SELFTEST=ON`, then built with one job. Binary SHA-256:
`b217f2d8323d7245eb09510bf892c86dbe6e6b2fc372121bc35c0a15ffb2d55a`.

Under the six-GiB physical-memory supervisor, all four checks passed:

- Managed allocation with CPU write, synchronized GPU increment, and CPU read.
- Registered pinned-host mapping with a GPU increment visible to the CPU.
- 512 mapped CPU/GPU doorbell publication round trips using the platform's
  acquire/release helpers.
- CUDA VMM reserve/create/map/access, GPU increment, unmap and release using
  the device's reported 2-MiB granularity.

The test exited successfully in 1.05 seconds. Minimum host `MemAvailable` was
26,463,649,792 bytes (24.66 GiB); no cgroup memory events were recorded. Raw
supervisor memory samples, tegrastats and process output are retained here.

This is primitive-level correctness evidence only. It does not compare these
ownership modes on a model buffer, price the physical backing, measure transfer
latency or energy, or qualify the modes as replacements for Strata's current
production allocations. `concurrentManagedAccess` is not asserted; the managed
case synchronizes at the CPU/GPU ownership boundary, while the mapped doorbell
is a separate pinned-host mechanism.
