# Coder IQ1_M order-balanced performance screen

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This four-pair screen
repeats the held-out 50-token `is_prime` request from the earlier Coder screen,
using the same binary, IQ1_M model, static expert profile and launch settings.
Two pairs run Strata first and two run strict NInfer first. Each fresh engine
gets an eight-token same-prompt warmup, followed by the 89-token measured
answer. State hashing and accepted-prefix capture are disabled.

## Results

All eight measured answers produced the same 89 token IDs and passed all 11
executable function cases. Three pairs had the same 1,649/44,640 expert hit
counts in each arm. In pair 1, NInfer recorded 1,712/46,080 hits and accepted
4/11 speculative drafts, while Strata recorded 1,649/44,640 hits and accepted
0/4. The other three pairs recorded 0/4 accepted drafts in both arms.

| Metric | Pair effects (NInfer vs Strata) | Paired median | Four-pair bootstrap 95% screen interval |
|---|---|---:|---:|
| Decode TPS gain | −67.25%, −0.63%, −0.11%, −0.05% | **−0.37%** | −67.25% to −0.05% |
| Prompt TPS gain | −0.01%, −0.07%, −0.05%, −0.14% | −0.06% | −0.14% to −0.01% |
| First-token latency reduction | +0.01%, −0.07%, −0.03%, −0.13% | −0.05% | −0.13% to +0.01% |
| Client total-time reduction | −150.81%, −0.46%, −0.09%, −0.08% | −0.28% | −150.81% to −0.08% |

The first pair contained a large NInfer decode outlier: 2.07 tokens/s versus
6.32 for Strata, with 43.0 s measured decode time versus 14.1 s. The three
remaining pairs were tightly grouped around 7.8 tokens/s for both backends.
The outlier is retained; its cause is unknown. Prompt throughput and first-token
latency stayed close in every pair. The median did not approach the plan's 5%
useful-effect threshold, so this screen does not warrant the seven-pair
confirmation or profile promotion. The interval's negative upper bound reflects
four samples and the retained outlier; it is not a release-grade regression
claim.

This is an order-balanced, fixed order sequence, not a randomized confirmation.
Model, profile, binary and task identities are in [`results.json`](results.json).
The earlier three-pair screen had all NInfer-first pairs and measured +0.49%
median decode change. These screens are retained separately; pooling them would
mix different order designs and is not used as the decision statistic.

## Conditions and limits

- Model: Qwen3.8-Flash-Next GSQ-RCO Coder IQ1_M, both GGUF shards.
- Binary SHA-256: `df8e666b8d19dbdc5f687826b4d7187783f4c91aaf5ba2037497a65823d4be98`.
- Static profile SHA-256: `c1e66c2e60ae8e7880befa303fb6bb79da1ccdd59895053eb95d433c648ef047`.
- Context 512, prompt 50 tokens, temperature 0, MTP-2, prefill chunk 64,
  prompt cache off, CPU prefill share 0, expert-cache argument 256.
- Minimum available RAM was 20.30 GiB, above the six-GiB guard. Sampled swap
  peaked at 1.36 GiB; the existing cgroup OOM-kill count remained one.
- GPU/CPU clocks were observed but uncontrolled; initial GPU readback was
  306 MHz. EMC readback was denied and energy was not measured.
- One pair's speculative acceptance and hit counters differed between
  backends despite matching output tokens. No cause is assigned.

Full per-process logs and supervisor telemetry remain local. The curated paired
measurements and identity hashes are in [`results.json`](results.json).

## Reproduction

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-11-05-e6-coder-order-balanced-repeat/supervisor-retry \
  --sample-clocks --timeout 1800 -- \
  python3 bench/results/2026-11-05-e5-coder-natural-prompt/run_is_prime_perf_screen.py \
  bench/results/2026-11-05-e6-coder-order-balanced-repeat/run \
  --orders='strata,ninfer;ninfer,strata;strata,ninfer;ninfer,strata'
```
