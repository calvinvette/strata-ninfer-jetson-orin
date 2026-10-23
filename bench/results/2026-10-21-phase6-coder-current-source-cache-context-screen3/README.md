# Current-source Coder IQ1_M cache × context screen

This randomized four-cell screen tests whether changing the requested expert
cache budget interacts with configured context on the Coder IQ1_M service.
Each fresh service ran one same-task warmup followed by three measured
requests. These are screening medians, not independent-block confirmation
estimates; no confidence intervals are reported.

## Identity and fixed settings

- Jetson AGX Orin, ARM64, CUDA 12, SM87; all cells ran on 2026-10-21.
- Model repository: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`,
  revision `5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M two-shard GGUF.
  Model files remained under `~/models/strata-orin-validation/Coder-GGUF/`;
  shard checksums are in [`model-sha256.txt`](model-sha256.txt).
- Source commit: `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`.
- Candidate binary SHA256:
  `b672187692408e8abcb48beb6d80282b01954bae819ec48963ac7c6440e4ec9`.
- The only varied settings were requested `--expert-cache` values 1,500/3,000
  and context limits 8,192/16,384. The cache flag name is retained from the
  engine; actual admitted slots and MiB are reported below.
- Other settings were held at MTP off, FP16 KV, 64-token prefill chunks,
  eight pool workers, prompt cache disabled, and adaptive swaps disabled.
  Each cell had a separate 28-GiB cgroup, read-only clock sampling, and no
  clock controls. The 512-token task and exact answer are retained in
  [`workloads.json`](workloads.json).

The screen and randomized cell order are in [`campaign/`](campaign/).
[`analysis.json`](analysis.json) records each cell median, contrasts, token
counts, exact-answer checks and memory-scope audit. Re-run its analysis with:

```sh
python3 bench/results/2026-10-21-phase6-coder-current-source-cache-context-screen3/analyze_screen.py
```

## Results

Each cell reports the median of three measured requests after its warmup. The
task returned exactly 512 prompt tokens and 45 completion tokens on all 12
measured requests, each matching:
`EARLY=EMBER-VAULT-317, MIDDLE=SILVER-MAPLE-846, LATE=TIDAL-COPPER-529, SUM=1692`.

| Context | Cache argument | Actual expert slots / MiB | Median TTFT | Median client total | Prompt / decode rate |
|---|---:|---:|---:|---:|---:|
| 8K | 1,500 | 1,934 / 3,807 | 20.86 s | 24.32 s | 24.7 / 12.7 tok/s |
| 8K | 3,000 | 3,903 / 7,615 | 18.25 s | 21.41 s | 28.2 / 13.9 tok/s |
| 16K | 1,500 | 1,934 / 3,807 | 20.93 s | 24.39 s | 24.6 / 12.7 tok/s |
| 16K | 3,000 | 3,903 / 7,615 | 18.33 s | 21.49 s | 28.1 / 13.9 tok/s |

At 8K, the 3,000 cache argument had 12.54% lower median TTFT and 11.95%
lower median total time than 1,500; at 16K, the corresponding changes were
−12.41% and −11.93%. Prompt throughput rose about 14.2% and decode throughput
about 9.45% at either context. The 16K context setting changed median TTFT and
total time by less than 0.5% at either cache argument. These are within-screen
descriptive comparisons; each set of three requests shared one service and
the result does not establish a performance recommendation.

One of the three 16K/1,500-cache measurements was slower: 52.24 s TTFT and
55.70 s total, versus 20.82/24.28 s and 20.93/24.39 s for the other two. It is
retained in the raw records. The median is not driven by this sample; its cause
is not established by this screen.

All four supervisors passed. Across 590 memory samples, minimum host and
admission availability was 14.14 GiB, with zero cgroup `high`, `max`, `oom`,
or `oom_kill` events; the six-GiB host floor remained intact. The larger cache
admitted 3,903 slots / 7,615 MiB and had lower minimum host availability than
the 1,934-slot cells. Energy was not measured.

## Next gate

The screen suggests that the larger cache may reduce latency for this short
Coder task and that the context limit alone has little effect when the actual
prompt remains 512 tokens. The larger cache also uses substantially more
physical shared memory. Confirm any cache choice with at least seven
independent randomized pairs, held-out prompts, full memory admission checks,
and a context workload that exercises the larger reservation before promoting
a profile. No setting changed. Phase 6 remains open.
