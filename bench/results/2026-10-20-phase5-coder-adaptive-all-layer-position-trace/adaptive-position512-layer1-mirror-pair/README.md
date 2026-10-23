# Layer-1 arithmetic mirror at verifier position 512 — Orin — 2026-10-20

This randomized same-service delayed/adaptive pair used the pinned Coder IQ1_M model, revision `5348543e0147355ac9cbcb031184a3546350988e`, and current candidate binary SHA256 `6e4b89f7d0979dd0d16eb000c238aa837d5c990dbe54033dada9a479a93fcd38`. It enabled the opt-in CPU Q8_1 arithmetic mirror only for `iq2_s/q2_0@layer=1`. The requests were a 512-token short prompt, a 2,048-token long prompt, and same-service 512-token recovery, with 12 generated tokens each.

Adaptive and delayed arms returned the same token IDs for all three requests. Delayed-control terminal state fingerprints were exact; adaptive terminal fingerprints changed in `gdn`, `tail`, `pooled`, `pooled_full`, and `kv`. At selected position 512, layer-1 verifier router inputs, IDs, weights, expert contributions and combined MoE outputs match between adaptive initial/recovery requests; layer-2 GDN verifier fields and pre/post state also match. The accepted layer-2 recurrent matrix and convolution history at position 512 are bit-identical between arms and across initial/recovery.

The all-layer dispatch capture at position 512 reports owner placement first changed at layer 1, activation first changed at layer 3, and expert IDs first changed at layer 4. The per-GDN service-hash comparator finds the first adaptive initial/recovery difference at endpoint 511, beginning at GDN ordinal 3 (model layer 4) and affecting 33/36 GDN hashes. Delayed control is exact at captured accepted endpoints through 522. Thus matching layer-1 arithmetic and layer-2 state does not resolve the later adaptive state divergence; the next raw-state target is model layer 4 at endpoint 511. Hash evidence localizes a state difference but does not quantify it or identify its cause.

Both supervised runs passed. Minimum host/admission availability was 14.14 GiB for delayed control and 14.20 GiB for adaptive, with zero sampled cgroup `high`, `max`, `oom`, or `oom_kill` events. This is correctness evidence for one model/workload, not a performance result or migration qualification.

The delayed-control runner summary originally mislabeled its raw GDN state capture as position 511. The position-512 header and two-record initial/recovery structure are authoritative; the summary now reflects that correction. No capture bytes changed.

Reproduce from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261044 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1' \
  --capture-moe-positions 512 \
  --capture-verify-moe-layer 1 --verify-moe-positions 512 \
  --capture-verify-gdn-layer 2 --verify-gdn-positions 512 \
  --capture-verify-gdn-state-layer 2 --gdn-state-positions 512 \
  --capture-gdn-commit-state-layer 2 --gdn-commit-state-positions 512 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-layer1-mirror-pair
```

Raw captures, supervisor data, service logs, per-GDN comparisons and verifier-parts comparisons are retained beside this report. The multi-position follow-up is reported separately in [the prefix trace](../adaptive-position512-layer1-mirror-prefix-trace/README.md).
