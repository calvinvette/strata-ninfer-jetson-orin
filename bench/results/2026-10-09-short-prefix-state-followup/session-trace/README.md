# Session allocation trace repeat

This is the supervised auto-cache 8-token spec1/spec4 repeat using the native
candidate binary and source hashes in `identities.json`. The run returned 1 on
exact state mismatch, not on memory pressure; the supervisor retained its 6 GiB
floor. Both arms emitted the same eight IDs and ended at L=1469. Spec4 accepted
7 of 9 drafts. State hashes differed for GDN, tail, pooled rows, pooled spare
row and KV; PLE, dead-key and PLE history matched.

The primary session backing request was 235,033,088 bytes. It remained live in
the trace when the isolated server subprocess ended. Parser output labels it as
live-at-end, not as a leak. Each arm had 31 observed allocations, 30 observed
frees, and 30/30 of those explicit frees matched. This is partial owner coverage;
stage/batch sessions, other backings and graph-pool bytes are excluded.

Raw logs, owner summaries, supervisor report, telemetry and identities are
retained. Verify with `sha256sum -c SHA256SUMS`.
