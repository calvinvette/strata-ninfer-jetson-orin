# E6 active staged-compute held-out retrieval/state check at 8K

Date: 2026-10-27 (Orin AGX). Source: `fbeac91615cb2a8c9d0833431ae90f1abe734a4b`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

This one-run-per-arm diagnostic compared Strata grouped compute with strict NInfer grouped compute, with staging enabled in both. Model/profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0; 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers, 16K configured context and `pcie-frac=1` in both arms. The exact-length 8,192-token held-out prompt planted three retrieval codes and required their ordered return plus suffix sum `1768`.

| Check | Strata grouped | Strict NInfer grouped | Result |
|---|---|---|---|
| Exact expected answer | Pass | Pass | Same exact text |
| Generated tokens | 47 | 47 | Token IDs identical |
| Resident map | Same 3,000-slot map | Same 3,000-slot map | SHA-256 `a02fd81e…` in both |
| Persistent state | All 9 fields captured | All 9 fields captured | Every field identical |
| Minimum available RAM | 11.40 GiB across both runs | — | Above 6-GiB floor |

The checker exited successfully with no failures. This extends exact-answer and final-state parity for the active staged-compute path through an 8K prompt under a 16K capacity. The arms were sequential and traced, so this is correctness evidence, not a performance estimate or a near-limit 16K test. It does not qualify arbitrary natural generation or broader model support. Supervisor telemetry sampled clocks without changing them; energy was not measured.

Reproduce by generating an exact fixture with `python3 tools/integration/prepare_ninfer_long_retrieval.py --tokens 8192 --output <new-output-dir>`, then run the checker under `tools/integration/run_control.py` with `--compare-staged-backends --run`, using a Q2_0 config with `--max-context 16384`. The 2K report contains the complete checker invocation.

Raw fixture, config, traces, residency maps and supervisor samples remain local in this directory; models and build products remain outside Git.
