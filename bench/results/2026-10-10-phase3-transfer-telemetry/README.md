# Phase 3 request-local file-tier transfer telemetry

This checkpoint adds opt-in request-local file-tier counters to the Orin
generation log and records a mapped-versus-pread screening run. It does not
change the default transfer path. The run used the exact 512-token prompt and
64 generated-token request, with three randomized mapped/pread pairs, prefetch
staging disabled, and the Phase 3 six-GiB physical-memory supervisor.

The three pairs generated identical token IDs and matched all nine checked
persistent-state fields. Median prompt time was 22,038.5 ms mapped and 21,836.1
ms pread; median decode time was 4,623.5 ms mapped and 5,850.6 ms pread. This
small screen does not establish a transfer-path performance win. Minimum
`MemAvailable` was 8.33 GiB. `/proc/self/io` read bytes were unavailable on this
Orin kernel; major-fault counters were available but do not measure bytes read
from storage.

Both arms handed out 40,996.1 MB of expert reads per request. The mapped arm
measured 33,428–33,729 MB resident in the page cache at handout and 7,267–7,568
MB not resident. In the pread/fill-cache arm, three requests measured 2,216.0,
2,245.1 and 2,298.3 MB of actual `pread` traffic. Summed worker time was
2,515.6, 2,635.7 and 2,723.0 ms; this is cumulative time across workers, not
wall-clock transfer time. Decode waited zero milliseconds in zero fetches,
consistent with the prefetch path staying ahead in these requests. The `used`
and `unused` stage-buffer counters are zero because staging was disabled.
Page-cache residency is intentionally omitted for the pread/fill-cache mode:
that path does not collect the mapped-path mincore samples, so reporting zero
would be incorrect.

The initial three-pair run used binary SHA-256
`1a4825bb2b68504302ac6712c9425b52ac36f5464fce27f1c23da649cdc8cde2`. It
predated the final print-only correction that suppresses unavailable pread
cache-residency fields. The final source and rebuilt Orin binary hashes are
recorded in `orin-final-output-check/` after a one-pair supervised output check.
That final check also matched output and persistent state, reached 8.37 GiB
minimum `MemAvailable`, and confirmed that mapped logs include cache residency
while pread logs omit it. The final binary passed `--help`; its SHA-256 is
`e83366f3f83295d4e13394367f1101da64160361b1b235857f42462b637b7680`. The
generated evidence remains scoped to the exact binary named in each result
file.

The engine now reports file-tier bytes and pread worker time even when
`/proc/self/io` is unavailable. It seeds counter deltas after startup and cache
population, so the first request is comparable to later requests. The harness
reads these diagnostics from the engine log rather than intercepting the Python
queue, and records host block-device counters separately; those counters cover
the whole device and include unrelated reads and kernel readahead. A same-day
three-pair NVMe-partition screen is documented in
[`phase3-mapped-pread-screen`](../2026-10-10-phase3-mapped-pread-screen/README.md).

Validation: the 55 Python integration tests passed; the harness passed
`py_compile`; the candidate CUDA target built on Orin and passed `--help`; the
modified native source also built on maestro1 with HIP and its binary passed
`--help`. The HIP result is compile evidence only, not runtime qualification.
No SYCL files changed. Energy, isolated engine storage bytes, copy latency, and
GPU/EMC clocks remain unmeasured. Keep the broader Phase 3 transfer gate open.
