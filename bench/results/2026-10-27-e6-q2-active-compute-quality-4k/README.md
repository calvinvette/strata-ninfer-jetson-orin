# E6 active staged-compute held-out retrieval/state check at 4K

Date: 2026-10-27 (Orin AGX). Source: `a6f2c3dab62ed5f08bdeb31bce6f48c8118b6b18`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

This one-run-per-arm diagnostic compared Strata grouped compute and strict NInfer grouped compute with staging enabled in both. The Qwen3.8-Flash-Next GSQ-RCO Q2_0 profile used 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers, 8K configured context and `pcie-frac=1` in both arms. The exact-length 4,096-token held-out prompt planted three retrieval codes and required their ordered return plus the suffix sum `1768`.

| Check | Strata grouped | Strict NInfer grouped | Result |
|---|---|---|---|
| Exact expected answer | Pass | Pass | Same exact text |
| Generated tokens | 47 | 47 | Token IDs identical |
| Resident map | Same 3,000-slot map | Same 3,000-slot map | SHA-256 `a02fd81e…` in both |
| Persistent state | All 9 fields captured | All 9 fields captured | Every field identical |
| Minimum available RAM | 11.62 GiB across both runs | — | Above 6-GiB floor |

The checker exited successfully with no failures. This extends the bounded task-quality and final-state evidence for the active staged-compute path from 2K to 4K prompt tokens. The arms were sequential and traced, so this is a correctness diagnostic, not performance data. It does not qualify arbitrary natural generation, near-limit context, or other model/profile combinations. Supervisor telemetry sampled clocks without changing them; energy was not measured.

Reproduce by generating an exact fixture using `python3 tools/integration/prepare_ninfer_long_retrieval.py --tokens 4096 --output <new-output-dir>`, then run `tools/integration/ninfer_q2_retrieval_check.py` under `tools/integration/run_control.py` with `--compare-staged-backends --run`, using the Q2_0 config and engine noted in the 2K [reproduction instructions](../2026-10-27-e6-q2-active-compute-quality-2k/README.md).

Raw fixture, engine traces, resident maps and supervisor samples remain local in this directory; model weights and build products remain outside Git.
