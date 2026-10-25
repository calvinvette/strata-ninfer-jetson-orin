# E5 Q2_0 strict NInfer 4K retrieval and arithmetic task

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. This functional
check extends the short retrieval task to an actual 4,096-token prompt under
strict NInfer execution.

## Setup and result

The held-out fixture placed three unique codes near 10%, 50% and 90% of a
4,096-token prompt. It asked for the ordered codes and sum of the numeric
suffixes. The exact answer was:

```
EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768
```

Fresh MTP-off and MTP-4 services used the same Q2_0 model/PLE pack, strict
`--expert-backend ninfer`, 3,000 static expert slots, 8K context, FP16 KV,
prefill 128, eight workers and adaptive swaps disabled. Both returned the exact
answer in 47 tokens. All output IDs and nine final state fingerprints matched.
MTP-4 offered 45 drafts and accepted 34.

Prompt-content SHA256 is
`9aa01309f45b707c17366c7a5447494ff6e4d4ed337e7e5033fa3444ded26ed4`; formatted
token-ID SHA256 is
`703a480c32f5a8edfc61cf061936a340228c9080a5c199c50213d69a81494a26`. The
workload SHA256 is
`6377157646a6c1e757191e189b5ff73d5e2f422365bebd0e1263451ee51611e6`. The
Release binary SHA256 is
`527d7833ac398b82368c37b1001ed1adfdd245730b28482a90fef28851161be8`.

## Resources and interpretation

The supervised run lasted 238.1 seconds. Minimum physical/admission availability
was 18,147,246,080 bytes (16.90 GiB), above the preserved 6 GiB floor. Sampled
cgroup low/high/max/OOM/OOM-kill events were zero. CPU clocks ranged from
729.6 MHz to 2.2016 GHz, and GPU clocks ranged from 306 MHz to 1.3005 GHz.
EMC readback was denied; clocks were observed, not controlled. Energy was not
attributed.

Single-run prompt/decode timings were 91.21/9.92 seconds for MTP off and
92.22/8.75 seconds for MTP-4. This functional pair was not randomized or
repeated and is not an MTP or NInfer effect estimate. Detailed outputs and usage
are in [`evidence/results.json`](evidence/results.json); supervision summary is
in [`evidence/supervisor-result.json`](evidence/supervisor-result.json). The
fixture and reproducible exact-length generator are retained alongside this
report. This qualifies one 4K static-residency retrieval/scoring case; it does
not qualify near-limit 8K ingestion, other tasks or adaptive residency.
