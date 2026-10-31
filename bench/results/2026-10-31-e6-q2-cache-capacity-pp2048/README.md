# Q2_0 2K prompt cache-capacity screen

Date: 2026-10-31. This is a same-build, randomized three-pair comparison of
3,000 versus 4,000 configured expert-cache slots with strict NInfer. Runtime
settings, Q2_0 artifacts, 8,192-token context reservation and adaptive-swap
policy match the [8K cache-policy confirmation](../2026-10-31-e6-q2-cache-size-confirm/README.md).
The workload used a tokenizer-verified 2,048-token prompt, 48-token generation
limit, one warmup and one measured request per independent process. Prompt
cache and tracing were off; clocks remained uncontrolled.

## Correctness and results

All six measured requests passed. Each response began with the exact three
position-distributed retrieval codes and checksum (`SUM=1768`); each generated
47 tokens before the natural stop. All response hashes matched. This is a
functional check for this fixture, not broad model-quality equivalence.

Positive advantage means the 4K arm is faster. Three-pair bootstrap intervals
are discrete and descriptive.

| Metric | 3K median | 4K median | 4K advantage (95% paired interval) |
| --- | ---: | ---: | ---: |
| Prompt TPS | 42.17 tok/s | 41.33 tok/s | −1.41% (−2.55%, +1.13%) |
| Decode TPS | 8.95 tok/s | 8.63 tok/s | **−3.79% (−4.28%, −3.15%)** |
| First-visible TTFT | 48.94 s | 50.00 s | −1.56% (−2.74%, +0.93%) |
| Client total | 53.84 s | 55.24 s | −1.73% (−2.68%, +0.63%) |

The decode gain seen in the pp512+tg64 heldout screen did not carry over to this
pp2048+tg48 task: the 4K median was 3.79% slower. No metric crosses the 5%
regression threshold, so this is not evidence to reject 4K generally, but it
also provides no support for broadening the earlier policy result. The two
workload cells together suggest a workload-dependent cache-capacity effect.

Adaptive swaps were enabled in both arms. This compares configured capacity
plus adaptive ownership, not fixed resident maps or slot count in isolation.
The [paired summary](paired-summary.json) records per-process observations,
ordered answer checks and output hashes; prompts and responses are not included.

## Resources and scope

Minimum sampled available RAM was 10.28 GiB, peak sampled swap was 2.77 GiB,
and sampled OOM kills were zero. The 6 GiB host floor and 3 GiB workspace
reserve remained in force. CPU/GPU clocks were observed dynamically; EMC
readback was denied. No request-attributed energy was measured.

Keep 4K as a candidate only for the confirmed 8K/pp512+tg64 retrieval domain.
Do not generalize its speedup to longer prompts or promote it as a release
profile. E6/E7 remain open.
