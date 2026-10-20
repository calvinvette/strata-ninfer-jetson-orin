# Accepted-prefix 8 verifier and expert capture — Orin — 2026-10-20

This follow-up used the pinned Coder GGUF IQ1_M artifact at revision
`5348543e0147355ac9cbcb031184a3546350988e` and candidate binary
`14afd1a4b953e176a88d7812bddcdf2beb65944bb5795beaf0f37e5834a496aa`. Each
supervised service ran the same 512/2,048/512-token prompts and generated 64
tokens per request. At position 519, it captured layer-31 verifier routes,
expert contributions and combined output, plus layer-32 GDN intermediates.
This is a correctness localization; it makes no performance or task-quality
claim.

The accepted-prefix service trace first differs in adaptive persistent state
at zero-based prefix 8, after verifier position 519 accepted token 27,718.
Initial and recovery token IDs, expert IDs and router weights at layer 31 match.
The adaptive owner trace shows experts 76 and 22 moving from CPU to GPU between
the initial short request and recovery. The verifier expert rows isolate the
change to rank 2, expert 22: 2,559/2,560 values differ (relative L2
`1.31996e-4`, maximum absolute delta `2.53413e-5`). Expert 76's independent
same-input CPU/GPU oracle outputs are bit-identical; expert 22's differ in
2,559/2,560 values (relative L2 `1.31992e-4`). All other captured expert rows
and the shared-expert output are exact. The weighted combined MoE output
differs in 2,555/2,560 values (relative L2 `3.38419e-5`, maximum absolute delta
`3.14415e-6`).

At the following layer-32 boundary, the accepted-prefix route capture first
differs in the layer-32 dispatch input (relative L2 `1.42941e-5`), and the
layer-32 verifier GDN capture first differs in `x` (2,551/2,560 values,
relative L2 `1.04390e-5`). Its `qkv`, `h`, `z` and `gdn_out` fields remain
bit-identical; later fields differ. This agrees with the service's first
changed GDN state fingerprint at ordinal 24, which maps to model layer 32.
Delayed control has exact expert rows, combined MoE output and GDN intermediates
at the same position. The evidence strongly implicates the owner-dependent
layer-31 expert-22 arithmetic as the immediate source of the observed layer-32
input change. The verifier GDN intermediates do not contain the serving
session's before/after recurrence arrays, so they do not alone prove which
state write causes the persistent hash delta. A subsequent
[raw committed-state capture](../adaptive-state-prefix8-committed-raw/README.md)
confirmed that the serving layer-32 recurrent matrix first differs at accepted
position 519, while its convolution history remains exact; the raw layer hash
matches the per-layer fingerprint in the same service log.

Both 28-GiB supervisors passed with zero sampled cgroup low/high/max/OOM/OOM-kill
events. Minimum host/admission availability was 14.24 GiB for adaptive and
14.19 GiB for delayed control. The runs took 310.8 and 307.8 seconds, with
dynamic clocks and no request-attributed energy. Raw captures and comparator
outputs are retained under each arm. The single-input expert oracle records,
CPU/GPU outputs and activation are under
`../operator-checks/layer31-position519/`; dequantized weight dumps were
discarded because the pinned GGUF is the source of truth.

Reproduce the paired capture from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261034 --continuations 0 --generated-tokens 64 \
  --capture-verify-moe-layer 31 --verify-moe-positions 519 \
  --capture-verify-gdn-layer 32 --verify-gdn-positions 519 \
  --output /tmp/coder-prefix8-verifier

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_layer25_verifier_parts.py \
  --run /tmp/coder-prefix8-verifier/adaptive-cap8/result --layer 31 --positions 519 \
  --output /tmp/coder-prefix8-verifier/adaptive-layer31.json

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_layer26_gdn_intermediates.py \
  --run /tmp/coder-prefix8-verifier/adaptive-cap8/result --layer 32 --positions 519 \
  --output /tmp/coder-prefix8-verifier/adaptive-gdn32.json
```

The comparator commands also pass on the delayed-control result. Adaptive
migration remains opt-in and Phase 5 remains open pending accepted-state write
isolation and broader supported-format coverage.
