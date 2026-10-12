# Q2_0 16K configured-context admission screen — Orin — 2026-10-11

This extends the Q2_0 cache/context admission screen with the 16,384-token
configured-context point at requested expert-cache sizes 3,000 and 5,000. Each
fresh process loaded the Q2_0 native pack, matching PLE shard and expert
profile, processed the prepared 512-token prompt, and greedily emitted one
token with `--spec 2`. Context was reserved/configured; the request did not
contain a 16K prompt. MTP weights and prompt caching were disabled. The
existing 3-GiB workspace reserve and six-GiB physical headroom remained in
force. Runs were sequential, without a paired timing design.

Both cells passed the supervisor and emitted a token. The engine admitted
exactly 3,000 slots (3.86 GiB) and 5,000 slots (6.44 GiB). Minimum host
`MemAvailable` was 19,621,257,216 bytes (18.27 GiB) and 16,996,556,800 bytes
(15.83 GiB), respectively. No cgroup OOM events were recorded. The owner trace
balanced 278 allocations/frees per process; its instrumented requested-live
peak was 6,592,312,952 bytes at 3,000 slots and 9,357,112,952 bytes at 5,000.
Those totals omit uninstrumented allocations and graph/driver-private backing;
they are not added to `MemAvailable` and do not replace the physical-memory
guard. The 16K session allocation request was 559,240,704 bytes in both runs.

This is one-token admission evidence for one model and two cache sizes. It is
not a 16K workload, quality, capacity-boundary, or performance result. Dynamic
clocks were not controlled; energy was not measured. Raw supervisor telemetry,
engine output, and exact commands are retained in each cell directory. The
model source is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` revision
`5348543e0147355ac9cbcb031184a3546350988e`; local shard hashes were not
recomputed for this extension. The Q2_0 pack and profile identity record is
linked from the [4K/8K screen](../2026-10-11-phase3-q2-admission/README.md).

This adds one configured-context point to the existing 4K/8K Q2_0 screen. It
does not close Phase 3's physical-backing, broader pressure, graph-pool, or
transfer/admission gates.
