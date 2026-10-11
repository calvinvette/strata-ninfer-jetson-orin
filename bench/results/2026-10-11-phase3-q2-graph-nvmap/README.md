# Q2_0 verifier-graph NVMap follow-up — Orin — 2026-10-11

This experiment repeats the calibrated process-owner trace with the Q2_0 model,
which uses native spec2 verification without MTP. It complements the IQ1_M
startup trace in the parent Phase 3 report with a distinct quantization and
verifier-window configuration.

Each run used the candidate engine at SHA256
`3e1e003c2097d58591db30b60412acbd8798e5ab39ce857f1e3e2c0ebd241a5b`, Q2_0
artifacts identified in `artifact-identities.json`, a 256-slot expert cache,
4K context, 512-token prefill chunk and the ordinary six-GiB host availability
floor. The real-model protocol harness passed all seven HTTP, streaming,
cancellation and recovery scenarios in every process.

| Run | Engine PID | Successful runtime graph calls | Stable NVMap before (B) | After fourth call (B) | Net interval increase (B) | Minimum host availability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 00 | 2710316 | 4 | 5,237,268,480 | 5,309,693,952 | 72,425,472 | 21.30 GiB |
| 01 | 2736421 | 4 | 5,237,268,480 | 5,309,693,952 | 72,425,472 | 21.32 GiB |
| 02 | 2762490 | 4 | 5,237,268,480 | 5,309,693,952 | 72,425,472 | 21.17 GiB |

The net increase is exactly 69.09375 MiB in all three processes. The counter is
the root-readable NVMap IOVMM client table, sampled every 0.1 seconds and
calibrated against a live 512 MiB CUDA allocation in the [prior calibration](../2026-10-11-phase3-graph-nvmap-calibration/README.md).

The CUDA runtime interposer reports four successful `cudaGraphInstantiate`
calls in each process, but the then-current integration owner trace reports
only three `verifier` window-graph events. Source inspection found that verifier
commit-state graph instantiation was not separately reported. This follow-up
adds a `verifier-commit-graph` event. The native CUDA build, maestro1 HIP
build, five focused CTests and 75 integration-tooling unit tests passed. A
post-patch Q2_0 service check observed four owner events for four successful
runtime calls. The recorded memory samples are from the prior binary, before
this diagnostic-only change. The changed SYCL verifier translation unit compiles on maestro1; the full engine link remains pending as recorded in the [backend check](../2026-10-11-phase3-commit-graph-trace-tests/README.md).

The stable pre-first-call sample and post-fourth-call sample bracket initial
verifier graph capture through the first request's fourth successful
instantiation. This repeatable change includes adjacent synchronous device
allocations during that interval. It is not an isolated graph executable size,
a graph-disabled differential, or a universal graph cost. No timing or quality
claim is made. The initial launch with the IQ1_M pack was rejected for a model
geometry mismatch before serving and is retained separately under
`config-rejected/`; it is excluded from these measurements.

The `repeat-00/`, `repeat-01/` and `repeat-02/` folders retain service logs,
protocol results, supervisor telemetry, and the respective owner-counter
samples. Model files remain under `~/models/` and are not copied into Git.
Phase 3 remains open for other graph paths, memory owners, transfer and
admission gates.
