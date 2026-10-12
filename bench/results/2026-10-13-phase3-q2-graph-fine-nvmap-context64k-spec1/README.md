# Q2_0 spec1 graph-control compatibility check — Orin — 2026-10-13

The spec1 attempt is unsupported on the native Q2_0 serving route. The engine
exited before readiness because that route requires speculation T >= 2 with
native shard and prefill options. No request or graph was executed. The
supervised command returned 1 after 4.25 seconds; minimum host/effective
availability was 24.43 GiB, above the six-GiB floor, and no OOM event occurred.
This records a route constraint, not a performance failure or a reason to
weaken validation.

The attempted server configuration, refusal logs and supervisor record are
retained. The corresponding spec2/spec3/spec4 measurements remain separate;
there is no spec1 graph result. Engine logs are ignored by Git and their hash
is recorded in ENGINE_LOG_SHA256.txt. The manifest verifies committed artifacts.
