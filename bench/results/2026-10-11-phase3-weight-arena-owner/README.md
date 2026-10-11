# Main WeightTable dense-arena owner check

## Result

The opt-in integration owner trace now records the main CUDA dense `WeightTable`
backing allocation in `src/program/generate.cpp`, with a matching free event only
after `cudaFree` succeeds. The trace-disabled path does not call `cudaGetDevice`
or emit owner events. Both modes completed the same Q2_0 one-token request and
returned output token ID 32.

The traced request recorded 278 allocation and 278 free events. The dense arena
was one 1,485,606,400-byte requested allocation, and the identity-based ledger
ended at zero live requested bytes on both host and device. Its peak concurrent
requested bytes were 5,913,564,928 on device 0 and 354,492,280 on host (-1).
These are observed requested allocations, not the full physical GPU ledger;
views, CUDA graph pools, driver allocations and other uninstrumented owners are
excluded. The explicit-cache path emitted no planned reservation events.

## Workload and controls

- Host: local Orin AGX; Q2_0 native two-shard model, prepared `q2-ple-pack`, and
  expert profile under `/home/calvin/models/strata-orin-validation/`.
- Binary: CUDA candidate SHA-256
  `facca01aaf48730f0098fb67b254dd0f42cc063403b03834ed84fa41211dbb83`.
- Input: prepared 512-token prompt, speculative window 2, requested expert cache
  3,000 slots, context 4,096, mmap experts, prompt cache disabled, one greedy
  output token.
- Trace-on and trace-off supervisor runs both exited successfully. Minimum
  physical `MemAvailable` was 19,807,301,632 bytes (18.45 GiB) with tracing and
  19,856,191,488 bytes (18.49 GiB) without tracing, both above the six-GiB
  floor. The runs are control checks, not timing samples.
- Trace-on logged one `weight-arena` allocation and its matching free using
  allocation identity `9008214016`; the trace-off stderr contains no owner trace.
- The `owner_observations.py` unit tests passed. No CUDA clocks or energy result
  are claimed.
- The artifact-aware `ple_parity` CTest passed 1/1 under the six-GiB supervisor
  in 3.16 seconds; minimum physical availability was 24.39 GiB. Its raw output
  and supervisor samples are in `ple-parity/`.
- The changed shared `generate.cpp` compiled and linked in the existing maestro1
  HIP `strata` build (`gfx1100`). The resulting x86 HIP binary SHA-256 was
  `fddaea1c7c63738a79e93c664afebe101f94ffcfea0d8871646d8b99906a34e9`.
  This is compile evidence only. The SYCL route uses its separate
  `sycl/src/program/generate.cpp`, which this change does not touch.

Raw supervisor records are in `supervisor/` and `trace-off-supervisor/`; the
parsed owner ledger is `owner-summary.json`. The runtime trace is opt-in and
reports requested payload bytes only. This check covers one main-route model
configuration; the split `arena_s` route and early process exits still need
separate evidence. It does not close Phase 3 graph-pool attribution, broad
memory-pressure, or transfer-measurement gates.
