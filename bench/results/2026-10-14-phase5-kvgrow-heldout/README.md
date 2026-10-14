# Held-out 15K elastic-KV MTP state check — Orin AGX — 2026-10-13

A cache-matched MTP-off/MTP4 sequence passed on a distinct 15,003-token prompt
at 16,384 context. Each fresh engine handled `short-512 → long-15003 →
short-512-recovery` with elastic KV enabled. This is one held-out correctness
pair on the local IQ1_M artifact, not a Q2_0 result or a speed qualification.

| Arm | Output and final state | Common accepted-prefix boundaries | KV lifecycle |
| --- | --- | ---: | --- |
| MTP off | Exact match with MTP4 on all three requests | 4 short, 3 long, 4 recovery | Captured before growth; grew 2,048 → 16,384 cells; trimmed to 2,048 |
| MTP4 | Exact match with MTP off on all three requests | 4 short, 3 long, 4 recovery | Two verifier graphs captured before growth; grew 2,048 → 16,384 cells; trimmed to 2,048 |

All shared accepted-prefix states matched across MTP settings, including the
15K prompt. Within each arm, the short recovery output and state exactly
matched its initial short request. At 15K, MTP4 offered/accepted 6/6 drafts;
on each short request it offered/accepted 9/6. Draft counts are diagnostic and
not a performance result. The outputs were capped at eight generated tokens,
so this test makes no task-quality claim.

Both arms used a 3,793-slot expert-cache floor during growth (`--expert-cache
2993`, `STRATA_KV_GROW_FLOOR=3793`), the same IQ1_M artifacts, 32-token prefill
chunks, prompt cache disabled, and `--adapt-every 100000`. The long prompt is
SHA256 `1f61b868996bddf9b30dfd921d62f3d793f8cfc61e7bed3eed3a0b118d04447f`
over its token-ID JSON. The serving binary SHA256 is
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`.

The run completed in 2,025.7 seconds. A separate `systemd-run --user --scope`
limited the process to 28 GiB and enforced the six-GiB host/effective floor.
Minimum host/effective availability was 13.42 GiB; cgroup `high`, `max`,
`oom`, and `oom_kill` counters remained zero. Clocks were sampled read-only;
energy was not process-attributed. No clock or service controls were changed.
Raw traces, supervisor telemetry, commands and configurations are retained in
`attempt-04/`.

Three excluded attempts are retained for audit. Attempt 1 stopped at prompt
construction because the chosen base workload was already too long; the engine
never started. Attempt 2 exposed a stale harness expectation for one standalone
state-hash line per request. Attempt 3 completed the 15K engine request but the
shared trace reader merged adjacent requests when that standalone delimiter was
absent. The local harness now separates groups by the persistent-state
position discontinuity and validates the published IDs against each group; the
successful fourth attempt repeats the entire sequence with that correction.
These harness failures were not engine failures.

This extends the cache-matched 9K diagnosis to one separate longer prompt while
keeping the same cache floor. It does not establish a general elastic-KV × MTP
contract, qualify other cache floors, or measure whether MTP improves serving.
Defaults remain unchanged.
