# E5 Q2_0 strict NInfer retrieval and arithmetic task

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. This is a functional
task check with the experimental strict NInfer expert backend; it is not a
performance comparison against Strata's expert kernels.

## Setup and result

The held-out 512-token retrieval fixture contains three independently placed
codes, at 10%, 50% and 90% of the prompt, and asks for their ordered values and
the sum of their suffixes. The exact answer was:

```
EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768
```

Prompt-content SHA256: `06f01bad0d5bee0536704e85177113ac5de64a3366a7c48caf7d15060668a06c`.
Formatted prompt-ID SHA256: `84500183f3c7f7ddc116a80f576b97fcea3d87cc490b81e5689722aac9aab9c9`.
The workload fixture SHA256 is `c80ade67777ad08470fb9bd61ffa75d294af64e7958af6e9e25792103970b9e7`.
The Release executable SHA256 is
`527d7833ac398b82368c37b1001ed1adfdd245730b28482a90fef28851161be8`.

Fresh services ran sequentially with MTP off and MTP-4. Both used the same
Q2_0 artifact and PLE pack, strict `--expert-backend ninfer`, 3,000 static
expert slots, 8K context, FP16 KV, prefill 128, eight workers, and adaptive
swaps disabled. Both returned the exact answer in 47 tokens. Token IDs and all
nine final persistent-state fingerprints matched. MTP-4 offered 45 drafts and
accepted 34.

One-run engine prompt/decode durations were 37.51/9.60 seconds with MTP off and
31.42/8.40 seconds with MTP-4. These are descriptive functional-run timings,
without warmup, randomization or repeated paired blocks, and do not estimate an
MTP or NInfer performance effect. Detailed outputs and usage are in
[`evidence/results.json`](evidence/results.json); the supervisor record is in
[`evidence/supervisor-result.json`](evidence/supervisor-result.json). The
fixture is copied to [`evidence/workload.json`](evidence/workload.json) with its
source attribution retained in this report.

## Resources and harness correction

The corrected supervised run lasted 122.3 seconds. Minimum physical/admission
availability was 18,184,417,280 bytes (16.94 GiB), above the preserved 6 GiB
floor. Sampled cgroup low/high/max/OOM/OOM-kill events were zero. CPU clocks
ranged from 729.6 MHz to 2.2016 GHz and GPU clocks from 306 MHz to 1.3005 GHz;
EMC readback was denied. Energy was not attributed.

The first harness attempt is retained in
[`evidence/initial-harness-attempt.json`](evidence/initial-harness-attempt.json).
It correctly found matching token IDs and state, but reported a false answer
mismatch because the tokenizer decoder included the terminal `<|im_end|>` token.
The harness now removes that protocol terminator before comparing visible text;
the complete supervised rerun passed. This parser correction does not change
the captured token IDs or engine path.

This covers one short retrieval-plus-arithmetic task for static strict NInfer
with MTP off/4. Long retrieval/scoring, other prompt distributions and adaptive
residency remain open in E5. No model files were copied or modified.
