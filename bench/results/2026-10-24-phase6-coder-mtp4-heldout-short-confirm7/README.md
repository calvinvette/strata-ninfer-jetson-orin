# Held-out MTP4 retrieval confirmation — Orin — 2026-10-24

## Result

Seven randomized paired blocks compared MTP-off and MTP4 with FP16 and INT8 KV
on a distinct 512-token Coder IQ1_M retrieval/arithmetic prompt. This prompt
was used in the prior MTP3 confirmation, but was held out from the MTP4 screen
reported separately. Each arm used a fresh supervised process. All 28 cells
passed the expected-answer check and returned the exact three marker codes and
sum 1478. There were 14 qualified same-day paired comparisons and no excluded
pairs.

Effects are MTP4 relative to MTP-off. Intervals are paired-block bootstrap 95%
intervals; the seven blocks, not successive tokens, are the independent units.

| KV | Decode throughput | Client TTFT | Client total |
| --- | ---: | ---: | ---: |
| FP16 | +13.22% (+11.92, +15.28) | −0.06% (−0.43, +2.45) | −1.07% (−2.88, +0.65) |
| INT8 | +13.72% (+13.51, +14.41) | +0.05% (−0.34, +1.69) | −1.43% (−1.82, −0.10) |

The paired MTP4 × KV interaction interval includes zero for decode throughput
(median interaction +0.61%, 95% interval −1.35% to +2.20%) and total time
(+0.75%, −1.50% to +1.09%). This single held-out prompt supports a short-task
decode gain for MTP4 under both KV formats. It does not establish a stable
end-to-end gain for FP16; the INT8 total-time median reduction was small. It
does not overturn the separate near-limit screen, where MTP4 decode throughput
was lower by 8.80–10.95%. No global setting or default is promoted.

MTP4 drafted 39 and accepted 34 tokens in every measured request. MTP-off
drafted and accepted none. Each response emitted 47 tokens through natural
stop. These are workload-specific results and do not establish persistent
state parity.

One retained block-4 FP16 MTP-off control was a decode outlier: 5.15 tokens/s
and 36.19 seconds total, versus 13.44 tokens/s and 30.44 seconds for its MTP4
pair. Its GPU clock samples spanned 306–1,300.5 MHz; the other cells were also
dynamically clocked. The logs do not establish why this control was slow. It is
retained in the paired summary and response-model diagnostics, not discarded.

## Measurement scope

- Date: 2026-10-24; seven randomized blocks; 14 same-day pairs; all cells pass.
- Model: pinned Coder IQ1_M GGUF artifact revision
  `5348543e0147355ac9cbcb031184a3546350988e`, plus upstream base-checkpoint MTP
  weights. Artifacts remain under `~/models/strata-orin-validation/`.
- Workload: 512 formatted input tokens, 47 output tokens, 8,192-token context.
  Prompt and expected answer are retained in `inputs/workloads.json`.
- Expert cache: 1,500 MiB requested; 1,934 actual slots / 3,807 MiB allocated.
- Device: Orin AGX, native aarch64, CUDA 12.6 / SM87. GPU clocks varied from
  306 to 1,300.5 MHz; EMC readback was unavailable.
- Memory: minimum physical and effective-admission availability was 16.84 GiB.
  The 28-GiB per-arm cgroup recorded zero high, max, OOM or OOM-kill events.
- Energy: not analyzed. This makes no energy-per-token or Pareto claim.

The campaign and audit are `campaign.json` and `final-audit.json`. The
full-rank exploratory response fit is `response-model.json`; its script is
`fit_response_model.py`. The model uses log responses, six fixed block
indicators, MTP, KV and MTP × KV. Its design rank is 10/10 with 18 residual
degrees of freedom, but maximum standardized residuals exceed 3 for decode
throughput and total time. The model-based effects are therefore diagnostic
only; paired-block bootstrap estimates above are primary. Per-arm raw logs and
telemetry remain local.

To reproduce the campaign, use `config-source.json` with its retained draft
model path:

```sh
python3 tools/integration/mtp_kv_workload_screen.py \
  --config bench/results/2026-10-24-phase6-coder-mtp4-heldout-short-confirm7/config-source.json \
  --workloads bench/results/2026-10-24-phase6-coder-mtp4-heldout-short-confirm7/inputs/workloads.json \
  --warmup-workloads bench/results/2026-10-24-phase6-coder-mtp4-heldout-short-confirm7/inputs/warmup-workloads.json \
  --output /tmp/coder-mtp4-heldout-short-confirm7 \
  --workload-cells coder-mtp-retrieval-short-512 \
  --kvs fp16 int8 --windows 0 4 --blocks 7 --seed 20261024 \
  --per-arm-memory-max 28G
```

The confirmation covers one held-out prompt, not a workload family. MTP4's
long-prompt decode regression, persistent-state limits, graph × speculation,
and energy/Pareto gates remain open. Phase 6 and Phase 5 remain open.
