# Q2_0 backend comparison at 4K cache, pp2048+tg128

Date: 2026-10-31. Device: Jetson AGX Orin Developer Kit (aarch64, SM87,
CUDA 12.6). This three-pair screen compares Strata with strict NInfer on the
same held-out 2,048-token retrieval/arithmetic prompt. Both used a 4,000-slot
expert cache, 8K configured context, prefill chunk 128, MTP window 2, eight
pool workers, adaptive swaps, a 6 GiB resident budget and separate 3 GiB
workspace reserve. PCIe staging and prompt cache were off. The only server
setting changed was `--expert-backend`; the NInfer arm used
`--expert-backend-strict`. Experimental CTA and exact-entry toggles were off.
Each process issued one warmup and one measured request, with counterbalanced
order Strata→NInfer, NInfer→Strata, Strata→NInfer.

The measured prompt was exactly 2,048 tokens. The generation cap was 128, but
the task naturally stopped after 47 tokens. All six measured responses
matched the exact expected string:

`EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768`

## Results

Positive advantage means higher throughput or lower latency. The intervals are
95% percentile bootstrap intervals over the three paired process effects
(100,000 resamples); three pairs provide screening uncertainty only.

| Metric | Strata median | Strict NInfer median | NInfer paired advantage (95% interval) |
| --- | ---: | ---: | ---: |
| Prompt throughput | 41.5 tok/s | 42.1 tok/s | +2.14% (−0.24%, +16.62%) |
| Decode throughput | 8.7 tok/s | 8.8 tok/s | **0.00% (−2.47%, +1.15%)** |
| First-visible TTFT | 49.86 s | 49.21 s | +2.24% (−0.34%, +16.26%) |
| Client total | 54.81 s | 54.58 s | +1.98% (−0.15%, +14.63%) |

Decode TPS is the primary metric for this expert execution path. Its paired
median is tied and all pair effects are within about 2.5% in either direction;
this screen does not meet the 5% useful-effect gate. Prompt/TTFT/client medians
favor NInfer slightly, but their wide three-pair intervals include zero and
are dominated by the first pair's larger difference. Do not run seven-pair
service confirmation for this cell. The result offers no request-level support
for promoting the exact-entry grouped operator specialization.

## Resources and limits

Minimum sampled available RAM was 10.17 GiB, above the six-GiB host floor and
separate workspace reserve. Peak sampled swap was 6.38 GiB; sampled OOM kills
were zero. CPU observations ranged 729.6–2,201.6 MHz and GPU observations
306–1,300.5 MHz. EMC readback was denied; clocks remained dynamic and energy
was not measured. Per-pair values, hashes, model/binary identity and resource
observations are in [`paired-summary.json`](paired-summary.json). Raw prompt
and response payloads remain outside the repository.
