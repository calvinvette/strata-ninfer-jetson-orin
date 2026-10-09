# First verifier owner diagnostic, 2026-10-09

This is a fresh opt-in instrumentation change after the paired control report.
It does not promote a NInfer kernel or change inference policy. The full plan
remains active. Source hashes, source diff, binary identity, CUDA build log and
raw model runs are retained here. Models remain under `~/models/`.

`STRATA_INTEGRATION_TRACE=1` records the existing verifier's successful primary
arena allocation request and release, plus selected successful window graph
instantiations. The new header uses standard C++; the SYCL migrated owner has
matching primary arena events and a single-window finalization event. CUDA/HIP
batch graph coverage is broader than this initial SYCL graph instrumentation.

| Check | Result | Scope |
| --- | --- | --- |
| Native ARM64 Release CUDA12.6.68 SM87 build | Pass | Changed verifier compiled and engine relinked |
| Harness tests | 37 pass | Includes actual compiled C++ opt-in/silence and observation ownership failures |
| Real-model protocol, trace on | 7 pass | Streaming/cancellation/recovery; no persistent-state parity claim |
| Real-model protocol, trace off | 7 pass | No integration records emitted |
| Primary verifier arena | 77,960,704 requested bytes, one allocate / one free | Observed requested payload, not physical backing or total verifier bytes |
| Window graph instantiations | 3 | Successful instantiations, not live graph count or pool bytes |
| Sampled physical minimum, trace on / off | 8.21 / 8.60 GiB | Separate whole-process samples, not a paired memory effect |
| Existing conversation snapshot GPU test | 3901 checks pass | Synthetic byte-pattern save/restore, formats, refusal/isolation and ring reconstruction; not speculative commit parity |
| HIP / SYCL builds | Pending | Isolated maestro1 setup; no AMD/Intel GPU execution |

Both runs preserve six GiB physical headroom and the separate three GiB reserve.
They reuse the paired control settings/artifacts; tracing is explicit in the
on-run config and absent in the off-run. Source hashes identify the dirty source
overlay on `0c08fa5`; binary hashes differ from the earlier control builds.
Neither these two protocol runs nor the source change establish performance or
long-output byte identity. The earlier raw-logit discrepancy remains open.

The observation parser reports zero outstanding observed primary arena bytes
at graceful engine shutdown. Auxiliary allocations and graph pools are not
instrumented, so this cannot qualify total teardown or peak ownership.
The ordinary output path stays silent when the new environment flag is absent;
an actual compiled fixture checks absent/0/true/10 values and explicit1.

Reproduction and remaining coverage are in
[instrumentation notes](../../../docs/integration/INSTRUMENTATION.md).
All retained evidence hashes are in `SHA256SUMS.json`. Engine logs use `.txt`;
no model or compiled binary is committed.
