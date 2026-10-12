# Q2_0 16K prompt admission at 19 GiB — Orin — 2026-10-13

The current Q2_0 service completed an exact 16,384-token prompt plus one
output token with a 32,768-token configured context, 3,000 requested expert
slots, FP16 KV and a 19-GiB systemd `MemoryMax`. The run performed one
warm-up request and one measured request in the same server process. Both
reported 16,384 prompt tokens, one completion token (`A`), zero cached prompt
tokens and passed the API workload check.

The six-GiB supervisor passed. Minimum host availability was 18,682,822,656
bytes (17.40 GiB); minimum effective cgroup headroom was 9,329,324,032 bytes
(8.686 GiB). The scope recorded zero OOM and OOM-kill events. The two client
request durations were 94.67 and 81.79 seconds, respectively; these are
single-process descriptive samples, not a performance comparison. The system
was using dynamic clocks, and energy was not measured.

The model is the local Qwen3.8-Flash-Next GSQ-RCO Q2_0 Orin-validation
artifact (the same two GGUF shards, Q2 PLE pack and expert profile used in the
[32K admission campaign](../2026-10-12-phase3-q2-actual32k-context64k-19G/README.md)); artifacts remain under
`~/models/strata-orin-validation/`. Candidate binary SHA256 is
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.
The exact formatted-workload JSON SHA256 is
`cb49f237f67efa3fe57688c0873a7a70393829b94a85d65c1e8ed52442d3dae6`.

Trace instrumentation was disabled for this admission/timing-only run, so it
has no owner ledger or accepted-prefix fingerprints. It is a 16K request
admission point, not numerical quality, cache-capacity, recovery, physical
allocation ownership, or performance qualification. The result, exact
workload, server capabilities, cgroup/clock telemetry and supervisor record
are retained. The ignored local engine log hash is listed in
`SHA256SUMS.txt`.
