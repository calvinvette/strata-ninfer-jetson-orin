# Corrected-kernel 6-GiB staged screen

Date: 2026-10-25. The grouped SwiGLU Q8_1 division was changed to the precise
expression used by Strata's grouped quantizer. This fresh screen reuses the
Q2_0 Coder model, 3,000 resident slots, 6-GiB complement, 3-GiB workspace
reserve, 8K context cap, MTP-2, 128-token prefill and 8 workers. Three
randomized CPU-miss / strict-NInfer pairs used the same resident-map hash.
Each arm processed a warmup and a measured short `1+1` request.
The model shards are `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf`
(37,623,740,192 bytes) and
`Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf` (28,800,138,432 bytes).

| Pair | Client completion change | TTFT change | Measured output hash |
| ---: | ---: | ---: | --- |
| 1 | −4.91% | −6.79% | match |
| 2 | −3.86% | −5.66% | match |
| 3 | −4.57% | −6.29% | match |
| Median paired change | −4.57% | −6.29% | all match |

Negative values mean staged NInfer completed sooner. The TTFT screen crossed
5%, while client completion improved by less than 5%. Minimum available
memory was 11.39 GiB. This is a screening set; seven-pair confirmation was
pre-registered separately after the exact-state quality check passed.

Raw service results and residency maps are in [`staged-screen/`](staged-screen/);
the supervised run has read-only memory and clock telemetry in `supervisor/`.
