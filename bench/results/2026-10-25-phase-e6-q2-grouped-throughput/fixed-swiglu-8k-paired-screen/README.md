# Corrected-kernel 8K natural-generation screen

Date: 2026-10-25. Three independent randomized Strata/NInfer process pairs
screened the five planned natural-generation request shapes at an 8K context
cap. Each service received one warmup and one measured request for each shape.
The Coder Q2_0 model, 3,000-slot resident profile, MTP off, FP16 KV, prefill
128 and eight workers were held fixed. All 60 eligible API/token-count checks
passed. All 15 measured output hashes matched their paired control, and all six
resident maps had SHA256
`a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`.

Negative paired changes mean NInfer was faster. TTFT and client completion are
percentage latency changes; prompt/decode are percentage throughput changes.
Each cell has only three pairs, so the values below are a screening result, not
a performance estimate or confirmation interval.

| Request | TTFT changes (pairs 1/2/3) | Median TTFT | Client changes (pairs 1/2/3) | Median client | Median prompt TPS | Median decode TPS |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| 512 + 64 | +0.74 / −0.01 / −1.25% | −0.01% | −0.48 / −0.34 / −1.60% | −0.48% | 0.00% | +1.79% |
| 2,048 + 128 | −1.59 / −1.84 / +0.24% | −1.59% | −1.77 / +6.77 / +0.05% | +0.05% | +1.48% | +0.98% |
| 172 + 64 | −6.37 / −0.71 / +0.89% | −0.71% | −4.42 / −0.52 / +0.50% | −0.52% | +0.53% | +0.94% |
| 557 + 64 | +0.21 / −1.63 / +1.99% | +0.21% | −0.09 / −1.58 / +0.94% | −0.09% | −0.25% | +1.72% |
| 1,069 + 64 | −0.43 / −1.11 / −0.70% | −0.70% | −0.33 / −1.10 / −0.75% | −0.75% | +0.62% | +0.84% |

No workload reached the predeclared 5% useful-effect threshold at the median,
so no seven-pair confirmation was run. The 172+64 cell's first-pair TTFT gain
did not reproduce in the other pairs. The 2,048+128 cell had one NInfer decode
outlier: decode time was 32.6% above its paired Strata result, while TTFT was
1.84% faster and output hashes still matched. Its median client change was
near zero. This variability and the small sample do not support a performance
claim.

The minimum available physical/admission memory across the six services was
19,116,556,288 bytes (17.80 GiB), above the six-GiB host-headroom floor and
separate three-GiB workspace reserve. GPU clock samples were read-only and
dynamic; the initial readback was 306 MHz. EMC readback was unavailable, and
energy was not attributed. The server binary SHA256 was
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75`.

Raw three-pair data and per-process logs, residency maps, API checks and
supervisor telemetry are in [`pair-1/`](pair-1/), [`pair-2/`](pair-2/) and
[`pair-3/`](pair-3/). Reproduce each pair with
`run_context_matrix.py --contexts 8192`, using seeds 20261025, 20261026 and
20261027 respectively.
