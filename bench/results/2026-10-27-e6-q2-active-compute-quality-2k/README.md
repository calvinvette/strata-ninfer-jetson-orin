# E6 active staged-compute held-out retrieval/state check at 2K

Date: 2026-10-27 (Orin AGX). Source: `aed2bb115b6de4e32390c1e47a52ff5b54c67dda`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

This one-run-per-arm diagnostic compared Strata grouped compute and strict NInfer grouped compute with staging enabled in both. The Qwen3.8-Flash-Next GSQ-RCO Q2_0 profile used 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers, 8K configured context and `pcie-frac=1` in both arms. The exact-length 2,048-token held-out prompt planted three retrieval codes and required their ordered return plus a suffix sum. The expected answer was fixed before execution: `EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768`.

| Check | Strata grouped | Strict NInfer grouped | Result |
|---|---|---|---|
| Exact expected answer | Pass | Pass | Same exact text |
| Generated tokens | 47 | 47 | Token IDs identical |
| Resident map | Same 3,000-slot map | Same 3,000-slot map | Hashes identical |
| Persistent state | All 9 fields captured | All 9 fields captured | Every field identical |
| Minimum available RAM | 11.59 GiB across both runs | — | Above 6-GiB floor |

The checker exited successfully with no failures. This is bounded task-quality and final-state evidence for one held-out retrieval task on the active staged-compute path. Runs were sequential, not randomized timing pairs; no performance conclusion is drawn. It does not qualify arbitrary natural generation, other prompt lengths, or near-limit context. Supervisor telemetry sampled clocks without changing them; energy was not measured.

Reproduction: regenerate the fixture with `python3 tools/integration/prepare_ninfer_long_retrieval.py --tokens 2048 --output <new-output-dir>`, then run the command below under the integration memory supervisor. Use the Q2_0 configuration and current qualified engine binary; `--compare-staged-backends` forces both arms to staged residency and checks answer, token IDs, all nine state fields and residency.

```sh
python3 tools/integration/run_control.py --output <supervisor-dir> --timeout 3600 --interval 1 --sample-clocks -- \
  python3 tools/integration/ninfer_q2_retrieval_check.py \
  --config bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/config.json \
  --engine build/integration/e0-cuda-build/strata \
  --workload <new-output-dir>/workload.json \
  --output <run-dir> --compare-staged-backends --run
```

Raw workload, logs, residency CSVs and supervisor samples remain local in this report directory; models and build products remain outside Git.
