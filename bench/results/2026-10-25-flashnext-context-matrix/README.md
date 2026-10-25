# Qwen3.8-Flash-Next cross-variant context matrix

This report consolidates the existing current-candidate Strata performance
campaigns for the three Flash-Next variants requested for later port
comparison. It adds no new inference runs. Each campaign used the same two
NInfer workload shapes, seven independent fresh server processes, an 8,192
configured context, and one warmup plus one measured request per shape in each
process. Context size in the workload column means the exact prompt length;
the configured context capacity was 8,192 tokens for all three campaigns.

## Results

Rates are campaign medians. Prompt and generated rates are engine-reported;
TTFT is client time to the first nonempty streamed content delta. The source
reports contain bootstrap intervals, full-request latency, memory, clocks,
artifact identity and raw per-process observations.

| Variant | Prompt + output tokens | Prompt tok/s | Generated tok/s | Client TTFT (s) | Campaign |
| --- | ---: | ---: | ---: | ---: | --- |
| Coder IQ1_M | 512 + 64 | 65.2 | 16.0 | 7.93 | [7-block report](../2026-10-24-coder-iq1m-current-candidate-performance/README.md) |
| Coder IQ1_M | 2,048 + 128 | 68.5 | 15.9 | 29.97 | [7-block report](../2026-10-24-coder-iq1m-current-candidate-performance/README.md) |
| Coder Q2_0 | 512 + 64 | 32.6 | 10.2 | 15.88 | [7-block report](../2026-10-25-q2-current-candidate-performance/README.md) |
| Coder Q2_0 | 2,048 + 128 | 54.2 | 10.4 | 37.97 | [7-block report](../2026-10-25-q2-current-candidate-performance/README.md) |
| Original Flash-Next IQ3_S | 512 + 64 | 13.1 | 5.7 | 40.06 | [7-block report](../2026-10-24-iq3s-current-candidate-performance/README.md) |
| Original Flash-Next IQ3_S | 2,048 + 128 | 22.1 | 6.3 | 93.46 | [7-block report](../2026-10-24-iq3s-current-candidate-performance/README.md) |

## Scope and comparison limits

The two prompt/output shapes align with the NInfer short and long workload
cells (`pp512+tg64` and `pp2048+tg128`). The Strata results are separate
single-candidate campaigns collected on October 24–25, 2026, not same-day
paired runs. Do not interpret differences between quant variants as causal
quantization effects. These rows also do not establish an engine speedup over
NInfer: the NInfer records use a different model artifact/runtime format, and
the Flash-Next GGUFs in this table have not been run through NInfer. A future
port comparison needs a model/format that both runtimes can load, matched
hardware state, workload and measurement protocol. Until then this matrix is
a Strata-side reference for the later report.

The original IQ3_S is the non-Coder `ISTA-DASLab/Qwen3.8-Flash-Next` model;
Coder IQ1_M and Q2_0 are from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`. These are different
model artifacts as well as different quantizations.
