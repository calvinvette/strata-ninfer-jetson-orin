# Q2_0 stage backing: warmup-separated timing confirmation

This is a seven-pair, same-day comparison of pageable and pinned host backing
for the Q2_0 expert staging buffers on the Orin. It follows the earlier
[three-pair traced correctness screen](../2026-10-11-phase3-q2-stage-pin-screen/README.md),
which matched token IDs, all nine persistent-state fields, cache counters and
the expected owner for each mode. Both modes requested 353,894,400 bytes of
stage buffers in that screen.

## Result

All seven independently supervised process blocks completed. Every measured
request generated the same 64 token IDs within its pair. Each arm first ran the
same separately formatted 172-token, 64-output warmup, followed by the measured
512-token, 64-output prompt. Five pairs produced the same warmup output hash in
both arms; two had different warmup output hashes, although both arms completed
64 warmup tokens and all seven measured output pairs matched. This is retained
as a warmup reproducibility limitation.

The paired pinned-minus-pageable request-latency median was **+0.58%** (pinned
slower), with a whole-pair percentile-bootstrap 95% interval of **−2.01% to
+10.36%**. Prompt latency was +3.28% (interval +0.30% to +14.00%); decode was
+1.02% (−3.86% to +2.77%). Positive values mean pinned took longer. With seven
blocks these bootstrap intervals are coarse and should be read as screening
uncertainty, not a service-tail guarantee. The request interval spans zero.
More importantly, the warmup hashes differ in two pairs, and the separate
traced follow-up found a persistent-state mismatch in one of three pairs when
the warmup output differed. The timings are therefore diagnostic only: they do
not qualify a product-level effect or support a default change.

Descriptive per-arm medians were 20.940 s pinned and 20.105 s pageable for the
measured request; prompt medians were 8.749 s and 8.273 s, and decode medians
were 12.113 s and 11.832 s. These marginal medians are not the paired effect
estimator. One pageable decode took 32.582 s versus 11.438 s for its paired
pinned request; the resulting −51.34% paired request delta is retained as an
observed outlier, not removed.

The minimum sampled physical `MemAvailable` was 22,735,892,480 bytes (21.18
GiB). Minimum headroom within the 28-GiB per-block cgroup was 20,058,865,664
bytes (18.68 GiB). No OOM or OOM-kill event was observed. These are physical
host and process-cgroup observations on one Orin, not additive CUDA and host
memory capacities. Dynamic clocks were observed in raw tegrastats; there was no
clock lock or energy attribution.

## Reproduction and artifacts

The measured binary SHA256 was
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`; the
checkout was `11f68d79f05187b6bb9bdd645ca06538f471a4ce`. Model, PLE shard,
expert pack, profile and tokenizer identities are recorded in
[`artifact-identities.json`](../2026-10-11-phase3-q2-graph-nvmap/artifact-identities.json);
the files remain under `~/models/` and are not in Git. The campaign config hash
is in `campaign.json`.

Each block used `systemd-run --user --scope -p MemoryMax=28G` and
`tools/integration/run_control.py` with the six-GiB effective-availability
floor. `run_campaign.py` ran seven randomized arm orders with fixed seeds. The
timing-only harness removed Strata tracing variables and `LD_PRELOAD` from
each engine process. No `GRAPH_DRIVER_MEM` events appear in these timing logs.
`analyze.py` reproduces per-arm medians and the 200,000-resample paired
bootstrap in `summary.json`. Raw request logs, supervisor samples, OOM
counters, and tegrastats are retained in each `pair-*` directory.

The warmup-separated traced follow-up at
[`q2-stage-pin-warmup-state3`](../2026-10-11-phase3-q2-stage-pin-warmup-state3/README.md)
found 2/3 pairs with matching warmup, measured output and persistent state. In
the remaining pair the 64-token warmup outputs differed, measured output IDs
still matched, but GDN, tail, pooled, full-pooled and KV fingerprints differed.
The harness now rejects a warmup-completion mismatch explicitly. This is an
unresolved correctness limitation for warmup-assisted comparisons.

The earlier directory
[`q2-stage-pin-confirm7`](../2026-10-11-phase3-q2-stage-pin-confirm7/README.md)
is retained as an instrumented diagnostic because its process inherited the
graph-driver preload probe. Its timing is excluded from this conclusion.

This is a same-model, 8K-reservation, 256-slot-cache, spec2, 512/64 workload
measurement. It does not qualify other models, contexts, cache sizes, devices,
or stage policies. Phase 3 remains open for the broader ownership, graph,
admission and transfer gates.
