# Layer-1 arithmetic mirror, four-position verifier/state trace — Orin — 2026-10-20

This fresh randomized same-service pair used the pinned Coder IQ1_M snapshot (revision `5348543e0147355ac9cbcb031184a3546350988e`) and current candidate binary SHA256 `6e4b89f7d0979dd0d16eb000c238aa837d5c990dbe54033dada9a479a93fcd38`. The opt-in CPU Q8_1 mirror was limited to `iq2_s/q2_0@layer=1`. Each arm ran 512-token, 2,048-token and same-service 512-token requests, generating 12 tokens per request. The arm order was delayed control then adaptive cap-8.

The short and long output token IDs match across arms, and each arm's initial/recovery short outputs match. Delayed terminal fingerprints are exact; adaptive terminal fingerprints differ in `gdn`, `tail`, `pooled`, `pooled_full`, and `kv`. We captured positions 512–515 in dispatch, verifier GDN intermediates, verifier pre/post state and accepted commit state. Every selected layer-2 GDN field and state is bit-identical between initial and recovery in both arms; layer-2 committed recurrent and convolution state is also bit-identical across arms at all four positions. Raw verifier-state dumps are byte-identical across arms.

The per-GDN service-hash comparison still finds the first adaptive initial/recovery difference at endpoint 511, beginning at GDN ordinal 3 (model layer 4), and finds 33/36 differing GDN hashes at each paired endpoint through 522. Delayed control stays exact through 522. The position-512 all-layer dispatch trace reports first owner placement change at layer 1, first activation change at layer 3, and first expert-ID change at layer 4. The layer-2 state capture is therefore downstream of the needed explanation in model order and does not quantify the layer-4 difference. The next direct diagnostic should capture verifier parts and raw pre/post plus committed state at model layer 4, endpoint 511.

Both supervised runs passed. Minimum host/admission availability was 14.14 GiB for delayed control and 14.20 GiB for adaptive. Maximum scope use was 10.23 and 10.75 GiB; sampled `high`, `max`, `oom`, and `oom_kill` counters were zero. This remains correctness evidence for one model and workload, not an answer-quality or performance result.

The delayed-control `analysis.json` was created before the runner summary fix and initially labeled the GDN state capture as position 511. Raw headers show exactly two records for each requested position 512–515; the summary was corrected from those validated headers and annotated. The adaptive arm ran with the corrected summary code. The pair campaign retains the source hash recorded at launch; the per-arm launch files and raw capture headers document this summary-only correction. Captures and measurements were not changed.

Reproduce from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261045 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1' \
  --capture-moe-positions 512,513,514,515 \
  --capture-verify-gdn-layer 2 --verify-gdn-positions 512,513,514,515 \
  --capture-verify-gdn-state-layer 2 --gdn-state-positions 512,513,514,515 \
  --capture-gdn-commit-state-layer 2 --gdn-commit-state-positions 512,513,514,515 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-layer1-mirror-prefix-trace
```

Raw captures, comparator outputs, service logs and supervisor telemetry are retained beside this report. The follow-up for positions 516–523 is separate and still underway.
