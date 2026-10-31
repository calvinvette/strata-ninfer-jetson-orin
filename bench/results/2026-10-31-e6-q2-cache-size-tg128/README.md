# Q2_0 longer-generation cache-capacity screen

Date: 2026-10-31. Same binary, Q2_0 artifacts, strict NInfer backend, 8,192-token
reservation and cache/adaptive-swap settings as the [8K cache-policy
confirmation](../2026-10-31-e6-q2-cache-size-confirm/README.md). This three-pair
screen kept the two 512-token heldout retrieval prompts and requested 128 output
tokens per task. Each independent process warmed each task once; tracing and
prompt cache were off. Pair order was randomized within each independent pair.

## Eligible task and results

The `NIMBUS-7319` task completed exactly 128 tokens in all six measured
observations, with the exact expected code at response start. Candidate advantage
is positive when 4K is faster.

| Metric | 3K median | 4K median | 4K advantage (95% paired interval) |
| --- | ---: | ---: | ---: |
| Prompt TPS | 22.93 tok/s | 23.62 tok/s | +2.99% (−3.79%, +3.46%) |
| Decode TPS | 7.66 tok/s | 8.02 tok/s | **+9.40% (+3.55%, +10.63%)** |
| First-visible TTFT | 22.53 s | 21.89 s | +2.87% (−4.05%, +3.63%) |
| Client total | 39.09 s | 37.86 s | +3.13% (+1.54%, +6.21%) |

The three-pair decode screen clears the 5% median threshold and its interval
excludes zero, but it is based on one eligible prompt and the small-sample
bootstrap interval is discrete. It is a candidate for confirmation, not a
qualified general cache profile. Response hashes differ across runs; each
response passes the exact answer and fixed-length checks, but full text is not
identical.

## Failed cell and resources

The `ORBIT-4826` task is retained as a failed cell. On 3K, it naturally stopped
at 117 of 128 requested tokens in both its warmup and measured requests; the
matched 4K task reached 128. The harness marked those 3K cells incomplete, so
this task is excluded from paired effects. The pair-0 baseline process therefore
has a separate failed task even though its NIMBUS measured task passed. A new
multi-prompt confirmation should replace ORBIT with a task that reliably
completes 128 tokens, or qualify natural-stop behavior using an output-length
metric designed for it.

Across eligible process runs, minimum sampled available RAM was 10.28 GiB,
maximum sampled swap was 2.67 GiB and sampled OOM kills were zero. The six-GiB
host floor and three-GiB workspace reserve remained in force. Clocks remained
dynamic; EMC readback was denied. Energy was not request-attributed.

Adaptive swaps were enabled. This is configured capacity plus adaptive policy,
not a fixed-resident-map experiment. No default or release profile changes.
E6/E7 remain open. Per-process observations and the excluded-cell summary are
in [`paired-summary.json`](paired-summary.json).
