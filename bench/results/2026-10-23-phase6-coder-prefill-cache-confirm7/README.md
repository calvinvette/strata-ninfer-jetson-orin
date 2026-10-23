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
events.

Randomized block 5 passed all four cells; each answer was exact with 7,501
prompt and 46 completion tokens:

| Requested slots | Chunk | Client TTFT | Client total | Prompt tok/s | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,500 | 32 | 584.5 s | 588.2 s | 12.8 | 12.3 |
| 1,500 | 128 | 186.2 s | 189.9 s | 40.3 | 12.2 |
| 3,000 | 128 | 166.4 s | 169.8 s | 45.1 | 13.1 |
| 3,000 | 32 | 568.3 s | 571.7 s | 13.2 | 13.2 |

The five-block partial audit passed all twenty cells. Across blocks 1–5,
chunk 128 reduced median client total time by 67.7%/68.8% at cache arguments
1,500/3,000; the median cache-by-chunk time interaction was −3.0%. These are
descriptive partial results; the analyzer suppresses confidence intervals
until all seven confirmation blocks are present. Minimum physical/admission
availability remained 14.19/14.19 GiB, with zero cgroup events. Blocks 6–7
remain.

Randomized block 6 passed all four cells; each answer was exact with 7,501
prompt and 46 completion tokens:

| Requested slots | Chunk | Client TTFT | Client total | Prompt tok/s | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,500 | 128 | 187.2 s | 191.0 s | 40.1 | 12.0 |
| 1,500 | 32 | 587.7 s | 591.4 s | 12.8 | 12.1 |
| 3,000 | 128 | 166.1 s | 169.5 s | 45.2 | 13.1 |
| 3,000 | 32 | 538.6 s | 541.9 s | 13.9 | 13.4 |

The six-block partial audit passed all twenty-four cells. Across blocks 1–6,
chunk 128 reduced median client total time by 67.7%/68.8% at cache arguments
1,500/3,000; the median cache-by-chunk time interaction was −3.0%. These remain
descriptive partial results without confidence intervals. Minimum
physical/admission availability remained 14.19/14.19 GiB, with zero cgroup
events.

Randomized block 7 passed its four cells. Each answer was exact with 7,501
prompt and 46 completion tokens:

| Requested slots | Chunk | Client TTFT | Client total | Prompt tok/s | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3,000 | 128 | 166.7 s | 170.2 s | 45.0 | 13.0 |
| 1,500 | 128 | 192.2 s | 196.0 s | 39.1 | 11.7 |
| 1,500 | 32 | 586.2 s | 589.9 s | 12.8 | 12.1 |
| 3,000 | 32 | 538.0 s | 541.5 s | 13.9 | 13.0 |

## Seven-block result

The complete seven-block audit passed all 28 measured cells. All measured
responses returned the exact 46-token answer after the expected 7,501-token
prompt. Deterministic paired-block bootstrap intervals use the seven randomized
block contrasts (10,000 resamples); requests and tokens within a block were not
treated as independent replicates.

| Contrast | Median change | Paired-block bootstrap 95% interval |
| --- | ---: | ---: |
| Chunk 128 vs 32, 1,500 requested slots, client total time | 67.71% lower | 67.55%–67.95% lower |
| Chunk 128 vs 32, 3,000 requested slots, client total time | 68.72% lower | 68.56%–68.85% lower |
| Cache × chunk interaction, client total time | −3.13% | −5.43% to −1.93% |
| Chunk 128 vs 32, 1,500 slots, decode throughput | −0.81% | −1.65% to +0.83% |
| Chunk 128 vs 32, 3,000 slots, decode throughput | +0.76% | −0.76% to +1.52% |

The effect is concentrated in prefill/TTFT; decode-throughput intervals include
zero. Minimum physical and admission availability were both 14.19 GiB and all
cgroup memory event counters remained zero. Clocks were sampled and dynamic;
energy was not measured. The cells compare chunk settings and requested cache
arguments for this Coder IQ1_M model, FP16 KV, MTP-off 8K profile and one held-out
archive task. This confirms a large latency effect for the tested prefill path,
not a universal setting or a release-default recommendation. Other Phase 6
interactions, workload/quality domains and the broader Pareto/energy scope
remain open.

### Retrospective named-rail estimate

The retained tegrastats samples also support a retrospective rail analysis in
[`rail-followup`](rail-followup/README.md). It integrates power over each of
the 28 measured request windows; all 28 windows had supported bracketing
samples. `VIN_SYS_5V0` energy per output token was 66.27% lower with chunk 128
at 1,500 requested slots (paired-block bootstrap 95% interval 66.00%–66.50%
lower) and 67.15% lower at 3,000 (66.92%–67.29% lower). The cache-by-chunk
interaction was −3.38% (−4.11% to −1.95%). GPU and CPU named rails are reported
separately in the follow-up. These estimates include idle/background activity,
are not process-attributed, and are neither summed nor whole-device energy.
This adds an energy observation for the same workload; it does not establish
an energy Pareto frontier.
