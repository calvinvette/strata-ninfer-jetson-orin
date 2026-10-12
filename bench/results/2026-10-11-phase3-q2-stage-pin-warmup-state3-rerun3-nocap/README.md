# Q2_0 pageable/pinned staging state rerun

Date: 2026-10-11. Device: Orin AGX, CUDA 12.6, current integration candidate.
This is a three-pair correctness rerun of the traced pageable-versus-pinned
expert-stage comparison after the earlier [warmup/state follow-up](../2026-10-11-phase3-q2-stage-pin-warmup-state3/README.md)
recorded one divergent warmup and five differing persistent-state fields.
No timing inference is made from this trace-enabled run.

Each independent arm used the Q2_0 PLE pack, 256 requested expert-cache slots,
8,192 context, speculation window 2, prefill chunk 512, 172/64 separate
warmup and the exact 512/64 measured prompt. It collected token and nine-field
persistent-state hashes plus stage-owner events. The only arm change was
`STRATA_STAGE_PIN=0` (pageable) versus `1` (pinned). The old graph-probe
`LD_PRELOAD` was removed. The harness seed was `2026101210`; the resulting order
was pinned then pageable in all three pairs. Output data and arm logs are in
`experiment/`.

All three pairs passed. Warmup completion IDs matched between arms, measured
IDs matched, and all nine persistent-state fields matched. Each pair observed
the expected pageable or pinned host-stage owner, with 353,894,400 requested
bytes for each backing mode. The supervisor passed with a minimum host and
effective availability of 22,661,926,912 bytes (21.11 GiB), above the six-GiB
floor. Sampled CPU clocks ranged 729.6–2,201.6 MHz and GPU clocks 306–1,300.5
MHz; EMC clock sampling was denied. Energy was not measured, and traced timing
is not used.

An immediately preceding three-pair attempt used an extra 28-GiB experiment
cgroup cap and was safely aborted at 5.81 GiB cgroup headroom, just below the
required floor, while host `MemAvailable` was 24.95 GB. That attempt completed
pair 0 before the cap's page-cache charge tightened. It is retained at
[`../2026-10-11-phase3-q2-stage-pin-warmup-state3-rerun3/`](../2026-10-11-phase3-q2-stage-pin-warmup-state3-rerun3/)
and is not combined with these uncapped results. No OOM event occurred.

The three clean pairs show that the earlier warmup/state mismatch did not
recur under this rerun. They do not identify its cause or erase the earlier
failure, and they do not establish a performance benefit or change the default
pageable path. Broader transfer and pressure gates remain open.
