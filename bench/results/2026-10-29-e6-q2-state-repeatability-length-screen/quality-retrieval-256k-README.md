# Q2_0 256K exact retrieval and state check

Date: 2026-10-29
Device: Jetson AGX Orin 64GB
Model: Qwen3.8 Flash Next Q2_0, same two GGUF shards, PLE pack and expert profile in both arms
Binary: `/tmp/strata-e6-boundary-build/strata` (local qualified build)

## Result

One fresh-process Strata/strict-NInfer pair consumed the same 256,000-token
held-out retrieval/arithmetic prompt with a 262,144-token context cap and PCIe
expert staging disabled. Both returned the exact expected answer:

```text
EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768
```

The pair matched all 47 generated token IDs, all nine persistent-state
fingerprints (`L`, GDN, PLE, tail, dead, pooled, pooled-full, KV and previous
PLE), and the residency hash. There were no checker failures.

| Arm | Prompt time | Prompt rate | Decode time | Decode rate |
| --- | ---: | ---: | ---: | ---: |
| Strata expert backend | 2,568.339 s | 99.68 tok/s | 12.103 s | 3.88 tok/s |
| Strict NInfer expert backend | 2,565.728 s | 99.78 tok/s | 11.868 s | 3.96 tok/s |

This single pair implies about +0.10% NInfer prompt throughput and +1.98%
decode throughput. It is a functional near-limit result, not performance
confirmation: the small differences are within the scope of one unreplicated
pair. The total supervised command took 5,345.5 s (about 89 minutes).

The supervisor sampled a minimum of 7.04 GB (6.56 GiB) available RAM during
its guarded window, 0.56 GiB above the required 6 GiB floor. Peak sampled swap
use was 6.32 GiB. Sampled cgroup low/high/max/OOM/OOM-kill counters remained
zero, and no memory-pressure abort occurred. Clock observations were dynamic; EMC readback was
unavailable and energy was not measured. No clocks or services were changed.

This adds one exact retrieval/recovery-size correctness cell at 256K. It does
not establish broad 256K quality, sustained-service behavior, or a performance
advantage. The checker also has nine final-state fingerprints; this test did
not capture an accepted-prefix state trace. E6 and E7 remain open.

## Reproduction notes

The full prompt fixture and execution captures remain local and are not part of
Git. A preliminary preflight with an incorrectly small context cap was rejected
before inference; the recorded result is from the corrected 262,144-cap run.
The model files remain under `~/models/` and were not copied into the project.
