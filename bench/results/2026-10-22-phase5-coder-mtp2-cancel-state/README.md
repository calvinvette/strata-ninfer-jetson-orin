# MTP2 cancellation state parity — Orin — 2026-10-22

This current-source Orin test checked cancellation and same-service recovery
with the Coder IQ1_M artifact, MTP window 2, adaptive accepted-only updates,
8K context, and a 3,000 MiB expert cache. After five non-empty streaming
deltas, the client closed the stream. The engine had committed eight tokens
across five accepted prefixes at state lengths 48, 50, 51, 53, and 55; three
MTP drafts were accepted. Both fresh exact-length reference runs reproduced
all five token sequences and every recorded persistent-state fingerprint.
The canceled service then remained alive and returned the expected `Hello
Orin!` recovery response.

The supervised command completed in 101.20 seconds. Across 98 memory samples,
minimum available host RAM was 13.18 GiB and minimum admission availability
was 12.53 GiB, above the preserved 6 GiB floor. Cgroup `low`, `high`, `max`,
`oom`, and `oom_kill` counters remained zero. Clocks were observed dynamically;
EMC readback was denied, and energy was not attributed to requests. The run was
under a 28 GiB cgroup memory limit.

This adds state-parity evidence for one MTP2 cancellation boundary set and one
same-process recovery request. It does not bound every cancellation point,
long-chain adaptive drift, or the two-live batch-MTP mismatch; Phase 5 remains
open. Raw logs and supervisor telemetry remain local-only. The current binary
was `build/integration/candidate/strata`, SHA256
`c3b356593d55ccc76ccdf19d13edfbf290835313ab513067992ad4a256b63101`.

Reproduction used `tools/integration/mtp_cancel_state_parity.py` with the
Coder configuration from
`bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/config.json`,
changing both `--spec` and `--mtp-max-t` to `2`, and ran it under
`tools/integration/run_control.py` with `MemoryMax=28G`, one-second telemetry,
and clock sampling. The generated config and detailed outputs are retained in
the local `run/` and `supervisor/` directories but excluded from Git.
