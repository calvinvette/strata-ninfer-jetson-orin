# Coder IQ1_M MTP window screens — Orin — 2026-10-16

These randomized three-block screens compare MTP off/2/3/4 on the same Coder
IQ1_M service path, first for a 512-token retrieval-plus-arithmetic task and
then for a 7,501-token near-limit retrieval task at 8K context. The short-task
results are in [`screen-short/README.md`](screen-short/README.md), and the
near-limit results and residency qualification are in
[`screen-near-limit/README.md`](screen-near-limit/README.md).

Both screens use `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M,
revision `5348543e0147355ac9cbcb031184a3546350988e`. The draft runtime comes
from upstream `Qwen/Qwen3.8-Flash-Next`, revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`; it is not Coder-specific. The
model and runtime stay in `~/models/strata-orin-validation/`.

The near-limit MTP2 comparison initially had one block with unequal actual
expert residency. A separate three-block MTP-off versus MTP2 follow-up at a
lower cache cap matched 3,378 slots in all six services. One MTP2 run still had
a 9.92-second streaming gap, producing a wide decode-rate interval; this is
recorded as an inconclusive screen in
[`screen-near-limit-mtp2-fixed-cache/README.md`](screen-near-limit-mtp2-fixed-cache/README.md).
See [`mtp2-fixed-cache-command.txt`](mtp2-fixed-cache-command.txt) for its exact
command. It supplements but does not replace the original all-window results.

These are screening results for one Coder quantization, one task per prompt
length and FP16 KV. They do not qualify a preferred MTP window, a default
profile or general long-context quality. Phases 5–7 remain open.
