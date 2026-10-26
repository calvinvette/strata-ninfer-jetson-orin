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

The first raw-F32 FP64 oracle comparison bypassed the runtime's Q8_1 activation
boundaries, so its residuals are exploratory and are not a pass/fail result.
The oracle now also emulates the service's Q8_1 input quantization, Q2_0 × Q8_1
block dot products, and Q8_1 SwiGLU intermediate before the down projection.
For both sampled layer-2 experts (372 and 357) on both routes, its output
matched the captured expert row to about `9e-8` relative L2 (maximum absolute
error below `1.3e-8`). We extended the check to the earliest sampled MoE layer:
experts 97, 74 and 70 at model layer 1 match at `5.9e-8`–`1.03e-7` relative
L2. There, route IDs match, the route-weight delta is at most `6e-8`, the input
delta is `1.03e-7`, and the combined MoE output delta is `1.53e-7`. The first
nonzero GDN state difference is at state layer 1 (`1.61e-5` relative L2).
Together these results locate the earliest observed divergence near first-layer
computation/aggregation and state update, with small numerical differences;
they do not establish which operation causes it. The larger layer-2 activation
delta is downstream growth, not evidence of a layer-2 expert-kernel fault. See
the [layer-1 oracle results](evidence/oracle-layer1/analysis.json) and
[layer-2 oracle results](evidence/oracle-layer2/analysis.json).

Reproduce the oracle checks with `python3 analyze_layer_oracle.py --layer 1`
and `python3 analyze_layer_oracle.py --layer 2` on the Orin with the local
Q2_0 model.

## Staged-backend isolation

The retrieval checker now has `--compare-staged-backends`. Both arms set
`--pcie-frac 1.0` and use the same resident map, staged weights and workload;
only the grouped expert backend changes between Strata and strict NInfer. On
the one-token diagnostic, both routes generated token 19910, staged 97 expert
reads, and matched residency plus all final state fingerprints. On the full
held-out task, both returned the exact answer in 47 tokens, staged 4,556 reads,
and matched every token ID and persistent-state field. Minimum available
memory was 11.56 GiB and 11.59 GiB. These are functional ablations, not
performance measurements.

This comparison indicates the CPU-miss versus staged state difference does
not come from a difference between the Strata and NInfer grouped GPU backends
for this task. Both staged GPU backends produce identical persistent state,
while the prior CPU-miss versus NInfer-staged comparison does not. The
remaining discrepancy is associated with the CPU-miss versus staged execution
path; the specific arithmetic, activation representation or state operation
responsible has not been isolated.

An all-layer committed-state capture after processing the prompt's final
zero-based position (2047) further localizes the first material GDN difference.
The two arms used the same committed token (271). Model layer 0 state was
bit-identical; layer 1 relative L2 was `1.076e-9`; model layer 2 was the first
material change at `9.937e-4`. Across 36 GDN layers and 29,417,472 floats,
global relative L2 was `0.03865`. The error then grows through later layers.
This is one accepted-prefix snapshot; it points to a small upstream difference
being amplified by downstream computation but does not identify the operation
that creates it. The raw 225 MB capture remains local. Its SHA256 and the
13 MB pre/post capture hash are recorded in
[`evidence/state-capture-artifact-hashes.json`](evidence/state-capture-artifact-hashes.json);
per-layer metrics are in
[`evidence/state-commit2047/per-layer-comparison.json`](evidence/state-commit2047/per-layer-comparison.json).
Reproduce the summary with `python3 analyze_gdn_commit_capture.py <capture>
--output <json>` on the local capture.

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

- `python3 -m py_compile tools/integration/ninfer_q2_retrieval_check.py bench/results/2026-10-26-e6-q2-staged-retrieval-2k/analyze_layer_oracle.py`
- `python3 -m py_compile bench/results/2026-10-26-e6-q2-staged-retrieval-2k/analyze_gdn_commit_capture.py`
- `python3 tools/integration/test_analyze_ninfer_backend_capture.py`
- `python3 tools/integration/test_q2_0_expert_oracle.py` (4 tests)
- `git diff --check`

No performance conclusion is drawn from the sequential diagnostic timings. E6
remains open until the staged state difference is explained or bounded by an
accepted numerical/quality contract and matched performance testing is
repeated.
