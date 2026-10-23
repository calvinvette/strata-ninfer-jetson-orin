# Coder prefill chunk × expert cache held-out confirmation

This confirmation follows the three-block screen in
[`2026-10-23-phase6-coder-prefill-cache-screen3`](../2026-10-23-phase6-coder-prefill-cache-screen3/README.md).
It reuses the IQ1_M model, 8K context, FP16 KV, MTP-off configuration and the
2 × 2 cache/chunk grid, but uses a different 7,501-token archive, different
marker locations and values, and a different arithmetic answer.

The confirmation has seven randomized blocks. Each block launches one fresh
service for each of the four cells, with one same-task warmup and one measured
request per cell. All cells use a 28-GiB cgroup limit and retain the six-GiB
physical host reserve. The analyzer audits the exact answer and prompt length,
cell completion, host reserve, cgroup scope and events, then computes paired
block contrasts and deterministic bootstrap intervals over blocks. Individual
tokens and repeated requests within a process are not treated as independent
replicates.

Model files remain in `~/models/strata-orin-validation/`. The exact prompt hash,
model revision, binary identity and campaign factors are in `design.json`.
Raw request and telemetry files are retained under `per-cell-scopes/` locally
and are not committed.

Run from the repository root:

```sh
python3 bench/results/2026-10-23-phase6-coder-prefill-cache-confirm7/run_confirm7.py
python3 bench/results/2026-10-23-phase6-coder-prefill-cache-confirm7/analyze_confirm7.py
```

To resume one unstarted block, pass `--block N` to the runner. The runner
refuses to overwrite an existing block directory. The analyzer defaults to
requiring all seven blocks; its optional `--blocks N` mode is for partial-data
audits and does not satisfy the confirmation gate.

## Status

The tokenizer check and a separate preflight passed. Both preflight requests
returned the exact answer at 7,501 prompt tokens; the natural-stop rule accepts
the model's 46-token response. The preflight retained 18.04 GiB minimum host
availability and 17.67 GiB admission availability, with zero cgroup events. It
is excluded from confirmation statistics.

Randomized block 1 passed all four cells. Each measured request returned the
exact answer with 7,501 prompt tokens and 46 completion tokens:

| Requested slots | Chunk | Client TTFT | Client total | Prompt tok/s | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,500 | 128 | 184.1 s | 187.7 s | 40.8 | 12.3 |
| 3,000 | 128 | 166.8 s | 170.2 s | 45.0 | 13.2 |
| 3,000 | 32 | 537.8 s | 541.3 s | 13.9 | 13.1 |
| 1,500 | 32 | 582.1 s | 585.8 s | 12.9 | 12.0 |

Minimum physical/admission availability across block 1 was 14.33/14.33 GiB;
cgroup events were zero. The one-block paired chunk-128 reductions in client
total time were 68.0%/68.6% for cache arguments 1,500/3,000. The one-block
cache-by-chunk time interaction was −1.9%; this is a preliminary descriptive
contrast and carries no useful uncertainty estimate.

Randomized block 2 also passed all four cells. Each measured request again
returned the exact answer with 7,501 prompt tokens and 46 completion tokens:

| Requested slots | Chunk | Client TTFT | Client total | Prompt tok/s | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,500 | 32 | 584.2 s | 587.9 s | 12.8 | 12.1 |
| 1,500 | 128 | 187.1 s | 190.8 s | 40.1 | 12.1 |
| 3,000 | 32 | 537.7 s | 541.1 s | 14.0 | 13.1 |
| 3,000 | 128 | 167.1 s | 170.4 s | 44.9 | 13.4 |

Randomized block 3 passed all four cells on the distinct archive prompt. Every
answer was exact (7,501 prompt, 46 completion tokens):

| Requested slots | Chunk | Client TTFT | Client total | Prompt tok/s | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3,000 | 32 | 539.3 s | 542.7 s | 13.9 | 13.2 |
| 3,000 | 128 | 165.7 s | 169.0 s | 45.3 | 13.3 |
| 1,500 | 128 | 186.9 s | 190.6 s | 40.2 | 12.1 |
| 1,500 | 32 | 584.5 s | 588.2 s | 12.8 | 12.0 |

Randomized block 4 passed all four cells; each answer was exact with 7,501
prompt and 46 completion tokens:

| Requested slots | Chunk | Client TTFT | Client total | Prompt tok/s | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,500 | 32 | 612.1 s | 615.9 s | 12.3 | 12.1 |
| 3,000 | 128 | 167.0 s | 170.4 s | 44.9 | 13.4 |
| 3,000 | 32 | 542.7 s | 546.0 s | 13.8 | 13.2 |
| 1,500 | 128 | 192.2 s | 196.0 s | 39.1 | 11.9 |

The four-block partial audit passed all sixteen cells. Across blocks 1–4,
chunk 128 reduced median client total time by 67.8%/68.7% at cache arguments
1,500/3,000; the median cache-by-chunk time interaction was −2.4%. These are
descriptive partial results; the analyzer suppresses confidence intervals
until all seven confirmation blocks are present. Minimum physical/admission
availability across the four blocks was 14.19/14.19 GiB, with zero cgroup
events. Blocks 5–7 remain.
