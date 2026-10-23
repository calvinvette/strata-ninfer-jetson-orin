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

## Screening checkpoint: blocks 1–2 of 3

All eight cells across the first two blocks passed. Each returned the exact
answer with 7,501 prompt tokens and 45 generated tokens. The cache realized
1,934 slots (3,807 MiB) for the 1,500-slot argument and 3,903 slots (7,615 MiB)
for the 3,000-slot argument.

Block 1 measured:

| Requested slots | Chunk | Client TTFT | Client total | Prompt tok/s | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,500 | 32 | 576.1 s | 579.9 s | 13.0 | 11.7 |
| 1,500 | 128 | 197.3 s | 201.1 s | 38.1 | 11.4 |
| 3,000 | 32 | 556.2 s | 559.6 s | 13.5 | 12.9 |
| 3,000 | 128 | 166.5 s | 169.8 s | 45.1 | 13.1 |

Block 2 measured:

| Requested slots | Chunk | Client TTFT | Client total | Prompt tok/s | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3,000 | 32 | 568.5 s | 572.1 s | 13.2 | 12.8 |
| 3,000 | 128 | 164.6 s | 168.0 s | 45.6 | 13.2 |
| 1,500 | 128 | 185.6 s | 189.1 s | 40.5 | 11.9 |
| 1,500 | 32 | 577.4 s | 580.7 s | 13.0 | 12.0 |

Across these two screening blocks, chunk 128 reduced median client total time
66.4% at 1,500 slots and 70.1% at 3,000. The larger cache reduced total time
2.5% at chunk 32 and 13.3% at chunk 128. The block time interaction
(ratio-of-ratios) was −12.5% and −9.8%, median −11.1%; prompt-rate interaction
was +12.4%. Decode-rate effects from chunk size stayed small (median −1.7% at
1,500 slots, +2.3% at 3,000). These are descriptive two-block contrasts with
no confidence intervals or promotion claim. Minimum physical/admission
availability was 14.31/14.14 GiB, and cgroup pressure/OOM counters were zero.
Dynamic clocks were sampled; EMC readback was unavailable. Energy was not
measured. Block 3 remains outstanding.
