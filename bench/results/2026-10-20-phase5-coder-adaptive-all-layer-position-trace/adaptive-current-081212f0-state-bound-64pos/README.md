# Raw accepted-state follow-up at the first token-drift region — Orin — 2026-10-22

A randomized, supervised current-source pair repeated the Coder IQ1_M
short-512 → long-2048 → short-512 sequence, with 64 generated tokens per
request, MTP2, accepted-only cap-8 adaptation versus delayed control, and
`STRATA_NATIVE_CPU_Q8_1_DOT=all`. Binary SHA256 is
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`; model
revision is `5348543e0147355ac9cbcb031184a3546350988e` with both shard hashes in
`campaign.json`. Seed: `20261044`; order: adaptive then delayed control.

This follow-up captured raw committed layer-32 GDN state at accepted endpoints
515 and 534 and cross-checked both against the corresponding service hashes.
Delayed control reproduced its initial recurrent and convolution state exactly
at both endpoints and its initial/recovery token IDs across all 64 outputs.
Adaptive recovery had already diverged from its initial raw state by endpoint
515 while its token still matched: recurrent relative L2 was `0.0016605`
(max absolute delta `0.005118`), and convolution relative L2 was `0.0073540`
(max absolute delta `0.08131`). At endpoint 534, just before the first token
mismatch at output index 23, the recurrent and convolution relative L2 deltas
had grown to `0.0255905` and `0.0252282`. All recurrent values differed at
534. Adaptive recovery differed from the initial short request at 40/64 token
IDs; delayed control differed at 0/64.

An adaptive-only supervised rerun with the same seed, model, binary and request
sequence captured the actual final committed endpoint, position 574 (the
64th generated token uses zero-based positions 511–574). It matched the service
hashes and found a recurrent relative-L2 delta of `0.524326` (max absolute
`0.420518`) and a convolution delta of `0.915769` (max absolute `10.0160`);
all values differed. The initial/recovery token IDs at this endpoint were
`264`/`1785`. This confirms substantial growth through the end of this chain.
The earlier request for position 575 was outside its generated range.

These measurements do not establish a general numerical bound: this is one
prompt sequence, one model/quantization and one cache/adaptation profile. The
underlying owner/arithmetic source is covered by the adjacent layer-11 and
layer-31 captures; this result does not test a proposed correction. Phase 5
remains open.

The accepted-prefix all-layer dispatch capture at position 511 also showed
owner changes across 23 layers while the compared activations and expert IDs
remained equal there; its full summary is in `accepted-prefix-analysis.json`.

Both 28-GiB supervisors passed. Minimum host and admission availability were
13.94 GiB (adaptive) and 14.23 GiB (delayed), above the six-GiB headroom floor;
no cgroup low/high/max/OOM/OOM-kill events were observed. The arms took 375.6
and 376.5 seconds. Clocks were sampled read-only and dynamic; energy was not
measured. Full service logs, raw arrays, requests, all-layer trace, supervisor
samples and tegrastats are retained in the local result directory beside this
note. `captured-artifacts-sha256.txt` records their hashes;
`state-delta-summary.json` contains the compact numerical comparison, including
the separately captured endpoint 574; `adaptive-cap8-end574-command.txt` records
its single-arm supervised reproduction command.

Reproduce from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261044 --sequence short-long-short --continuations 0 \
  --generated-tokens 64 --native-cpu-q8-1-dot all \
  --capture-gdn-commit-state-layer 32 --gdn-commit-state-positions 515,534 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-state-bound-64pos
```

The final-endpoint capture command is recorded in `adaptive-cap8-end574-command.txt`.
