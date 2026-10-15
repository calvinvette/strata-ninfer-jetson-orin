# Adaptive residency-table verification — Orin — 2026-10-14

The adaptive-refill diagnostic now also checks the device residency map after
it is uploaded. With opt-in `STRATA_VERIFY_ADAPT_SWAPS=1`, each completed batch
first compares incoming cache-slot bytes against their stable source blobs,
then copies the main and any stage residency table back and compares it with
`host_res`. A mismatch reports the failed check and aborts the diagnostic run.
Both checks are disabled by default.

A bounded IQ1_M Coder MTP-off request exercised the opt-in path on the current
Orin CUDA build: a 512-token prompt and 16 generated tokens with accepted-only
adaptation every four tokens. All three adaptive apply points passed. The
service verified 288 incoming expert blobs and matched the full device
residency table to `host_res` after each upload. The request completed
successfully. This verifies the checked route's bytes and uploaded ownership
map for this request; it does not explain the longer same-service
short/long/short output and persistent-state drift.

The 28-GiB supervisor recorded 14.27 GiB minimum host and admission
availability. Across 65 memory samples, cgroup `high`, `max`, `oom` and
`oom_kill` event counters stayed zero. The run took 67.7 seconds. Energy was
not request-attributed; clock observations and raw tegrastats are retained.

The current CUDA service built and completed this runtime check on Orin. The
changed generation source was also rebuilt into the HIP `strata` target on
maestro1, with its CLI help check recorded. That is x86 compile/link evidence,
not HIP device-runtime qualification. The attached single-arm driver,
service log, result, supervisor samples and backend build evidence provide the
reproduction record. No model or build product is included.
