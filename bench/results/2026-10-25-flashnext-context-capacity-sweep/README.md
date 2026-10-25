# Qwen3.8-Flash-Next context-capacity sweep on the current Orin port

Measured on the local Jetson AGX Orin using the current candidate binary
`build/integration/candidate/strata` (SHA256
`ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df`; runtime
source commit `348e6261ab3fa5f119ec3050637c01477fddaa78`). The sweep covers
configured context capacities 1,024 through 262,144 tokens for Coder IQ1_M,
Coder Q2_0 and the original non-Coder ISTA-DASLab IQ3_S model. All 27
model/capacity cells passed, and each completed request used fresh prefill and
generated exactly 64 tokens.

## Method

This follows the October 8 context comparison's matched short-prompt matrix:
three prompt lengths (172, 557 and 1,069 formatted tokens), three repetitions
per prompt length, greedy decoding, and a 64-token output cap. At 1,024 context,
the 1,069-token prompt is omitted because prompt plus output does not fit. Each
capacity starts a fresh loopback server. There is no separate warmup; file cache
state carries naturally between cells, and prompt caching is disabled. The
prompt text and token counts match the reference workload. Streaming was used
to measure client time to the first nonempty output delta (TTFT); the October 8
responses were non-streaming and did not report TTFT.

Within each model, only `--max-context` changed between capacities. The
current candidate's qualified settings remain in place: FP16 KV, MTP off,
3,000 requested expert-cache slots, prefill chunk 128, eight workers, mapped
experts, 3,072 MiB workspace reserve and prompt cache off. Each model retains
its existing expert profile and model paths; realized cache sizes are recorded
in the per-cell configs and engine logs. This measures context capacity under
the current port's fixed selected profile, rather than changing cache size to
fit each capacity.

The October 8 sweep used the same Coder IQ1_M revision, prompt lengths, output
length and capacity points, but used MTP spec 4 and automatic expert-cache
sizing. Thus the workload matrix matches and the current-port profile is
explicit, but this is not a same-day paired engine-version test or a causal
speedup comparison. The table below compares capacity effects within each
current model/profile. The three variants are different artifacts; do not use
their absolute differences as quantization effects.

Rates are engine-reported medians; TTFT is client-measured. Each tuple is
**prompt tok/s / decode tok/s / TTFT seconds**. Each cell has three
within-process repetitions; min–max values are in [`summary.json`](summary.json)
and every request, output hash, config, server log and memory sample is in
[`campaign/`](campaign/). These three repetitions are descriptive, not
independent-process confidence intervals.

## Coder IQ1_M

| Configured context | Min available GiB | 172-token prompt: PP / TG / TTFT | 557-token prompt: PP / TG / TTFT | 1,069-token prompt: PP / TG / TTFT |
| ---: | ---: | ---: | ---: | ---: |
| 1,024 | 14.20 | 42.5 / 15.9 / 4.2 | 58.2 / 15.8 / 9.8 | — |
| 2,048 | 14.37 | 43.5 / 15.9 / 4.2 | 58.9 / 15.9 / 9.7 | 66.1 / 15.5 / 16.4 |
| 4,096 | 14.16 | 44.3 / 16.0 / 4.1 | 60.5 / 16.1 / 9.4 | 66.2 / 15.6 / 16.4 |
| 8,192 | 14.25 | 44.0 / 16.1 / 4.1 | 60.6 / 16.0 / 9.4 | 66.1 / 15.6 / 16.4 |
| 16,384 | 13.96 | 44.1 / 16.1 / 4.1 | 60.8 / 16.1 / 9.4 | 66.4 / 15.7 / 16.3 |
| 32,768 | 13.61 | 44.4 / 15.9 / 4.1 | 61.1 / 15.9 / 9.3 | 66.3 / 15.6 / 16.3 |
| 65,536 | 12.67 | 43.1 / 16.1 / 4.2 | 60.4 / 16.0 / 9.4 | 65.2 / 15.6 / 16.6 |
| 131,072 | 11.10 | 30.4 / 14.4 / 5.9 | 52.6 / 15.5 / 10.9 | 58.9 / 14.4 / 18.4 |
| 262,144 | 8.11 | 16.0 / 11.6 / 11.2 | 30.8 / 11.6 / 18.4 | 42.0 / 10.3 / 25.9 |

## Coder Q2_0

| Configured context | Min available GiB | 172-token prompt: PP / TG / TTFT | 557-token prompt: PP / TG / TTFT | 1,069-token prompt: PP / TG / TTFT |
| ---: | ---: | ---: | ---: | ---: |
| 1,024 | 17.84 | 22.7 / 10.6 / 7.9 | 37.6 / 11.7 / 15.1 | — |
| 2,048 | 17.91 | 30.5 / 11.6 / 6.0 | 45.1 / 11.7 / 12.7 | 50.4 / 12.7 / 21.5 |
| 4,096 | 18.11 | 30.9 / 12.4 / 5.9 | 45.7 / 11.6 / 12.5 | 51.0 / 12.7 / 21.3 |
| 8,192 | 17.99 | 30.9 / 11.8 / 5.9 | 45.0 / 11.4 / 12.7 | 51.1 / 12.7 / 21.2 |
| 16,384 | 17.81 | 30.1 / 11.9 / 6.0 | 45.6 / 11.6 / 12.5 | 50.9 / 12.6 / 21.3 |
| 32,768 | 17.36 | 29.8 / 11.7 / 6.1 | 44.6 / 11.5 / 12.8 | 50.3 / 12.5 / 21.6 |
| 65,536 | 16.51 | 28.5 / 11.5 / 6.3 | 43.6 / 11.3 / 13.1 | 48.1 / 12.1 / 22.5 |
| 131,072 | 14.94 | 18.9 / 11.2 / 9.4 | 36.3 / 10.0 / 15.7 | 41.0 / 10.0 / 26.5 |
| 262,144 | 11.66 | 11.5 / 7.6 / 15.4 | 22.5 / 7.5 / 25.4 | 30.1 / 7.9 / 36.0 |

## Original ISTA-DASLab IQ3_S

| Configured context | Min available GiB | 172-token prompt: PP / TG / TTFT | 557-token prompt: PP / TG / TTFT | 1,069-token prompt: PP / TG / TTFT |
| ---: | ---: | ---: | ---: | ---: |
| 1,024 | 13.41 | 8.6 / 6.9 / 20.6 | 16.7 / 7.0 / 34.1 | — |
| 2,048 | 13.46 | 9.1 / 6.9 / 19.5 | 16.3 / 6.5 / 35.0 | 21.4 / 6.7 / 51.1 |
| 4,096 | 13.38 | 9.0 / 6.8 / 19.8 | 16.0 / 6.9 / 35.8 | 21.3 / 6.7 / 51.3 |
| 8,192 | 13.30 | 9.2 / 6.7 / 19.4 | 15.8 / 6.7 / 36.2 | 21.5 / 6.6 / 50.9 |
| 16,384 | 12.99 | 9.2 / 6.7 / 19.2 | 15.8 / 6.8 / 36.1 | 21.1 / 6.7 / 51.4 |
| 32,768 | 12.55 | 9.0 / 6.8 / 19.7 | 15.8 / 6.7 / 36.2 | 21.3 / 6.5 / 51.4 |
| 65,536 | 11.68 | 8.3 / 6.5 / 21.6 | 14.9 / 6.4 / 38.5 | 20.5 / 6.6 / 53.3 |
| 131,072 | 10.23 | 7.0 / 6.3 / 25.4 | 13.8 / 6.5 / 41.3 | 19.4 / 6.3 / 56.2 |
| 262,144 | 7.16 | 6.3 / 5.5 / 28.5 | 8.8 / 5.5 / 64.8 | 9.5 / 5.5 / 113.3 |

## Findings and limits

At 8K to 256K configured capacity, the median 557-token prompt rate fell by
49% for Coder IQ1_M (60.6 to 30.8 tok/s), 50% for Coder Q2_0 (45.0 to 22.5),
and 44% for original IQ3_S (15.8 to 8.8). Its TTFT increased from 9.4 to 18.4
seconds, 12.7 to 25.4 seconds, and 36.2 to 64.8 seconds, respectively.
The 1,069-token prompt shows similar capacity costs at 256K: prompt throughput
was 42.0 / 30.1 / 9.5 tok/s and TTFT 25.9 / 36.0 / 113.3 seconds for IQ1_M,
Q2_0 and IQ3_S. These are medians of three requests per cell, not causal
cross-quantization effects.

Minimum system `MemAvailable` was 8.11 GiB for IQ1_M, 11.66 GiB for Q2_0 and
7.16 GiB for IQ3_S. The six-GiB admission floor was preserved in every cell;
maximum observed swap use was 2.91, 2.91 and 3.69 GiB, respectively. The
28-GiB per-cell runtime cgroup recorded zero low/high/max/OOM events. These
numbers describe Orin's single physical memory pool; host RAM and CUDA capacity
are not added. CPU clocks were observed dynamically from 729.6 to 2,201.6 MHz,
GPU clocks from 306 to 1,300.5 MHz; EMC clock readback was unavailable. No
clock setting was changed. Energy was not measured; raw tegrastats is retained
for inspection but is not process-attributed energy.

These are short prompts at larger reserved context capacities. They do not
measure prefill of a prompt that actually occupies 64K–256K tokens, nor do they
test recall quality near those limits. The October 8 report's separate
near-limit prompts are not included in this matrix. The relevant model and
profile identities are in the prior [Coder IQ1_M](../2026-10-24-coder-iq1m-current-candidate-performance/artifacts.json),
[Q2_0](../2026-10-25-q2-current-candidate-performance/artifacts.json) and
[IQ3_S](../2026-10-24-iq3s-current-candidate-performance/artifacts.json)
campaign manifests. No weights, packs or build products are in this result
directory.
