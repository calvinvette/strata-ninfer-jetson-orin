# Short output-limit state follow-up

A supervised 2026-10-09 Orin run compared the same candidate in spec1 and spec4
modes at an 8-token output limit. Both arms emitted identical token IDs and ended
at state length 1469; spec4 offered 9 drafts and accepted 7. The captured GDN,
PLE, tail, completed pooled rows, dead key, KV prefix and PLE history matched.
The `pooled_full` fingerprint, which includes the in-progress spare indexer row,
did not match. MTP and stale-KV fingerprints also differed; those are proposal
or beyond-prefix data and are not in the harness's authoritative state field
set. The mismatch in `pooled_full` remains an unresolved accepted-prefix state
failure and needs source-level investigation plus a controlled continuation test.
It is not explained away by identical output text.

The supervisor exited on the harness parity failure, not memory pressure.
Minimum sampled physical availability was 9,051,082,752 bytes (8.43 GiB), above
the 6 GiB floor. Both model processes completed. The explicit 5,000-slot cache
configuration does not use the auto-cache reservation path, so this run contains
no planned-reservation events. Tracing was opt-in. Energy was not measured.

`results.json`, both engine logs, the supervisor report, raw tegrastats and
memory samples preserve the result. `config.json` records the runtime arguments;
model files remain in `~/models` and are not included. Identities and checksums
are in `identities.json` and `SHA256SUMS`.

## Session-trace repeat

A later auto-cache run with the session-allocation trace enabled again emitted
the same eight token IDs at state length 1469, with spec4 offering 9 and
accepting 7 drafts. This time exact fingerprints differed for GDN, tail,
completed pooled rows, the spare pooled row and KV; PLE, dead-key and PLE
history matched. Treat the full field set as unresolved exact-state parity, not
as a stable one-field-only discrepancy. The result and both engine logs are in
`session-trace/`. Minimum sampled availability was 8,062,767,104 bytes
(7.51 GiB), above the supervisor floor; exit code 1 reflects parity only.

The new owner trace reports a 235,033,088-byte primary session backing
allocation. It remains live at process end because the serving subprocess is
terminated as part of each isolated arm; this is not called a leak. Each arm
records 31 allocations and 30 explicit frees, with the session arena accounting
for the remaining live allocation. Other session allocations and physical
backing remain outside this selected trace.
