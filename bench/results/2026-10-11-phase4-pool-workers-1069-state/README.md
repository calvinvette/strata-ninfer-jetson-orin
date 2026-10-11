# Held-out accepted-prefix state check across CPU worker counts — Orin — 2026-10-11

This trace-enabled three-block check compared 1, 4 and 8 workers on the
1,069-token prompt with eight generated tokens. It used the IQ1_M Coder model,
Q2_0 MTP runtime, fixed requested 3,000-slot expert cache, 3,903 actual slots,
and CPU prefill sharing disabled. All nine API cells passed. Output hashes,
end-of-request persistent-state fingerprints, and full accepted-prefix traces
matched across worker counts. Each measured request emitted eight tokens and
its accepted-prefix trace covered all five verifier commits.

This extends the no-trace output/cache comparison for the held-out prompt with
direct committed-state evidence. Minimum host `MemAvailable` was
14,335,135,744 bytes (13.35 GiB), above the six-GiB floor. The run is
correctness-only: state hashing synchronizes the GPU and invalidates its timing
medians as worker-performance evidence.

The same order appears in the separate no-trace screen, where 8 workers were
fastest in all blocks. That timing result is limited to three process blocks,
one prompt length, one cache size and CPU-sharing-disabled execution; no
default or broad worker recommendation follows. Energy and GPU/EMC clocks were
not measured.

The engine SHA256 was
`3ed52e6e0f845415b8fb2f2c15577f4b90efe49be72e2866d0dc961dbb0c95b0`.
Base config, exact workload, per-process accepted-prefix traces, engine logs
and supervisor telemetry are retained under this directory. No model or build
products are included.
