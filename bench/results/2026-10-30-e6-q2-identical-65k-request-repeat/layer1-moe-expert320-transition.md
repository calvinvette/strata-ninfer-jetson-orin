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

The focused `ninfer_q2_expert_parity` executable was also run with the same
model layer, expert ID and input; it exited successfully. That operator check
does not reproduce the service's changing grouped multi-expert/runtime
history, so it does not close the issue.

## Interpretation and limits

This is evidence of request-to-request variation in a single resident NInfer
expert row with fixed route IDs, weights, and input. It is a correctness
localization finding, not a general determinism claim or proof that NInfer
alone causes the variation. The next investigation should compare the exact
expert-320 weight bytes and grouped-kernel intermediate/output state across
both service requests, then exercise the same grouped sequence under the
Strata backend as a control.

Both requests passed. Supervised telemetry recorded 8.61 GiB minimum
available RAM, 4.18 GiB peak swap use, and no cgroup OOM kills. Full raw
capture, logs, oracle data, and telemetry remain under
`/tmp/e6-65k-ninfer-moe-layer1-capture/`.
