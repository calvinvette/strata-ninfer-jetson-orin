# Prefill chunk × prompt-length screen — CPU sharing disabled — Orin — 2026-10-11

This follow-up repeats the chunk-32 versus chunk-128 three-length screen with
`STRATA_PREFILL_CPU_SHARE=0` set for both arms. It uses three randomized
independent process pairs, three distinct formatted prompts (172, 557 and 1,069
tokens), and eight output tokens per request. All API counts passed, all
supervised runs passed, and the exact output text matched in only 6 of 9
within-pair comparisons. Across independent processes, output text was stable
for both chunks at 172 tokens, stable only for chunk 128 at 557 tokens, and
unstable for both chunks at 1,069 tokens. Disabling CPU prefill sharing therefore
did not establish output stability for these longer diagnostic prompts.

The table reports the median paired candidate/control ratio across three
process blocks. Bootstrap intervals resample whole process pairs (50,000
resamples, seed 20261014); n=3 makes them screening summaries.

| Prompt | Output text matched | Request-time ratio (95% interval) | TTFT ratio (95% interval) | Prompt-rate ratio | Decode-rate ratio |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 172 tokens | 3/3 pairs | 0.516 (0.513–0.516) | 0.488 (0.483–0.490) | 2.074 | 0.945 |
| 557 tokens | 2/3 pairs | 0.385 (0.383–0.391) | 0.375 (0.373–0.377) | 2.677 | 0.990 |
| 1,069 tokens | 1/3 pairs | 0.349 (0.349–0.352) | 0.345 (0.344–0.347) | 2.908 | 1.289 |

Chunk 128 again improved the measured prefill and first-visible latency, while
short-request decode ratios varied with output drift. This is not a quality
pass and does not justify changing the default. No energy, disk, page-fault or
GPU/EMC clock measurements were collected. Minimum `MemAvailable` was 8.53 GiB;
CPU clocks varied from 729 to 2,201 MHz, temperature from 55.0 to 60.3 C, and
tegrastats GR3D utilization from 0 to 99%.

The raw requests, configs, engine logs and telemetry are retained in
`campaign/`; `campaign/paired-analysis.json` records per-block full-precision
values, text hashes and pass checks. The current binary SHA256 is
`3fc0f58108c14e5e33bcfbf1092f1b377b132451ae77305878ca406f70d397f1`. This
result further motivates accepted-prefix/state investigation before any chunk
setting can be promoted.
