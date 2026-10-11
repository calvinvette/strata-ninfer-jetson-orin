# Verifier mapped-host staging ownership — Orin — 2026-10-10

The verifier's `cudaHostAlloc`/HIP host-mapped staging buffers were not included
in the owner ledger, even though they consume system RAM. The opt-in trace now
records each successful mapped-host allocation and its successful release under
`verifier-mapped-host`, with device `-1`. The device pointer returned for each
mapping is an alias of that host allocation and is not added as another owner.
The optional pinned profiler buffer is recorded separately as
`verifier-pinned-host`.

The updated native ARM64 CUDA binary passed the Q2_0 512-token/one-output MTP
load/bind cell under the six-GiB supervisor. It returned token ID 32, as in the
prior MTP run; one output token still means zero MTP draft rounds. In the
ordinary verifier path, minimum host `MemAvailable` was 16,166,690,816 bytes
(15.06 GiB).

The owner parser found 282 allocations and 282 frees, with zero observed live
bytes on host and device at process exit. The verifier mapped-host owner peaked
at 495,480 requested bytes (0.473 MiB). The run includes 16 mapped-host
allocations/frees in addition to the prior 266 allocation pairs. These are
requested payload sizes; they do not establish page-rounded pinned backing,
total process ownership, or graph/driver memory.

A second run enabled `STRATA_VERIFY_TRACE=1`, which allocates the mapped
diagnostic breadcrumb ring. It passed the same request with 283 allocations
and frees balanced and zero live bytes on host and device. The mapped-host peak
was 521,352 bytes (0.497 MiB), including the diagnostic ring. This run also
confirmed the ring is freed at verifier destruction; it had not been in the
destructor's host-buffer list before this change. The [trace-on run and
accounting](../2026-10-10-phase3-verifier-trace-owner/) preserve its telemetry
and event log. Minimum host availability was 16,095,866,880 bytes (14.99 GiB).

The [supervised run](supervisor/result.json), engine trace in
`supervisor/stderr.txt`, and [parsed accounting](owner-accounting.json) are
retained here. Model and pack artifacts remain in `~/models/`.

The modified `src/core/verify.cpp` SHA256 is
`66fb43bcb0e646bda732980da27346cd2e7644709b0cdf700db490225e42e6bb`. The
native CUDA `strata` binary SHA256 is
`a9304410a0c22c2af6c2bab3a7eb4cb86c6a5fd8003a67fb45ee230f348f757e`. maestro1
rebuilt the HIP `strata` executable with one job after verifying the same
source digest; its binary digest, compiler output and pass marker are retained
under [maestro1-hip](maestro1-hip/). This change is in the CUDA/HIP source file;
SYCL uses its separate verifier implementation. No HIP GPU runtime result is
claimed.
