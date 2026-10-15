# Adaptive residency route-change capture — Orin — 2026-10-14/15

This Phase 5 diagnostic tests whether an adaptive cache transition changes
expert arithmetic even when the expert IDs and dispatch input are unchanged.
It extends the bounded opt-in MoE capture with a selected-layer stream-row
offset, so a later verifier window can be sampled without writing earlier
activations. The default capture limit remains small; this run captured 66
layer-0 rows across three requests.

Two fresh MTP-off IQ1_M Coder services each ran the accepted-only
short→long→short sequence: 512, 2,048 and 512 prompt tokens, 16 output tokens
per request, a 3,903-slot cache and adaptation cadence four. For each request,
the two services emitted identical token IDs and matched all nine retained
persistent-state fields. Within each service, the recovery short answer
differed from the initial short answer at 14 of 16 token positions, and seven
state fingerprints differed. The run used the same exact tokenized prompts in
both services; token hashes are in `run/results.json`.

The first and recovery requests each yielded 22 layer-0 verifier rows. In the
first seven aligned rows, every activation vector and all ten routed expert
IDs matched exactly, while 18 of 70 ownership assignments changed from CPU to
the primary VRAM cache. One was expert 119 in row 0. The following 15 aligned
rows had different activations and expert IDs, consistent with the two
execution paths diverging after those early route changes. A separate
`native_expert_parity` check ran expert 119 on that exact captured activation:
CPU and GPU outputs had 1.61% relative L1 difference, and all 7,680 output
words differed bitwise. Relative L1 against the independent floating-point
reference was 1.47% for CPU and 1.16% for GPU. The result supports
route-dependent arithmetic as a contributor to the recovery drift; it does
not establish that one expert or the sampled layer accounts for the entire
persistent-state change.

The first service's selected-layer cursor yielded all 66 rows, so the complete
initial/long/recovery comparison is retained in `start-0.jsonl`. The second
replay was configured with a stream-row start beyond its observed row count and
therefore emitted no second capture file; its outputs and state provide the
independent replay check. A separate positive-offset smoke verified that the
selector records requested rows 4 and 5.

The same run passed the already-enabled swap guards at every adaptive apply
point: incoming bytes matched their stable source blobs, and the uploaded
residency table matched `host_res`. This distinguishes numerical route
differences from corrupt refills or stale residency ownership in the tested
single-GPU path.

The main 28-GiB supervisor run took 406.6 seconds. Minimum host availability
was 14.24 GiB and minimum admission availability was 11.91 GiB. Across 385
samples, cgroup `high`, `max`, `oom` and `oom_kill` counters stayed zero. No
clock control was used, and energy was not request-attributed. Activation
capture and parity-trace timings are diagnostic evidence, not performance
measurements.

The row-offset smoke check passed separately: layer 0 capture starting at
stream row 4 recorded exactly rows 4 and 5 from a 512-token/16-output request.
Its minimum host and admission availability was 14.19 GiB, with no cgroup
pressure or OOM events. Three earlier offset-harness attempts are retained in
`offset-supervisor*`; their failures were driver/setup issues (stale state-log
input, a missing environment setting, and an argument-handling error). The
corrected offset smoke and the two full sequence sessions passed their
workload checks.

The model shards remained under `~/models/strata-orin-validation/IQ1_M/` and
their SHA256 digests are in `models.sha256`. The prepared pack remains under
`~/models/strata-orin-validation/pack/`; source and layout metadata digests
are in `pack-metadata.sha256`. `binaries.sha256` identifies the current Orin
CUDA service and parity utility. The 2,560-value parity activation is retained
as `route-example-activation.f32`, with its source dispatch in the JSONL trace.

The Orin CUDA service built and completed these runtime checks. maestro1 rebuilt
and linked the changed HIP service and its `--help` command passed; this is
x86_64 compile/CLI evidence only. The SYCL backend has separate
`sycl/src/core/expert_source.cpp` and `sycl/src/program/generate.cpp` sources;
the shared source changed here is outside that build path, and the existing
SYCL target reported no work. No SYCL device-runtime claim is made.

Reproduce the paired same-service capture and offset smoke from the repository
root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/route-capture-supervisor --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase5-current-source-route-change-capture/capture_same_service_routes.py \
  --output /tmp/route-capture-run --captures 128 --recovery-start-row 2592

build/integration/candidate/native_expert_parity \
  /home/calvin/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf \
  --expert 119 --activation-f32 \
  bench/results/2026-10-14-phase5-current-source-route-change-capture/route-example-activation.f32 0
```

The complete capture, request/state results, supervisor telemetry, independent
parity output, source and model hashes, backend build logs, and corrected offset
smoke are retained here. Adaptive residency remains unqualified for this
recovery-stability case; Phase 5 stays open.
