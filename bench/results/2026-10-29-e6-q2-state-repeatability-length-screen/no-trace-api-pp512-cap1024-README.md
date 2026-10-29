# No-trace API screen: Q2_0 pp512+tg64 at 1K capacity

Date: 2026-10-29, Jetson AGX Orin. Model: Qwen3.8-Flash-Next GSQ-RCO
Q2_0, 3,000 expert slots, six-GiB resident budget, 3-GiB workspace reserve,
MTP-2, prefill 128, eight workers. Configured context was 1,024 tokens; PCIe
staging was disabled (`--pcie-frac 0`) in both arms. Prompt cache was disabled.
Source revision: `5c94944c6f98869fd8b9d1cb6c0ac3f25bfbe784`; binary SHA-256:
`fbd40926be198adc92cd9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`.

Three same-day process pairs used randomized order, one warmup and one measured
request per process. The baseline used Strata's expert backend; the candidate
used strict NInfer. Instrumentation/tracing was disabled for the measured runs.
Each measured request completed 512 prompt and 64 generated tokens. Candidate
percentage is relative to baseline; positive TPS is faster, while positive TTFT
or client-time change is slower.

| Block | Order | Prompt TPS | Decode TPS | First-visible TTFT | Client total | Measured content equal |
|---|---|---:|---:|---:|---:|---|
| 0 | Strata → NInfer | -1.96% | +2.33% | +2.60% | +0.99% | Yes |
| 1 | NInfer → Strata | -0.97% | -1.14% | +0.88% | +0.84% | Yes |
| 2 | Strata → NInfer | +1.31% | +1.16% | -1.27% | -1.39% | Yes |
| Median paired change |  | **-0.97%** | **+1.16%** | **+0.88%** | **+0.84%** | 3/3 |

The paired bootstrap 95% median intervals from these three blocks were
-1.96% to +1.31% prompt TPS, -1.14% to +2.33% decode TPS, -1.27% to +2.60%
TTFT, and -1.39% to +0.99% client time. No median reaches the predeclared 5%
useful-effect screen, so seven-block confirmation is not indicated. The exact
measured content and warmup content matched across arms in each block; this is
not an independent task-quality oracle, and this no-trace run did not capture
persistent-state fingerprints.

Minimum available physical memory across the six arms was 11.66–11.70 GiB,
with zero OOM kills. CPU/GPU clock observations were read-only and dynamic;
EMC clock access was unavailable. Energy was not measured. This is a three-pair
screen for one synthetic short workload, not product-performance qualification.
Raw campaign files and supervisor telemetry remain local-only.
