# Excluded direct CPU-order kernel probe

This follow-up is retained as a failed, unsupported diagnostic. It passed a raw
Coder IQ3_XXS/IQ4_NL expert blob to `moe_hit_grouped_s2_cpu_order`, a helper
whose fixed layout is packed Q2_0. The helper returned non-finite values; no
parity conclusion can be drawn. The corrected diagnostic scratch sizing did not
change that result. This is an invalid-format invocation, not evidence about
the service implementation. Large dequantized-weight dumps were removed; the
supervisor stdout, stderr, result and telemetry for both attempts remain.
