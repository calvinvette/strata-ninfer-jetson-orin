# Q2_0 cancellation and same-service recovery at 8 seconds


Date: 2026-10-11. Device: Orin AGX, CUDA 12.6, current integration candidate.
This three-startup Phase 3 check tests client disconnect during a real Q2_0
long-prefill request followed by a short request to the same live service.

Each run used the Q2_0 PLE pack, 256 requested expert-cache slots, 8,192
context, speculation window 4, `--prefill 128`, and the same exact 2,048-token
formatted long prompt. The client closed its stream after 8 seconds. The client closed at eight seconds. The server completed its active prefill batch and then cancelled at 256 prompt tokens, before generation.
The service then returned exactly `Hello Orin!` to a new request and remained
alive. Cancellation produced zero generated tokens. All three supervisor and
recovery results passed.

The ordinary six-GiB physical/effective-availability guard ran without an
additional `MemoryMax` cap. Minimum host `MemAvailable` was 22.64 GB (21.10
GiB) or higher; the minimum by run is retained in [`analysis.json`](analysis.json).
No cgroup OOM or OOM-kill events occurred. Read-only clock samples ranged from 729.6 to 2201.6 MHz for CPU cores and 306.0 to 1300.5 MHz for GPU; EMC clock sampling was denied. Energy was not measured. Each owner trace recorded 304
allocations and 303 frees; the only requested bytes left at the end of the
request/recovery sequence were the 1,485,606,400-byte service-lifetime weight
arena, which is released when the service exits. Full token, timing, owner and
memory evidence is retained under `run-*/`.

The reproducible analyzer is [`analyze.py`](analyze.py). No clocks were
controlled and no energy claim is made. This extends the previous
[512-token-chunk cancellation check](../2026-10-11-phase3-q2-cgroup-cancel-recovery/README.md)
with later cancellation progress and recovery. The two cancellation delays are
separate experiments; they do not establish a general cancellation-latency
bound or recovery after allocation failure.
