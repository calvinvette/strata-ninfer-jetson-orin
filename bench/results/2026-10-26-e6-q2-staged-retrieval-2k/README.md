# E6 staged-miss 2K held-out retrieval and state diagnosis

Date: 2026-10-26. Hardware: Jetson AGX Orin 32 GB, CUDA 12.6, SM87. Model:
Qwen3.8-Flash-Next GSQ RCO Q2_0; expected-answer prompt length 2,048 tokens.
Strata binary SHA256:
`3a8133abbbe83dce0ec87473d5843f8cb59d9e59ed276198ab008747ff333b90` from
source commit `68de59ab2c6736ca328c83afabe2138123cd7051`.

## Result

The CPU-miss and strict NInfer staged routes returned the exact held-out
retrieval/arithmetic answer in 47 generated tokens, with identical token IDs
and identical 3,000-slot residency-map hashes. The staged route offloaded
4,556 expert reads. However, the final persistent state differed in GDN, PLE,
tail, pooled, pooled-full and KV fields. This fails the state-parity gate; the
staged profile is not qualified even though this task's answer was correct.
Minimum available physical/admission memory across runs was
12,296,478,720 bytes (11.45 GiB), above the 6-GiB floor.

A matched resident-only control (`--pcie-frac 0.0` for both backends) returned
the same answer and token IDs, with identical residency maps and all nine
final state fields. Its complete 36-layer GDN dump was bit-identical (zero
different floats). This isolates the observed state difference to the staged
miss route or to computations it causes; it does not identify a specific bug.

## State and route localization

At the same 2,047 prompt position, sampled MoE route IDs matched between
CPU-miss and staged runs at layers 1, 2, 3, 11 and 21. The activation and
combined MoE output differences grew with depth:

| Layer | Input relative L2 | Expert-parts relative L2 | Combined-output relative L2 | Max route-weight delta |
| ---: | ---: | ---: | ---: | ---: |
| 1 | `1.03e-7` | `5.94e-8` | `1.53e-7` | `6.0e-8` |
| 2 | `0.00106` | `0.00809` | `0.00564` | `9.53e-5` |
| 3 | `0.00591` | `0.01380` | `0.01074` | `4.79e-4` |
| 11 | `0.01312` | `0.02086` | `0.01974` | `0.00134` |
| 21 | `0.01938` | `0.02929` | `0.02688` | `0.00115` |

All ten selected experts at sampled layer 2 / position 2,047 were nonresident
according to the startup residency map. The layer-1 capture found small part
deltas in three ranks, including nonresident experts 74 and 70. These are
single-position diagnostics with tracing enabled; they are not performance
measurements and do not prove the causal path.

The final 2,094-token GDN comparison covered 29,417,472 float32 values. The
staged dump differed in 28,506,807 floats (96.9%), with global relative L2
`0.03414`; the largest layer-relative L2 was `0.07877` at allocation ordinal
26. GDN state first differed at ordinal 1 (`1.61e-5` relative L2), rose to
`0.00135` at ordinal 2, and continued to grow. The resident-only dumps were
identical at every ordinal. Full per-layer metrics are in
[`run-gdn-final/gdn-comparison.json`](evidence/run-gdn-final/gdn-comparison.json)
and [`resident/gdn-comparison.json`](evidence/resident/gdn-comparison.json).
The four 117-MB raw arrays remain local to the Orin worktree rather than Git;
their byte counts and SHA256 values are recorded in
[`gdn-dump-artifact-hashes.json`](evidence/gdn-dump-artifact-hashes.json).

The raw-F32 FP64 expert-oracle experiment in `analyze_layer2_oracle.py` is
retained as exploratory only. The service projects with Q8_1-quantized
activations, including a Q8_1 SwiGLU intermediate; that experiment's reference
uses unquantized F32 activations and therefore does not match the runtime
arithmetic contract. Its residuals are not used as a pass/fail result.

## Reproduction and evidence

The held-out workload was generated with
`tools/integration/prepare_ninfer_long_retrieval.py --tokens 2048`. Run records,
resident maps, supervisor telemetry, per-layer captures and analyses are under
[`evidence/`](evidence/). The state replay used `--compare-cpu-miss-staged`;
the resident-only control used `--compare-strata-control` with `pcie-frac 0.0`.
Both checkers returned nonzero only because the staged runs detected final
state differences; the engines completed and the primary task returned the
exact expected answer. The capture runs generate one output token only and are
state/route diagnostics, not complete-answer tests.

Focused checks passed:

- `python3 -m py_compile tools/integration/ninfer_q2_retrieval_check.py bench/results/2026-10-26-e6-q2-staged-retrieval-2k/analyze_layer2_oracle.py`
- `python3 tools/integration/test_analyze_ninfer_backend_capture.py`
- `python3 tools/integration/test_q2_0_expert_oracle.py` (4 tests)
- `git diff --check`

No performance conclusion is drawn from the sequential diagnostic timings. E6
remains open until the staged state difference is explained or bounded by an
accepted numerical/quality contract and matched performance testing is
repeated.
