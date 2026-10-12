# Q2_0 32K prefill cancellation and same-service recovery — Orin — 2026-10-13

The Q2_0 service accepted an exact 32,768-token prompt at 65,536-token
configured context, 3,000 expert-cache slots, FP16 KV and prefill chunk 512.
The client closed the stream 1.04 seconds after headers; the engine had read
512 prompt tokens and emitted no output. The same live service then answered a
20-token recovery request with `Hello Orin!` (five output tokens) and remained
healthy. Both harness checks passed.

The run used the Q2_0 model and PLE pack in `~/models/`, with state and owner
tracing enabled. Exact prompt text/token IDs, launch configuration, workload,
cancellation response, owner summary and engine log are retained in this
directory. Model shard SHA256 values are recorded in the [held-out transfer
confirmation](../2026-10-13-phase3-q2-mapped-pread-16k-heldout/README.md).

The user systemd scope used `MemoryMax=28G` and `IOAccounting=yes`. Minimum
host availability and effective scope headroom were both 16.38 GiB; OOM
counters stayed zero. The owner trace counted 304 allocations and 303 frees;
only the 1,485,606,400-byte service-lifetime weight arena remained
requested-live. This is one 32K cancellation/recovery cell, not a general
capacity or recovery guarantee. Together with the 8K and 16K cancellation
cells and the separate completed-32K recovery test, it adds evidence across
actual prompt lengths while leaving graph/driver physical backing open.
