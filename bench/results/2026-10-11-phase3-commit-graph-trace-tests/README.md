# Commit-graph ownership trace regression — Orin — 2026-10-11

The CUDA trace now labels verifier commit-state graph creation separately from
verifier-window graphs. The Q2_0 post-patch service check passed all seven
protocol/streaming/cancellation-recovery scenarios and observed four successful
`cudaGraphInstantiate` runtime calls alongside four integration owner events:
three `verifier` window graphs and one `verifier-commit-graph`. Minimum host
`MemAvailable` was 23,100,706,816 bytes (21.51 GiB), above the six-GiB floor.
The run validates trace coverage and service behavior; it is not a performance
or graph-memory measurement.

Five focused CTests also passed under the six-GiB supervisor:
`conversation_cache_test`, `conversation_memory_test`, `vmm_test`, `ple_parity`
(using the Q2_0 pack and PLE shard), and `expert_cache_memory_test`. Minimum
host `MemAvailable` was 30,316,105,728 bytes (28.23 GiB). The complete
integration-tooling unit suite passed 75 tests.

Backend compile evidence for this diagnostic change:

- Native CUDA: candidate `strata` target rebuilt successfully on Orin.
- HIP: full maestro1 HIP build passed with one build job; the resulting x86
  binary is compile/help evidence only.
- SYCL: the changed verifier translation unit compiled successfully with the
  configured maestro1 oneAPI toolchain. The existing Ninja rules file was
  missing; after reconfiguration, a full `strata` target would require a clean
  94-object rebuild on maestro1's 3.7 GiB host. The translation unit was built
  directly; the full SYCL engine link remains pending and must be included in
  the Phase 8 backend build matrix.

`backend-builds.json` records binary/source hashes and the precise SYCL limit.
Raw supervisor records and the post-patch protocol logs are retained alongside
this report.
