# Q2_0 16K prefill cancellation and same-service recovery — Orin — 2026-10-13

The Q2_0 service accepted an exact 16,384-token prompt at 32K configured
context, 3,000 expert-cache slots, FP16 KV and prefill chunk 512. The client
closed the streaming request 1.02 seconds after headers; the engine had read
512 of 16,384 prompt tokens and emitted no output. The same live service then
answered a 20-token recovery request with `Hello Orin!` (five output tokens)
and remained healthy. Both harness checks passed.

The run used the Q2_0 model and PLE pack retained under `~/models/`, with
tracing and state/owner instrumentation enabled. The prompt text and exact
token IDs are in [`prompt.json`](prompt.json); launch settings, workload,
cancellation result, and owner summary are retained alongside the raw engine
log. The model shard identities are the SHA256 values recorded in the
[held-out transfer confirmation](../2026-10-13-phase3-q2-mapped-pread-16k-heldout/README.md).

The user systemd scope had `MemoryMax=28G` and `IOAccounting=yes`. The six-GiB
supervisor floor remained intact: minimum host availability was 17.10 GiB and
minimum effective scope headroom was 14.82 GiB. OOM counters remained zero.
The owner trace counted 304 allocations and 303 frees. All transient/request
owners were freed; only the expected 1,485,606,400-byte service-lifetime weight
arena remained requested-live. This is one exact 16K cancellation/recovery
cell, not a general capacity or recovery guarantee. It complements the 8K
cancellation and 32K completed-request recovery observations.
