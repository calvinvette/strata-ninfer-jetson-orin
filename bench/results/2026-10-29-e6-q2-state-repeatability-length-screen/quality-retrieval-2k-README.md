# Held-out retrieval and state check: Q2_0 pp2048 at 4K capacity

Date: 2026-10-29, Jetson AGX Orin. Model: Qwen3.8-Flash-Next GSQ-RCO
Q2_0, MTP-2, 3,000 expert slots, six-GiB resident budget, 3-GiB workspace
reserve, prefill 128, eight workers. The exact-length 2,048-token fixture places
three retrieval markers at 10%, 50%, and 90% and asks for their codes and the
sum of their numeric suffixes. Configured capacity was 4,096; PCIe staging was
disabled in both arms.

One fresh-process pair compared Strata's expert backend with strict NInfer.
Both returned the exact expected answer:

`EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768`

All 47 generated token IDs, all nine persistent-state fingerprints, and the
residency hash matched. The supervisor passed with minimum available RAM of
11.76 GiB and zero OOM kills. This is one task/prompt functional check, not a
general quality contract. The trace/state instrumentation makes its rates
diagnostic only: Strata/NInfer measured 35.30/34.97 prompt tokens/s and
5.341/5.325 decode tokens/s (about -0.92%/-0.30% for NInfer). TTFT and energy
were not measured; clocks were dynamic. Raw captures and telemetry remain
local-only.
