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

## Same-server recovery probe (inconclusive)

A follow-up started the API server under the memory supervisor with the same
one-shot shim. The original shim refused the workspace during server startup
warmup, before readiness; that run confirms the service reports startup failure
and the engine cleans up the partial prefill owner and cache, but cannot test a
subsequent request. A second attempt allowed the first matching allocation and
waited for readiness. The API request then succeeded, and the shim did not
refuse any allocation during that request: the 32 MiB workspace allocated at
warmup was reused. This is not evidence of injected request failure or
same-process recovery. Minimum available memory in the latter run was
8,411,717,632 bytes (7.83 GiB).

The captured attempts are in `same-process/` and
`same-process-skip-warmup/`. The latter also retains the attempted driver
script. A useful request-level injection needs a targeted hook after warmup or
a different allocation that is created on the request path; this probe did not
establish one.
