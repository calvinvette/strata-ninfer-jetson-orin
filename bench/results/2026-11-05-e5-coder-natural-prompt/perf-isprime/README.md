# Coder IQ1_M `is_prime` performance screen

Date: 2026-11-05. Jetson Orin AGX, CUDA 12.6. This three-pair screen compares
Strata with strict NInfer on the same Coder IQ1_M static expert profile and the
held-out 50-token `is_prime` prompt. It follows the final-only state checks;
per-token tracing and state hashing were disabled for timing.

## Results

All six measured requests generated the same 89 token IDs, passed all 11
restricted-AST function cases, and recorded 1,649 expert hits from 44,640
lookups. The paired effects below express NInfer relative to Strata. Positive
decode values mean higher NInfer throughput; positive TTFT and client-time
values mean lower latency.

| Metric | Pair 1 | Pair 2 | Pair 3 | Paired median | Three-pair bootstrap 95% screen interval |
|---|---:|---:|---:|---:|---:|
| Decode TPS | +7.28% | −0.64% | +0.49% | **+0.49%** | −0.64% to +7.28% |
| Prompt TPS | −0.29% | −0.19% | +0.03% | −0.19% | −0.29% to +0.03% |
| First-token latency reduction | −0.29% | −0.20% | +0.01% | −0.20% | −0.29% to +0.01% |
| Client total-time reduction | +4.86% | −0.51% | +0.35% | +0.35% | −0.51% to +4.86% |

NInfer's decode rates were 6.99, 7.77 and 7.82 tokens/s; Strata's were 6.51,
7.82 and 7.78 tokens/s. Prompt throughput and first-token latency were nearly
unchanged. The decode median is below the pre-registered 5% useful-effect
threshold, and its interval includes both a small regression and a larger
gain. This is **not evidence of a meaningful NInfer speedup** and does not
justify a seven-pair confirmation or profile promotion. The first pair is
retained; it is not discarded as an outlier.

The runner shuffled each pair's arm order, but all three draws placed NInfer
first. The screen is therefore not order-balanced. Model file-cache state,
thermal behavior and dynamic clocks can be entangled with backend order; the
small apparent median must be treated as preliminary.

## Conditions and limits

- Coder IQ1_M two-shard model; shard names, sizes and SHA-256 values are recorded in
  [`results.json`](results.json). Both shards remained under `~/models`.
- Current executable SHA-256:
  `df8e666b8d19dbdc5f687826b4d7187783f4c91aaf5ba2037497a65823d4be98`.
- Static profile SHA-256:
  `c1e66c2e60ae8e7880befa303fb6bb79da1ccdd59895053eb95d433c648ef047`.
- Context cap 512, 50 prompt tokens, temperature 0, one eight-token same-prompt
  warmup before the measured request in each fresh process, MTP enabled as
  configured. Each request stopped at the model's natural 89-token answer.
- Supervised with `tools/integration/run_control.py`; minimum available RAM was
  21.14 GiB, above the 6 GiB floor. Swap peaked at 1.40 GiB. The existing cgroup
  OOM-kill count remained one. The supervisor's sampled RAM minimum was 21.15
  GiB (rounding difference from the finer memory samples).
- CPU/GPU clocks were dynamic and not controlled. Initial readback reported
  GPU 306 MHz; EMC readback was denied. Energy was not computed; raw rail
  samples are retained only in local supervisor output. Request times are
  sequential client measurements, and three pairs are screening evidence only.

The compact paired data, task identity, hashes and timing values are in
[`results.json`](results.json). Full per-process logs and supervisor telemetry
remain local and are not committed.

## Reproduction

From the integration worktree, run:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-11-05-e5-coder-natural-prompt/perf-isprime-supervisor \
  --sample-clocks --timeout 3600 -- \
  python bench/results/2026-11-05-e5-coder-natural-prompt/run_is_prime_perf_screen.py \
  bench/results/2026-11-05-e5-coder-natural-prompt/perf-isprime-screen
```

The run requires the existing local model shards, executable, profile, and
Orin runtime environment. The stored output JSON is the curated record from
the supervised run; the raw output directory is not part of this commit.
