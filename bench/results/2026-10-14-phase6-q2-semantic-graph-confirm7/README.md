# Q2_0 semantic graph × MTP confirmation

This Orin AGX Phase 6 campaign used seven randomized blocks of four fresh
services: captured/eager verifier route × MTP disabled/window 2. Every timed
request used the same held-out, exact 512-token semantic prompt and a 64-token
generation cap. The current Q2_0 artifact, FP16 KV, 3,000-slot expert cache,
accepted-only adaptation cadence 4, binary identity, randomized order, and
per-cell configs are recorded under [`run/`](run/). A distinct short warmup
preceded each timed request. Services ran under a 28 GiB systemd memory cap;
the six-GiB physical host floor and separate three-GiB workspace reserve were
preserved. Clocks remained dynamic and read-only.

All 28 timed cells passed workload, fresh-prompt, resource and supervisor
checks. All generated text was identical across all cells. Minimum physical
host availability was 16.899 GiB; minimum admission availability was 11.832
GiB. No memory-pressure or OOM event was recorded.

| Comparison | Median request-time change | Paired 95% interval |
| --- | ---: | ---: |
| Captured vs eager, MTP off | +1.86% | −2.49% to +4.59% |
| Captured vs eager, MTP2 | +0.89% | −2.20% to +9.62% |
| MTP2 vs off, captured | +16.93% | +7.49% to +25.40% |
| MTP2 vs off, eager | +11.52% | +9.46% to +13.76% |
| Capture × MTP request-time interaction | +0.49% | −4.27% to +10.09% |

The estimates use 20,000 percentile-bootstrap resamples over seven whole
within-block paired ratios; successive tokens are not treated as replicates.
For this exact workload, graph capture had no resolved end-to-end latency
effect. MTP2 increased median request time in both routes. The same direction
appeared in TTFT and prompt throughput; decode-rate intervals include little or
no change in at least one contrast. MTP2 offered and accepted 33/20 drafts in
each block, insufficient to pay back verification and prefill cost here. This
is not a broad claim about other prompt lengths, models, cache sizes or MTP
windows.

## Full-task quality check

The same exact 512-token semantic prompt was then run once per graph × MTP
condition with a 512-token generation allowance, in fresh supervised services.
All four responses stopped naturally at 334 completion tokens (285 words),
passed every rubric item, and were byte-identical (SHA-256
`75da7d861284f39e13c68d79fcbc70af15ba592502e8aeef44880ac4436651bb`). The
rubric checks the required opening, minimum length, scan code/input path,
fetch-decode-execute, binary and RAM concepts, output and storage paths, and
the exact arithmetic `17 x 19 = 323`. Minimum host availability across these
four runs was 16.928 GiB and minimum admission availability was 13.454 GiB.
The pilot used to validate the prompt is retained separately under `pilot/`.

These four quality runs qualify this particular task and these settings only;
they do not establish a general quality budget or erase earlier adaptive-swap
output/state sensitivities on other prompts. Energy is whole-device and not
request-attributed; energy per token was not measured. Dynamic clocks and the
shared OS file cache remain sources of variation. No route, MTP setting or
default is promoted from this result. The machine-readable timing and quality
summaries are [`analysis.json`](analysis.json) and
[`quality-analysis.json`](quality-analysis.json).
