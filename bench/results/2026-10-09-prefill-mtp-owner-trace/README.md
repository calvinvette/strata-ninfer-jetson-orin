# Prefill/MTP owner diagnostic — Orin, 2026-10-09

This checkpoint extends opt-in owner observations, without changing allocation
sizes, defaults, dispatch or physical admission. No NInfer execution component
is promoted. Models remain in `~/models/`; binary/logit payloads remain in ignored
build storage. Pinned Strata is `0be090c8997b24cf5d21557ced40a1b7e93e87d3`;
NInfer reference is `b07248f2528125aeda7550055580204541f1714c`.

## Executed scope

All runs use native ARM64 Release CUDA 12.6 SM87, the same independently hashed
Coder GGUF/pack/MTP artifacts as the [paired controls](../2026-10-09-paired-api-controls/README.md).
The distributed IQ1_M filename is not the artifact's per-tensor codec inventory.
Explicit commands/configs, full engine logs and sampled physical memory are
retained per run. Dynamic clocks were unchanged. These protocol diagnostics
are not paired performance measurements; rail logs are not whole-board energy.
The supervisor retains a six GiB floor and engine reserve remains 3072 MiB.

| Cell | Actual path / scope | API checks | Observed allocate/free | Minimum MemAvailable GiB |
| --- | --- | --- | --- | --- |
| owner-counters-final-owned | prefill64, context4096, cache5000, trace on | 7 pass | 30/30 | 8.588 |
| owner-counters-final-borrowed | prefill512, context4096, cache5000, trace on | 7 pass | 4/4 | 8.737 |
| owner-counters-final-off | prefill64, context4096, cache5000, trace absent | 7 pass | no trace records | 8.629 |
| prefill-streaming-kv-trace-final | requested resident1024 at context4096; clamped fully resident | 7 pass; streaming unsupported | 30/30 | 8.481 |
| rejected-clamped-streaming-kv | actual resident0; required mode rejected before requests | unsupported / command fails as expected | no protocol campaign | 8.726 |
| actual-streaming-kv-trace | context32768 reservation, cache4000; actual resident20480 | 7 short-request checks pass | 33/33 | 9.663 |

The 4K requested-streaming cell does **not** exercise streaming: the source
minimum is 20,480 tokens (`src/core/layer.cpp`, qsa_kv_resident_min). Its name is
historical and not a qualification label. The later owned harness saves
`capabilities.json` and `--require-kv-streaming` rejects absent/zero actual
residency. The 32K run reports context32768, resident20480, fp16 KV, 5215 cache
slots/10155 MiB, native spec6 and MTP max4. Requests are short: no boundary
paging, long-context quality or 32K capacity result is claimed.

## Partial allocation observations

For the 4K owned case, observed requested peaks are verifier 77,960,704 bytes,
prefill 228,829,184 bytes and MTP state/scratch 14,177,744 bytes. Three window
graph instantiations succeed. MTP's separately reported payload is
1,061,718,712 bytes; it includes arenas and must not be added to observed bytes.
The borrowed case explicitly borrows 192 expert-cache slots (~0.37 GiB), but
its only newly observed prefill backing is the 2048-byte token buffer. Its 67
view events are not allocations; the owned case records 34 views.

The streaming reservation observes prefill 303,311,360 bytes, MTP arenas
63,317,616 bytes and verifier 78,132,736 bytes; MTP's separate payload counter
is 1,110,858,584 bytes. All observed allocations are freed in these trace-on
runs. These requested peaks exclude other sites, allocator granularity,
pinned-host backing and driver/graph-pool allocations. They are not unique
physical ownership or total process memory. Graph bytes remain unsupported.

## Numerical repeatability remains open

Two separate default-profile runs of the exact pinned binary produce different
raw four-token final-position logits: maximum absolute difference 3.095, RMS
0.560; both argmax 248046. Candidate trace-off also differs from an earlier
control. This excludes a default-profile byte-identity claim and does not by
itself implicate instrumentation.

With explicit `STRATA_PREFILL_CPU_SHARE=0`, two pinned runs and the candidate
produce byte-identical raw logits, SHA256
`728dd556a404816e105daea81011a5d13fb07fb5dadc5f8e27ada8a6491c38e5`.
These runs use no MTP, prefill1, context256 and cache5000. This is narrow
GPU-prefill route evidence, not default-profile or long-chain state parity.
The independent CPU-reference discrepancy remains: KL(reference||Strata)
1.384906, maximum absolute difference 3.730145, RMS 0.705283. Equal argmax does
not close numerical qualification. Diagnostic JSONs retain source, digest and
comparison scope; no logits or model tensors are committed.

## Build and evidence boundaries

The final-source CUDA build and real-model tests pass. The earlier verifier-only
maestro1 HIP snapshot compiles; its SYCL build is running. Expanded prefill/MTP
HIP/SYCL builds remain pending and must finish before review. maestro1 supplies
x86 compilation evidence, not Orin or other GPU performance qualification.

`prefill-mtp-trace-identities-final.json` identifies the tested runtime after the
identity-table failure-branch brace correction. The similarly named earlier
identity file is retained as pre-correction history, not final-source evidence.
The initial 40-test log predates the actual-mode gate; current harness has 41
passing tests. `source-identities.json` and SHA256SUMS identify published sources
and evidence. No accepted-prefix state parity, integrated speedup or phase
completion is claimed. See [instrumentation](../../../docs/integration/INSTRUMENTATION.md)
and [porting notes](../../../docs/integration/PORTING_NOTES.md).


The staged `build-expanded-owner-backends.sh` waits for both initial backend
passes before applying the expanded overlay. It records source/binary hashes,
touches modified sources to prevent stale-object reuse, and runs serial one-job
HIP/SYCL builds into separate logs. `backend-build-handle.json` records the
last-observed live PIDs and overlay digest, not a terminal result. Failure of the
initial build leaves that source untouched; expanded failure remains explicit.
