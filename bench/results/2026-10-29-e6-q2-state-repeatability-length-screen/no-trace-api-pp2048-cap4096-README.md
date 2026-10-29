# No-trace API screen: Q2_0 pp2048+tg128 at 4K capacity

Date: 2026-10-29, Jetson AGX Orin. Model: Qwen3.8-Flash-Next GSQ-RCO
Q2_0, 3,000 expert slots, six-GiB resident budget, 3-GiB workspace reserve,
MTP-2, prefill 128, eight workers. Configured context was 4,096 tokens; PCIe
staging was disabled (`--pcie-frac 0`) in both arms. Prompt cache was disabled.
Source revision: `5c94944c6f98869fd8b9d1cb6c0ac3f25bfbe784`; binary SHA-256:
`fbd40926be198adc92cd9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`.

Three same-day process pairs used randomized order, one warmup and one measured
request per process. The baseline used Strata's expert backend; the candidate
used strict NInfer. Tracing was disabled. Each measured request completed 2,048
prompt and 128 generated tokens. Candidate percentage is relative to baseline;
positive TPS is faster, while positive TTFT or client-time change is slower.

| Block | Order | Prompt TPS | Decode TPS | First-visible TTFT | Client total | Measured content equal |
|---|---|---:|---:|---:|---:|---|
| 0 | NInfer → Strata | +4.48% | -4.30% | -4.39% | -2.34% | Yes |
| 1 | Strata → NInfer | +0.62% | +0.00% | -0.53% | -0.39% | Yes |
| 2 | Strata → NInfer | +6.11% | +47.62% | -6.13% | -14.10% | Yes |
| Median paired change |  | **+4.48%** | **+0.00%** | **-4.39%** | **-2.34%** | 3/3 |

The paired bootstrap 95% median intervals from these three blocks were
+0.62% to +6.11% prompt TPS, -4.30% to +47.62% decode TPS, -6.13% to -0.53%
TTFT, and -14.10% to -0.39% client time. The single +47.62% decode result
coincided with a notably slower Strata baseline (6.3 versus 9.2–9.3 decode
tokens/s in the other blocks); it did not repeat. Although TTFT improved in all
three pairs, its -4.39% median is below the 5% useful-effect threshold; prompt
TPS is also below threshold, and decode TPS is tied at the median. No seven-pair
confirmation is indicated. Warmup and measured content matched across arms in
each pair. This is not an independent task-quality oracle, and persistent-state
fingerprints were not captured in this timing-only run.

Minimum available physical memory across the six arms was 11.58–11.63 GiB,
with zero OOM kills. GPU clocks varied from 306 to 1,300.5 MHz across the
observed process windows; CPU/GPU clocks were read-only and dynamic, and EMC
clock access was unavailable. Energy was not measured. This is a three-pair
screen for one synthetic workload, not product-performance qualification. Raw
campaign files and supervisor telemetry remain local-only.
