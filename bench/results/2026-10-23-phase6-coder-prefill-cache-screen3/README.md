# Coder IQ1_M prefill chunk × expert-cache screen

This screening campaign crosses prefill chunks 32/128 with requested expert
cache budgets 1,500/3,000 slots for the held-out Coder retrieval/arithmetic
prompt used by the current-source cache/context campaign. It fixes context at
8,192, FP16 KV, MTP off, eight expert workers, and current-source CUDA/SM87
binary `build/integration/candidate/strata`. Each of three randomized blocks
uses a fresh service for every cell, one same-task warmup, and one measured
request. The screening is descriptive; it does not promote a default.

Model weights remain in `~/models/strata-orin-validation/Coder-GGUF/IQ1_M/`.
The model revision is `5348543e0147355ac9cbcb031184a3546350988e`. Binary and
model shard hashes are recorded in `design.json` and `model-sha256.txt`.

Run from the repository root:

```sh
python3 bench/results/2026-10-23-phase6-coder-prefill-cache-screen3/run_screen3.py
python3 bench/results/2026-10-23-phase6-coder-prefill-cache-screen3/analyze_screen3.py
```

The runner randomizes the four cells independently in each block, supervises
each service with a 28-GiB cgroup memory maximum and read-only clock samples,
and retains incomplete/failed cells. The analyzer requires the exact answer,
7,501 actual prompt tokens, one warmup and one measured request per cell, the
six-GiB physical headroom floor, observed cgroup v2, and zero cgroup memory
events. It reports block contrasts and cache × prefill ratio-of-ratios without
confidence intervals; three blocks are screening evidence only. Energy is not
measured. The named rails available on Orin include idle/background activity
and are not process-attributed.

Raw per-cell requests, logs, telemetry, and analysis remain in the local
`per-cell-scopes/` tree and are not committed. A seven-block held-out
confirmation is required before drawing a configuration recommendation.

## Block 1 checkpoint

All four randomized cells passed with the exact answer, 7,501 actual prompt
tokens and 45 generated tokens. The cache realized 1,934 slots (3,807 MiB) for
the 1,500-slot argument and 3,903 slots (7,615 MiB) for the 3,000-slot
argument.

| Requested slots | Chunk | Client TTFT | Client total | Prompt tok/s | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,500 | 32 | 576.1 s | 579.9 s | 13.0 | 11.7 |
| 1,500 | 128 | 197.3 s | 201.1 s | 38.1 | 11.4 |
| 3,000 | 32 | 556.2 s | 559.6 s | 13.5 | 12.9 |
| 3,000 | 128 | 166.5 s | 169.8 s | 45.1 | 13.1 |

Within this single block, chunk 128 reduced client total time 65.3% at 1,500
slots and 69.6% at 3,000 slots. Increasing the requested cache reduced total
time 3.5% at chunk 32 and 15.5% at chunk 128. The observed time interaction
(ratio-of-ratios) was −12.5%; prompt-rate interaction was +14.0%. Decode-rate
changes were small (−2.6%/+1.6% for chunk 128 at the two cache settings). These
are descriptive one-block contrasts, with no confidence interval or promotion
claim. All cells stayed above the six-GiB floor; minimum physical/admission
availability was 14.38/14.14 GiB and cgroup pressure/OOM counters were zero.
The run sampled dynamic clocks; EMC readback was unavailable. Energy was not
measured. Blocks 2 and 3 remain outstanding.
