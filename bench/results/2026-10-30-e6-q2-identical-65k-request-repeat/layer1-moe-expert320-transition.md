# Layer-1 MoE expert-part transition at the final prompt token

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is an instrumented,
same-process request-repeat diagnostic, not a speed result.

## Setup

One strict-NInfer process handled the same 65,536-token prompt twice, with
temperature 0, 32 generated tokens, 131,072 context, prompt cache disabled,
and PCIe staging disabled. An opt-in model-layer-1 MoE bundle captured route
IDs, route weights, the MoE input, ten expert output rows, shared output, and
combined output at prompt position 65,535. Both records have token 271. The
bundle is 266,496 bytes for the two records.

## Findings

Routes, weights, MoE input, and shared-expert output matched exactly. The same
ten experts were selected in the same order:
`383, 32, 97, 235, 400, 320, 193, 206, 70, 74`. Only the output row for expert
320 differed:

| Field | Different values | Maximum absolute difference | Relative L2 |
| --- | ---: | ---: | ---: |
| Route weights | 0 / 10 | 0 | 0 |
| MoE input | 0 / 2,560 | 0 | 0 |
| All expert output rows | 2,220 / 25,600 | 3.18438e-05 | 1.69993e-04 |
| Expert 320 output row | 2,220 / 2,560 | 3.18438e-05 | 5.24514e-04 |
| Each of the other nine expert rows | 0 / 2,560 | 0 | 0 |
| Shared-expert output | 0 / 2,560 | 0 | 0 |
| Combined output | 1,658 / 2,560 | 1.72993e-06 | 5.56115e-05 |

Expert 320 is route index 5 with weight `0.0543313771`. Multiplying its
per-expert output delta by that unchanged route weight predicts the combined
output delta with cosine similarity `0.99999980`; the relative L2 residual
between predicted and observed combined deltas is `6.30e-04`. This ties the
combined difference to this one expert row, subject to normal float summation
order.

An independent scalar Q2_0 × Q8_1 oracle used the captured common F32 input and
the GGUF weights for model layer 1, expert 320. The second request's expert
row matched the oracle to relative L2 `5.79e-08`; the first request's row
differed by relative L2 `5.24529e-04`, with a maximum absolute difference of
`3.18416e-05`. The change between requests is therefore localized to the
expert-320 computation/output row for this pair. The result alone does not
identify whether the changing factor is a weight view, scratch lifetime,
kernel race, or another runtime detail.

## Backend control and focused replay

A second same-process 65K pair used the Strata expert backend with the same
MoE bundle capture. Its repeated request showed the same expert-320 change:
routes, weights, input and shared output were exact; the expert-320 part and
combined output had the same changed-value counts and deltas as the NInfer
pair. More strongly, the per-request route, weight, input, all expert parts,
shared output and combined output were byte-identical between NInfer and
Strata. This run does not show a difference unique to the NInfer backend.

The focused `ninfer_q2_expert_parity` check was extended to replay the exact
one-entry grouped NInfer and Strata dispatch 32 times at fixed input and
weights. Both outputs remained bit-identical across all 32 calls. The direct
NInfer D3/D4 row matched an independent FP64 Q2_0/F32 oracle (relative L2
`1.57e-07`, maximum absolute error `1.34e-08`); grouped NInfer and Strata
outputs matched exactly for the one-entry case. The process passed. Its
interleaved operator timings were 24.510 vs 24.673 microseconds (NInfer /
Strata) for one token, 4,387.924 vs 3,949.398 microseconds for 64 tokens,
and 8,938.040 vs 7,958.909 microseconds for 128 tokens. Those isolated
operator timings do not represent end-to-end serving; the larger grouped
shapes were slower with NInfer in this run.

The service's repeated multi-expert request history is not reproduced by the
fixed-input one-entry replay. The unchanged backend output therefore narrows
the cause to shared service/runtime context (for example, the live expert
weight view or cache-slot ownership) but does not establish which one.

## Interpretation and limits

This is evidence of request-to-request variation in a single resident expert
row with fixed route IDs, weights and input, reproduced byte-for-byte by both
backends. It is a correctness localization finding, not a general
determinism claim. The next investigation should compare the exact expert-320
weight bytes and Q8_1 activation bytes presented to the service grouped
dispatch across both requests, then isolate the first changed intermediate
in that grouped sequence.

Both requests passed. Supervised telemetry recorded 8.61 GiB minimum
available RAM, 4.18 GiB peak swap use, and no cgroup OOM kills. Full raw
capture, logs, oracle data, and telemetry remain under
`/tmp/e6-65k-ninfer-moe-layer1-capture/`.
