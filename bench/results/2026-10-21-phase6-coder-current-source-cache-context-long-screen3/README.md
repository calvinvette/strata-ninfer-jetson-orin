# Coder cache × context long-prompt screen — Orin — 2026-10-21

This randomized three-block screen crosses requested expert-cache arguments
1,500/3,000 with configured contexts 8K/16K on a held-out 7,501-token
retrieval-and-arithmetic task. It tests whether the short-prompt cache result
holds when the request occupies most of the 8K context and begins to exercise
16K context. Each cell runs in a fresh Strata service with one same-task warmup
and one measured request. The three-block results are descriptive screening
evidence; they do not support confidence intervals or a setting recommendation.

## Identity and controls

- Jetson AGX Orin, ARM64, CUDA 12, SM87.
- Model: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
  `5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M two-shard GGUF. The shards
  remain under `~/models/strata-orin-validation/Coder-GGUF/IQ1_M/`; hashes are
  copied from the already-validated [short confirmation](../2026-10-21-phase6-coder-current-source-cache-context-confirm7/model-sha256.txt).
- Source base commit `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`; the executable
  is from the current CUDA Release/SM87 build. Exact executable hash is in
  `design.json`.
- Fixed settings: MTP off, FP16 KV, prefill 64, eight pool workers, prompt cache
  off, adaptive swaps off, mmap experts on, no clock control, and read-only
  clock sampling.
- Each fresh service has a 28-GiB cgroup scope. The six-GiB host availability
  floor is preserved. Energy is not measured.

The prompt asks for exact marker values at 10%, 50% and 90% of the 7,501-token
input and their numeric sum. Expected answer:

`EARLY=EMBER-VAULT-317, MIDDLE=SILVER-MAPLE-846, LATE=TIDAL-COPPER-529, SUM=1692`

## Screen results

All 12 measured requests returned the exact 45-token answer with exactly 7,501
prompt tokens. The larger cache admitted 3,903 expert slots / 7,615 MiB versus
1,934 / 3,807 MiB for the smaller cache. Median per-request values pool the
three independent blocks descriptively; paired effects are medians of the
three same-block percentage changes. Positive latency changes below mean the
larger cache was faster.

| Context | Cache argument | Actual slots / MiB | Median client TTFT | Median client total | Median prompt / decode tokens/s | Minimum host / admission GiB |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8K | 1,500 | 1,934 / 3,807 | 330.1 s | 333.6 s | 22.7 / 12.2 | 17.90 / 8.88 |
| 8K | 3,000 | 3,903 / 7,615 | 303.0 s | 306.3 s | 24.8 / 13.3 | 14.32 / 14.32 |
| 16K | 1,500 | 1,934 / 3,807 | 330.4 s | 334.0 s | 22.7 / 11.9 | 17.72 / 15.72 |
| 16K | 3,000 | 3,903 / 7,615 | 305.8 s | 309.2 s | 24.5 / 13.1 | 14.11 / 14.11 |

The paired cache effect favored 3,000 in all three blocks. At 8K, median TTFT
and total time improved 7.99% and 7.97%; prompt and decode rates rose 8.81%
and 8.20%. At 16K, TTFT and total time improved 7.45% each; prompt and decode
rates rose 7.93% and 11.76%. At the 1,500 cache, configured 16K versus 8K
changed median total time by about zero; at 3,000 it was about 1% slower. The
cache-by-context ratio-of-ratios was under 1% for client total time.

All supervisors passed. Minimum host availability was 14.11 GiB and minimum
admission availability was 8.88 GiB, both above the six-GiB floor. Per-cell
cgroup `low`, `high`, `max`, `oom`, and `oom_kill` counters stayed at zero.
Clocks remained dynamic; energy was not measured. These three blocks and one
measured request per cell are a screen only; they do not provide confidence
intervals, sustained-load evidence, or a general cache recommendation. A
separate seven-block confirmation on another held-out long prompt is needed
before considering a cache profile for this task class.

## Reproduction

```sh
python3 bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-screen3/run_screen3.py
python3 bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-screen3/analyze_screen3.py
```

Each block independently randomizes the four cells. Request, capability,
supervisor, memory, and clock observations remain under `per-cell-scopes/`.
`analysis.json` checks the exact answer and actual prompt length, cache
allocation, host/admission floors, and cgroup events, then reports descriptive
paired cache, context, and interaction effects.

A separate initial attempt is retained under
[`long-screen3-invalid-overlap`](../2026-10-21-phase6-coder-current-source-cache-context-long-screen3-invalid-overlap/).
It crossed the six-GiB floor while an agent checksum helper was reading the
large model shards into memory. That floor breach is confounded and excluded;
the rerun uses the previously recorded model hashes and performs no model-file
reads during measurement.
