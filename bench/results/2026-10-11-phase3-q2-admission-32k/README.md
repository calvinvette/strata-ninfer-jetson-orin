# Q2_0 32K configured-context admission screen — Orin — 2026-10-11

This extends the Q2_0 cache/context admission screen with the 32,768-token
configured-context point at requested expert-cache sizes 3,000 and 5,000. Each
fresh process loaded the same Q2_0 native pack, PLE shard and expert profile,
processed the prepared 512-token prompt, and greedily emitted one token with
`--spec 2`. The request did not contain a 32K prompt. MTP weights and prompt
caching were disabled. The existing 3-GiB workspace reserve and six-GiB
physical headroom remained in force. Runs were sequential, without paired
timing inference.

Both cells passed the supervisor. The engine admitted exactly 3,000 slots
(3.86 GiB) and 5,000 slots (6.44 GiB). Minimum host `MemAvailable` was
19,354,329,088 bytes (18.03 GiB) and 16,470,884,352 bytes (15.34 GiB),
respectively. No cgroup OOM events were recorded. Each owner trace balanced
278 allocations/frees; instrumented requested-live peaks were 7,024,653,944
bytes at 3,000 slots and 9,789,453,944 bytes at 5,000 slots. The session
owner allocation request was 991,516,160 bytes in both runs. These traces omit
uninstrumented allocations and graph/driver-private backing; their totals are
not added to `MemAvailable` and do not replace the physical-memory guard.

This is one-token admission evidence for one model and two cache sizes. It is
not a 32K workload, quality, capacity-boundary, or performance result. Dynamic
clocks were not controlled; energy was not measured. Raw supervisor telemetry,
engine output, and exact commands are retained in each cell directory. The
model source is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` revision
`5348543e0147355ac9cbcb031184a3546350988e`; local shard hashes were not
recomputed. The Q2_0 pack and profile identity record is linked from the
[4K/8K screen](../2026-10-11-phase3-q2-admission/README.md).

Together with the [16K extension](../2026-10-11-phase3-q2-admission-16k/README.md),
this adds configured-context admission points to the existing 4K/8K screen. It
does not close Phase 3's physical-backing, broader pressure, graph-pool, or
transfer/admission gates.
