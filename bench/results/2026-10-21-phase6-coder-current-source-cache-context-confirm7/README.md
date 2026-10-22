# Current-source Coder IQ1_M expert-cache confirmation

This seven-block confirmation tests the cache-size direction from the
[four-cell cache × context screen](../2026-10-21-phase6-coder-current-source-cache-context-screen3/README.md).
It fixes context at 8K and compares cache arguments 1,500 and 3,000 on a
different held-out 512-token retrieval-and-sum prompt. Each paired block
randomizes the order of two fresh service cells; each service runs one warmup
and three measured requests.

## Identity and controls

- Jetson AGX Orin, ARM64, CUDA 12, SM87; all measured requests ran on
  2026-10-21.
- Model: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
  `5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M two-shard GGUF. Model
  shards remained under `~/models/strata-orin-validation/Coder-GGUF/`;
  hashes are in [`model-sha256.txt`](model-sha256.txt).
- Source commit: `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`.
- Candidate binary SHA256:
  `b672187692408e8abcb48beb6d80282b01954bae819ec48963ac7c6440e4ec9`.
- Fixed settings: 8,192-token context, MTP off, FP16 KV, 64-token prefill,
  eight pool workers, prompt cache disabled, adaptive swaps disabled.
- The only varied setting was the `--expert-cache` argument, 1,500/3,000.
  The engine admitted 1,934/3,903 slots, or 3,807/7,615 MiB, respectively.
- Seven randomized paired blocks, each on the same local day; separate
  28-GiB cgroup per service cell, six-GiB physical host floor, read-only clock
  sampling and no clock controls. Energy was not measured.

Raw requests, per-cell capabilities and supervisor records are under
[`per-cell-scopes/`](per-cell-scopes/). The held-out prompt rendered to exactly
512 tokens with the model tokenizer. All 42 measured requests returned the
exact 47-token answer:
`EARLY=TUNDRA-ORBIT-593, MIDDLE=COBALT-MAPLE-248, LATE=GRANITE-COMET-761, SUM=1602`.

## Paired effects

Each cell value is the median of three requests in one fresh service; the
paired effect is calculated across seven independent blocks. Negative latency
changes mean faster; positive throughput changes mean faster. Intervals
bootstrap the paired block effects.

| Metric, cache 3,000 vs 1,500 | Median paired change | Paired-block bootstrap 95% interval |
|---|---:|---:|
| Client TTFT | −13.47% | −13.61% to −12.90% |
| Client total request time | −12.83% | −12.96% to −12.30% |
| Prompt throughput | +15.77% | +14.81% to +15.83% |
| Decode throughput | +10.24% | +9.45% to +10.32% |

All seven block effects favored the larger cache on all four measures. Minimum
host and admission availability was 14.19 GiB. All per-arm cgroup `low`,
`high`, `max`, `oom`, and `oom_kill` counters were zero. The larger cache used
3,808 MiB more shared physical memory at the measured allocation; that
cost is part of the result.

Reproduce the cells and paired-block analysis from the repository root:

```sh
bash bench/results/2026-10-21-phase6-coder-current-source-cache-context-confirm7/run_confirm7.sh
python3 bench/results/2026-10-21-phase6-coder-current-source-cache-context-confirm7/analyze_confirm7.py
```

## Scope

This confirms the larger-cache latency direction for one IQ1_M Coder model, one
short held-out task, 8K configured context and MTP-off/FP16 serving. It does not
test larger prompts, 16K context behavior or other model formats. The prior
screen's under-0.5% context difference used only the same short prompt and
does not qualify 16K context. No default or profile changed; Phase 6 remains
open for the remaining factors and Phase 5's adaptive accepted-state issue
remains open.
