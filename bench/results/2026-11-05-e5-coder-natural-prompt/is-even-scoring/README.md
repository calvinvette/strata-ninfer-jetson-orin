# Coder IQ1_M teacher-forced `is_even` scoring — Orin — 2026-11-05

This follow-up scores the exact 21-token `is_even(n)` answer that both
backends generated and that passed six executable cases. The answer was
teacher-forced after its exact 44-token chat prompt, producing coverage for all
64 next-token targets. Both runs used the canonical Coder expert profile,
3,000 cache setting, strict NInfer, MTP-2, context 512 and short-read 512.

The Strata and NInfer score files were byte-identical (SHA-256
`beb63d047ac99253298d592fd04aa30faad6f3669c13179237644d299cb63c89`). For all
21 answer tokens, total log probability was `-0.122645558`, mean
`-0.005840265`, and perplexity `1.005857`; target log-probability deltas were
zero, top-1 agreement was 100%, and top-10 overlap was 100%. Each backend logged
117 resident hits from 480 expert lookups; the remaining expert work followed
Strata fallback.

The supervisor passed in 60.8 seconds. Minimum host/admission availability was
14.67 GiB; sampled swap peaked at 1.64 GiB, and the pre-existing OOM-kill
counter stayed at one. Clocks were observed dynamically, EMC readback was
unavailable, and energy was not measured. Scoring instrumentation and probe
request timing are excluded from performance claims. This is a second bounded
sequence with exact score parity; it does not establish general model-quality
or persistent-state tolerance. Raw logs and telemetry remain in the adjacent
local run/supervisor directories.

See the [`is_prime` scoring report](../is-prime-scoring/README.md) for the
other teacher-forced sequence and the integration status for remaining gates.
