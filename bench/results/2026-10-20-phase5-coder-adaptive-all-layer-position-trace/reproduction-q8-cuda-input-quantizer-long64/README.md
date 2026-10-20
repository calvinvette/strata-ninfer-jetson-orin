# 64-token accepted-prefix follow-up — Orin — 2026-10-20

This same-service adaptive/delayed comparison extends the earlier 16-token
recovery check to 64 generated tokens per request. It used the pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M shards, current candidate
binary SHA256
`14afd1a4b953e176a88d7812bddcdf2beb65944bb5795beaf0f37e5834a496aa`, and
`STRATA_NATIVE_CPU_Q8_1_DOT=all`. Both arms ran short/long/recovery prompts
(512/2,048/512 prompt tokens) with 64 generated tokens each, greedy decoding,
`MemoryMax=28G`, and a six-GiB host-availability floor. Arm order was
adaptive-cap8 then delayed-control. This is a correctness test, not a timing or
quality comparison.

All 64 generated token IDs matched between the initial short prompt and its
recovery in both arms. The delayed-control recovery also matched all 64
accepted-prefix state fingerprints and all per-layer GDN hashes. The adaptive
recovery matched the first eight accepted-prefix state fingerprints, then
differed at prefixes 8–63 (zero-based indices); the first differing GDN hashes
were ordinals 24–35. Its final `gdn`, `tail`, `pooled`, `pooled_full`, and `kv`
fingerprints differed. Thus equal completion text and token IDs do not imply
equal persistent state: the 16-token checks passed earlier, while this longer
accepted chain exposes a later state divergence. The captured position-511
dispatch rows still show no adaptive activation difference between initial
and recovery prompts, although owner changes occur in 23 layers. The capture
does not identify the first divergent accepted-token operation or its cause.

Both supervised arms passed with zero sampled cgroup low/high/max/OOM/OOM-kill
events. Adaptive and delayed-control minimum host/admission availability was
14.14 and 14.32 GiB; peak scope use was 10.85 and 10.60 GiB. Runs took 311.1
and 371.2 seconds. Clocks remained dynamic; energy was not attributed to the
requests. The complete per-token service log, state fingerprints, all-layer
position-511 trace, supervisor samples and analyzer output are retained here.

Reproduce from the repository root (the model remains in
`~/models/strata-orin-validation/`):

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261032 --continuations 0 --generated-tokens 64 \
  --output /tmp/coder-adaptive-long64

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/analyze_trace.py \
  --run /tmp/coder-adaptive-long64 \
  --output /tmp/coder-adaptive-long64/accepted-prefix-analysis.json
```

The generated-token option defaults to 16, preserving the prior harness
behavior. Phase 5 remains open; the adaptive selector remains opt-in.
