# E6 active staged-compute held-out retrieval/state check at 160K — state parity failed

Date: 2026-10-27 (Orin AGX). Source: `2b0c2eb6` (the source tree was unchanged from that pushed checkpoint); binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

This one-run-per-arm diagnostic compared Strata grouped compute with strict NInfer grouped compute, staging enabled in both. Profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0; 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers, 256K configured context, `pcie-frac=1`. The exact-length 163,840-token held-out prompt planted three retrieval codes and required their ordered return plus suffix sum `1768`.

| Check | Strata grouped | Strict NInfer grouped | Result |
|---|---|---|---|
| Exact expected answer | Pass | Pass | Same exact text |
| Generated tokens | 47 | 47 | Token IDs identical |
| Resident map | Same 3,000-slot map | Same 3,000-slot map | SHA-256 `a02fd81e…` in both |
| Persistent state | Captured | Captured | **Failed:** `gdn`, `tail`, `pooled`, `pooled_full` and `kv` differ; `L`, `ple`, `dead` and `ple_prev` match |
| Minimum available RAM | 6.79 GiB sampled | — | Above 6-GiB floor |
| Peak swap used | 1.71 GiB sampled | — | Swap observed |
| Paired diagnostic elapsed | 54.2 min | — | Sequential, traced; not a throughput measure |

The exact text and token IDs do not qualify the request because five persistent-state fields differ. The supervisor stopped after the checker returned failure; it did not trigger the memory floor, and OOM counters were zero. This is a failed correctness cell at 160K prompt length, not an unsupported memory cell. The available-memory margin was narrow. Do not claim state-equivalent active NInfer at this length until the divergence is diagnosed and the comparison passes. Clocks were observed without controls; energy was not measured.

Reproduce by generating the fixture with `python3 tools/integration/prepare_ninfer_long_retrieval.py --tokens 163840 --output <new-output-dir>`, then running `tools/integration/ninfer_q2_retrieval_check.py` under `tools/integration/run_control.py` with `--compare-staged-backends --run`, Q2_0 config at `--max-context 262144`. The 2K report contains the complete invocation.

Raw fixture, config, traces, residency maps and supervisor samples remain local in this directory; model files and build products remain outside Git.


A corrected accepted-prefix GDN-array diagnostic found exact equality at GDN
layer 0, a tiny first difference at layer 1 (relative L2 `6.87e-10`), then
amplification at layer 2 (`3.41e-6`) and layer 3 (`4.41e-3`). The all-layer
relative L2 was `3.60%`; the originating operation remains unknown. See the
[GDN localization note](GDN_STATE_LOCALIZATION.md).
