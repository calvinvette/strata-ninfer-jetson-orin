# Late prefill-workspace allocation failure and recovery — 2026-10-10

This Orin check forces the owned prefill path (`--no-prefill-borrow`) and
refuses the exact 33,554,688-byte allocation used for the 32 MiB cuBLAS GEMM
workspace (the extra 256 bytes are the allocator guard/alignment). The
test-only `fail_workspace_malloc.cpp` shim logs its stack; it resolves to
`Alloc::take` in `Prefill::init`. The 64 MiB FP16 GEMM scratch allocation had
already succeeded, so this exercises a late partial-workspace failure after
the session, expert cache and some prefill buffers are live.

The injected run is retained at `injected-failure/`. It failed as expected
with `prefill: GEMM scratch does not fit`, before processing prompt tokens.
Minimum available memory was 9,880,702,976 bytes (9.20 GiB), above the required
6 GiB floor. Owner events show the successful prefill allocations and the
expert cache were freed. The session owner still had 235,033,088 observed bytes
at process exit; no same-process server retry was tested, so this is not a claim
that every session resource is released on this CLI error path. The request
process exited, allowing the OS/runtime to reclaim its remaining resources.

The recovery control at `recovery-control/` ran the same owned-workspace
request without injection. It completed a 511-token prompt and generated token
32 with 8,331,128,832 bytes (7.76 GiB) minimum availability. The owner summary
records 30 allocations and 30 frees across observed owners, with no observed
live prefill or expert-cache allocation. This is a new process, not proof of
same-process service recovery. Neither run is a performance comparison.
The per-run `owner-accounting.json` files report concurrent tracked
allocation-request peaks of 15,479,257,856 bytes for the injected failure and
15,868,409,344 bytes for the successful recovery control. Both logs end with
the observed 235,033,088-byte session allocation live at isolated process
termination. These requested bytes exclude untracked allocations, allocator
overhead and graph pools, and do not replace the supervisor's physical-memory
telemetry.

The shim is built and invoked as follows (the successful recovery control omits
the shim and `LD_PRELOAD`):

```bash
/usr/bin/g++ -shared -fPIC -O2 \
  -I/usr/local/cuda-12.6/targets/aarch64-linux/include \
  bench/results/2026-10-10-phase3-prefill-workspace-failure/fail_workspace_malloc.cpp \
  -ldl -o /tmp/strata-fail-prefill-ws.so
LD_PRELOAD=/tmp/strata-fail-prefill-ws.so STRATA_INTEGRATION_TRACE=1 \
python tools/integration/run_control.py \
  --output bench/results/2026-10-10-phase3-prefill-workspace-failure/reproduction \
  build/integration/candidate/strata --pack /home/calvin/models/strata-orin-validation/pack \
  --native /home/calvin/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --expert-profile data/expert-profile-coder.bin --spec 4 --prefill 512 \
  --tokens-file build/integration/workloads/pp512-tg64.tokens \
  --max-context 4096 --max-new 1 --expert-cache auto --no-prefill-borrow \
  --ple-gguf /home/calvin/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf
```

## Post-warmup request fault and service recovery

The first two API attempts are retained in `same-process/` and
`same-process-skip-warmup/`. The first refused the known 32 MiB GEMM workspace
during warmup; the second allowed warmup and then did not encounter another
matching allocation. They did not establish request-time recovery.

A marker-gated `cudaMalloc` shim now waits until after readiness, then refuses
the next allocation of at least 1 MiB during a 1,552-token formatted prefill.
Two supervised runs hit the injection at 1 MiB, returned HTTP 503 because the
engine aborted with exit code -6, restarted the engine once inside the same
Python API service, and completed a one-token recovery request. The follow-up
run's minimum physical availability was 8,377,454,592 bytes (7.80 GiB). The
service logs and per-generation owner summaries are in
`restart-check2/`; the first successful capture is in
`same-process-request-recovery/`. The first engine generation had 32 observed
allocation events and no frees before abort; OS process teardown reclaims those
allocations. The restarted generation had 32 allocations and 31 frees, with the
235,033,088-byte session arena still live because the server remained resident.
These are requested-byte observations, not complete physical ownership or graph
pool accounting. The two generations are summarized separately so the crashed
engine's allocations are not added to the restarted process peak.

This qualifies service restart and request recovery after an injected request-
path CUDA allocation failure. It does not show in-place engine recovery,
graceful cleanup of the aborted engine, or failure specifically in the GEMM
workspace allocation: the request-path shim refuses the first allocation of at
least 1 MiB, which is currently a CUDA GEMM host-buffer allocation on the traced
stack. The `restart-check-supervisor/` attempt failed before launch because its
loopback port was still unavailable; it is retained as a harness setup failure.
The successful re-run used port 18127.

Reproduction builds the shim and then runs:

```bash
g++ -shared -fPIC -O2 \
  -I/usr/local/cuda-12.6/targets/aarch64-linux/include \
  bench/results/2026-10-10-phase3-prefill-workspace-failure/fail_malloc_after_marker.cpp \
  -ldl -o /tmp/strata-fail-malloc-marker.so
python tools/integration/run_control.py \
  --output bench/results/2026-10-10-phase3-prefill-workspace-failure/restart-check2-supervisor \
  --timeout 1200 \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-10-phase3-prefill-workspace-failure/same_process_request_recovery.py \
  --config build/integration/candidate-protocol/server-config.json \
  --shim /tmp/strata-fail-malloc-marker.so \
  --output-dir bench/results/2026-10-10-phase3-prefill-workspace-failure/restart-check2 \
  --port 18127
```
