# Q2_0 staged-complement size screen

Date: 2026-10-25. Orin AGX, current qualified CUDA build, Q2_0 Coder
artifact, 8K context, 3,000 GPU resident slots, `--pcie-frac 1.0`, MTP-2,
128-token prefill, 8 workers. Three randomized paired CPU-miss versus
strict-NInfer staged requests were run at each complement size. Every process
within a size used the same resident-map hash. The measured request used a
55-token prompt and 29-token output. This is a screening test, not a release
qualification.

| Complement | Staged entries/request | Client latency, median paired change | TTFT, median paired change | Output hashes | Minimum available memory |
| ---: | ---: | ---: | ---: | --- | ---: |
| 1 GiB | 265 / 13,920 (1.9%) | −1.32% | −1.19% | all three differ | 16.21 GiB |
| 2 GiB | 537 / 13,920 (3.9%) | −1.00% | −1.62% | all three match | 15.39 GiB |
| 4 GiB | 922 / 13,920 (6.6%) | −3.29% | −3.80% | all three differ | 13.36 GiB |
| 6 GiB | 1,364 / 13,920 (9.8%) | −4.09% | −6.05% | all three match | 11.36 GiB |

Negative latency change means the staged NInfer arm completed sooner. The
6-GiB screen crosses the 5% TTFT screening threshold, but client completion
improved by less than 5%. The 6-GiB run maintained the six-GiB physical floor
and the separate three-GiB workspace reserve. GPU frequency was observed at
306 MHz during the supervised run; EMC frequency was unavailable, and energy
was not attributed. Warmup hashes differed in the first 6-GiB pair, while all
three measured hashes matched.

## Held-out functional check at 6 GiB

The 512-token retrieval/arithmetic fixture returned the exact expected answer
from both Strata and strict NInfer, and all 47 generated token IDs matched.
However, the final state fingerprints differ in `gdn`, `tail`, `pooled`,
`pooled_full`, and `kv`. The check therefore fails its persistent-state parity
requirement. Prompt processing used 31.668 s for Strata and 31.127 s for
NInfer; decode used 8.339 s and 8.525 s respectively. This single task is not
a broad quality oracle, but its state mismatch blocks a confirmation run and
any promotion of the 6-GiB setting.

## Evidence

- [1-GiB screen](../2026-10-25-phase-e3-q2-ninfer-max-offload/README.md)
- [2-GiB raw results](../2026-10-25-phase-e3-q2-ninfer-complement2g-max-offload/staged-screen/results.json)
- [4-GiB raw results](../2026-10-25-phase-e3-q2-ninfer-complement4g-max-offload/staged-screen/results.json)
- [6-GiB raw results](../2026-10-25-phase-e3-q2-ninfer-complement6g-max-offload/staged-screen/results.json)
- [6-GiB quality results](../2026-10-25-phase-e3-q2-ninfer-complement6g-quality/evidence/results.json)

All comparisons use the same model artifact and current executable on one day.
The output-hash differences at 1 and 4 GiB have no independent quality
assessment. The matched hashes at 2 and 6 GiB do not establish numeric state
equivalence; the held-out 6-GiB check explicitly found state divergence.
