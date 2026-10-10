# Expert-stage pinned-allocation fallback — 2026-10-10

This Orin experiment injects one `cudaHostAlloc` failure in the real native
IQ1_M prompt route, then verifies the expert-stage pool falls back to pageable
host memory and tears both kinds of buffers down. The request ran with
`STRATA_STAGE_PIN=1`, `STRATA_IO_PREFETCH=1`,
`STRATA_IO_PF_STAGE=1`, and `STRATA_INTEGRATION_TRACE=1`, under the six-GiB
supervisor floor.

`fail_stage_alloc.cpp` is a test-only LD_PRELOAD shim. It forwards calls to the
real CUDA runtime except for one exact 2,662,400-byte allocation. The default
prefill staging ring makes sixteen allocations of that size first; the shim
then refuses one subsequent request. The captured stack resolves to
`FileExpertSource::claim_stage` (see `run-expert-stage/stderr.txt`), so this
failure targets the expert-stage pool rather than prefill's separate Stager.
The runtime reports `cudaHostAlloc failed for a stage buffer (out of memory) -
pageable it is` and emits one `expert-stage-pageable-host` allocation.

The supervised request passed: 511 prompt tokens were processed and one token
(ID 32) was generated. Minimum available memory was 8,139,874,304 bytes
(7.58 GiB). Owner tracing recorded one pageable stage allocation/free and five
pinned stage allocation/free pairs. The page-locked allocation failure was
cleared, subsequent pinned allocations remained available, and the request
completed. This is fallback and cleanup evidence; no performance benefit is
claimed. `owner-summary.json`, produced by `tools/integration/owner_observations.py`,
validates 10 allocation/free pairs across the observed owners and reports zero
live observed bytes at process teardown. The summary remains explicitly scoped
to instrumented sites and requested allocation sizes.
The additional `run-expert-stage/owner-accounting.json` reports concurrent
observed request peaks of 15,949,091,840 bytes for device 0 and 15,974,400
bytes for pageable/pinned host owners (`device=-1`). These are separate
per-device requested-byte totals, not complete physical-memory measurements.

`run-expert-stage/` is the targeted fault-injection result. `forced-pageable/`
is a separate successful control using the engine's existing
`STRATA_TEST_PAGEABLE=1` hook, with the same request and owner tracing. Earlier
`run/`, `run-traced/`, `run-stack/`, and `run-stage-target/` attempts are kept
as well. The first three captured an unrelated prefill Stager allocation and
its caller; `run-stage-target/` hit Prefill's required CPU-expert row allocation
instead and correctly aborted after that injected failure. The source shim
records the exact selector used for the passing targeted run.

The passing targeted command included:

```bash
/usr/bin/g++ -shared -fPIC -O2 \
  -I/usr/local/cuda-12.6/targets/aarch64-linux/include \
  bench/results/2026-10-10-phase3-stage-hostalloc-failure/fail_stage_alloc.cpp \
  -ldl -o /tmp/strata-fail-stage-hostalloc.so
LD_PRELOAD=/tmp/strata-fail-stage-hostalloc.so \
STRATA_STAGE_PIN=1 STRATA_IO_PREFETCH=1 STRATA_IO_PF_STAGE=1 \
STRATA_INTEGRATION_TRACE=1 \
python tools/integration/run_control.py \
  --output bench/results/2026-10-10-phase3-stage-hostalloc-failure/reproduction \
  build/integration/candidate/strata --pack /home/calvin/models/strata-orin-validation/pack \
  --native /home/calvin/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --expert-profile data/expert-profile-coder.bin --spec 4 --prefill 512 \
  --tokens-file build/integration/workloads/pp512-tg64.tokens \
  --max-context 4096 --max-new 1 --expert-cache auto \
  --ple-gguf /home/calvin/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf
```
