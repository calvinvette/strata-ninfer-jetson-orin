# E6 active staged-compute held-out retrieval/state check at 128K

Date: 2026-10-27 (Orin AGX). Source: `b404f399` (the source tree was unchanged from that pushed checkpoint); binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

This one-run-per-arm diagnostic compared Strata grouped compute with strict NInfer grouped compute, staging enabled in both. Profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0; 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers, 256K configured context, `pcie-frac=1`. The exact-length 131,072-token held-out prompt planted three retrieval codes and required their ordered return plus suffix sum `1768`.

| Check | Strata grouped | Strict NInfer grouped | Result |
|---|---|---|---|
| Exact expected answer | Pass | Pass | Same exact text |
| Generated tokens | 47 | 47 | Token IDs identical |
| Resident map | Same 3,000-slot map | Same 3,000-slot map | SHA-256 `a02fd81e…` in both |
| Persistent state | All 9 fields captured | All 9 fields captured | Every field identical |
| Minimum available RAM | 6.80 GiB sampled | — | 0.80 GiB above 6-GiB floor |
| Peak swap used | 1.96 GiB sampled | — | Swap observed |
| Paired diagnostic elapsed | 43.7 min | — | Sequential, traced; not a throughput measure |

The checker and supervisor exited successfully; supervisor OOM counters were zero. This extends active staged-compute correctness through a 128K prompt under a 256K cap. The available-memory margin was narrow, so this result applies to the recorded host conditions and profile; no safety margin beyond the six-GiB guard is implied. The arms were sequential and traced, so this is functional evidence, not a timing estimate or near-limit 256K ingestion result. It does not qualify arbitrary natural generation. Clocks were observed without controls; energy was not measured.

Reproduce by generating the exact fixture using `python3 tools/integration/prepare_ninfer_long_retrieval.py --tokens 131072 --output <new-output-dir>`, then run the checker under `tools/integration/run_control.py` with `--compare-staged-backends --run`, using Q2_0 config at `--max-context 262144`. The 2K report contains the complete invocation.

Raw fixture, config, traces, residency maps and supervisor samples remain local in this directory; model files and build products remain outside Git.
