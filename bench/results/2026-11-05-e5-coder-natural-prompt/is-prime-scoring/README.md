# Coder IQ1_M teacher-forced answer scoring — Orin — 2026-11-05

The 89-token `is_prime(n)` answer that Strata and strict NInfer had both
produced and passed against the 11-case executable oracle was appended to its
exact 50-token chat generation prefix. Each backend then teacher-forced the
same 139-token sequence through the service verifier with `STRATA_LOGPOS` and
top-20 capture. The canonical `data/expert-profile-coder.bin` and a 3,000-slot
cache were used; the diagnostic score rows cover all 138 next-token targets,
including all 89 generated sequence tokens (the end-of-turn token is included
in that count).

The serialized score files were byte-identical (SHA-256
`1d44a08b8263f49f8ed7abe4d06e203a06be2fab508248478f4a5ca36ad69eac`). For the
89 answer tokens, both had total log probability `-1.105776162`, mean
`-0.01242445`, and perplexity `1.012502`; target-token log-probability deltas
were zero, top-1 agreement was 100%, and mean top-10 overlap was 100%. The
requests logged 109/480 resident hits/lookups per backend. This is a bounded
teacher-forced scoring result; the remaining route work followed Strata's
fallback path, and the result does not qualify all routed experts or establish
a general model-quality tolerance.

The supervisor passed in 121.0 seconds. Minimum host/admission availability
was 14.66 GiB, sampled swap peaked at 1.64 GiB, and the pre-existing OOM-kill
counter stayed at one. Clocks were observed dynamically; EMC readback was
unavailable and energy was not measured. Scoring instrumentation and the single
probe-token timings are excluded from performance claims.

A prior run with a 391-slot single-layer diagnostic profile also produced
byte-identical scoring records, but covered only 15/480 resident hits; that
limited screen is retained separately in [`results.json`](results.json). The
standard profile run is the primary result. The current comparison helper is
[`run_is_prime_scoring_pair.py`](../run_is_prime_scoring_pair.py); full score
files and raw telemetry remain local in the adjacent run directories.
