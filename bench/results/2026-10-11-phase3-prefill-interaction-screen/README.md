# Prefill chunk × prompt-length screen — default CPU sharing — Orin — 2026-10-11

Three randomized independent process pairs compared chunk sizes 32 and 128 on
three distinct prompts of 172, 557 and 1,069 formatted tokens. Each process
warmed and measured all three prompts, with eight requested output tokens per
request. Model/MTP, profile, context 4,096, expert-cache budget, workspace
reserve, one worker and prompt-cache setting were held fixed. The actual cache
reported 6,519 variable-size slots in every run. Every request passed API token
count checks and the six-GiB supervisor; minimum `MemAvailable` was 8.48 GiB.

The table reports the candidate/control median ratio across three paired
blocks. The interval is a percentile bootstrap over whole process pairs (50,000
resamples, seed 20261013); at n=3 it is screening evidence only.

| Prompt | Output text matched | Request-time ratio (95% interval) | TTFT ratio (95% interval) | Prompt-rate ratio | Decode-rate ratio |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 172 tokens | 3/3 pairs | 0.515 (0.513–0.526) | 0.489 (0.488–0.503) | 2.066 | 0.979 |
| 557 tokens | 3/3 pairs | 0.404 (0.403–0.408) | 0.393 (0.393–0.397) | 2.556 | 0.972 |
| 1,069 tokens | 2/3 pairs | 0.359 (0.349–0.365) | 0.352 (0.340–0.356) | 2.851 | 1.014 |

Output is only eight tokens, so pairwise text equality is a narrow drift check,
not model quality qualification. The 1,069-token prompt showed one pairwise
text mismatch. The single-prompt chunk-32/128 screen had matched text in all
seven pairs, but that result does not erase this separate variation. No default
change is supported. Raw requests, engine logs, configurations and telemetry
are retained in `campaign/`; `campaign/paired-analysis.json` has full-precision
samples and output hashes.

The minimum availability remained above the ordinary six-GiB floor. CPU clocks
varied from 729 to 2,201 MHz, CPU/TJ temperature from 52.2 to 61.5 C, and
tegrastats GR3D utilization from 0 to 99%; GPU/EMC clocks and energy were not
measured. This is a resource/performance screen, not held-out quality or
confirmation. The binary SHA256 is
`3fc0f58108c14e5e33bcfbf1092f1b377b132451ae77305878ca406f70d397f1`.
