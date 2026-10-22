# Current-source Coder IQ1_M short × long MTP × KV confirmation

This randomized Orin confirmation crosses two held-out retrieval-plus-arithmetic
prompt lengths with MTP off/MTP4 and FP16/INT8 KV. It uses one current-source
binary and seven blocks, so each cell has seven same-day paired observations.
The original seven-block long-only result is recorded separately in
[`2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/`](../2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/);
that earlier short-task campaign used a different binary and is not pooled here.

## Scope and identity

- Jetson AGX Orin, ARM64, CUDA 12, SM87; all arms ran on 2026-10-21.
- Model repository: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`,
  revision `5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M two-shard GGUF.
  Model and MTP files remain under `~/models/strata-orin-validation/`.
- Source commit recorded by the campaign: `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`.
- Candidate binary SHA256:
  `b672187692408e8abcb48beb6ad80282b01954bae819ec48963ac7c6440e4ec9`.
- Factors: MTP window {0,4} × KV {FP16,INT8} × prompt {512,7,501 tokens};
  seven randomized blocks; 56 total request arms. Each arm had a separate
  512-token, one-token warmup.
- All matching cells paired on local date and measured residency:
  1,934 expert slots / 3,807 MiB. Arms used separate 28-GiB cgroup scopes,
  preserved the six-GiB physical host floor, and ran with dynamic clocks.

The complete raw campaign is in [`campaign/`](campaign/). The campaign
generated its residency/date paired analysis; see [`audit.json`](audit.json).
[`qualification-audit.json`](qualification-audit.json) independently checked
all measured answers, supervisor statuses, memory samples, cgroup limits and
event counters. Every answer exactly matched:
`EARLY=EMBER-VAULT-317, MIDDLE=SILVER-MAPLE-846, LATE=TIDAL-COPPER-529, SUM=1692`.

## Paired MTP4 effects

Each entry is the median paired MTP4/off change, with the paired-block bootstrap
95% interval in brackets. Positive TTFT/total changes mean slower; negative
throughput changes mean slower.

| Prompt | KV | Client TTFT | Client total time | Prompt throughput | Decode throughput |
|---|---|---:|---:|---:|---:|
| 512 | FP16 | +3.54% [−0.44, +4.34] | +3.28% [−0.40, +4.03] | −3.44% [−4.16, +0.43] | −1.34% [−3.49, −0.71] |
| 512 | INT8 | +4.32% [−0.13, +5.29] | +3.89% [−0.13, +4.62] | −4.20% [−5.08, +0.17] | −0.21% [−0.50, +0.49] |
| 7,501 | FP16 | +0.51% [+0.43, +0.67] | +0.59% [+0.54, +0.79] | −0.51% [−0.66, −0.43] | −9.17% [−9.62, −8.22] |
| 7,501 | INT8 | +0.91% [+0.67, +3.32] | +1.01% [+0.75, +3.39] | −0.90% [−3.22, −0.65] | −9.24% [−10.38, −8.36] |

The long-task decode loss is consistent across both KV formats. Short-task
latency and throughput intervals are wider and often include no change. The
paired workload interaction estimates show a larger MTP4 decode-throughput
loss on the long task than on the short task: −6.97% [−7.81, −5.88] with FP16
KV and −9.41% [−10.70, −7.90] with INT8 KV. Long-versus-short interactions
for client total time have intervals spanning no change for both KV formats.
MTP × KV interaction and three-way intervals are in `audit.json`; the
three-way intervals span zero.

Two short-task MTP4 arms are unusually slow and remain in all analyses. Block
0 / FP16 had 56.31 s prompt time versus 24.80 s in its MTP-off pair; its
request GPU-clock samples had a 408 MHz median versus 612 MHz in the paired
control. Block 2 / INT8 had 25.21 s decode time versus 3.71 s in its MTP-off
pair; its sampled GPU median was 1,020 MHz versus 612 MHz in the control. Both
returned the exact answer and accepted 33 of 42 offered drafts. The clock
observations do not establish the cause of either delay. We retained both arms
and their effects instead of filtering them; their block-level ratios widen
the uncertainty for short-task interactions.

A blocked log-response model with all workload × KV × MTP terms has full design
rank (14/14 columns, 42 residual degrees of freedom). Its residual diagnostics
flag these same arms strongly (maximum absolute internally studentized
residuals: 6.39 for TTFT, 5.14 for total time and 5.08 for VIN_SYS_5V0 in
block 0 / FP16; 6.47 for decode and 3.97 for total time in block 2 / INT8).
The OLS intervals are therefore retained as diagnostics, not treated as a
supported response model. The paired-block bootstrap estimates above remain
the primary inference. See [`factorial-model.json`](factorial-model.json).
One additional randomized block across all eight cells checked recurrence of
the short-task delays. All eight arms passed and the delays did not recur; this
one-block diagnostic is documented separately in
[`followup/README.md`](followup/README.md) and is not pooled with the
prespecified seven-block confirmation.

## Request-window energy and Pareto cells

All 56 request windows had named tegrastats rail estimates. For the
VIN_SYS_5V0 board rail, median paired MTP4 changes per 45-token answer were:

| Prompt | KV | Change | Paired bootstrap 95% interval |
|---|---|---:|---:|
| 512 | FP16 | +0.15% | −2.83% to +0.39% |
| 512 | INT8 | +0.11% | −2.36% to +1.03% |
| 7,501 | FP16 | +0.46% | +0.13% to +0.64% |
| 7,501 | INT8 | +0.81% | +0.31% to +2.11% |

VIN_SYS_5V0 includes board idle and background draw; it is not process energy.
Other named rails are retained in [`rail-energy.json`](rail-energy.json).
CPU rates ranged from 729.6 to 2,201.6 MHz and GPU rates from 306 to 1,300.5
MHz during samples; EMC frequency could not be read because access to its debug
clock path was denied.

The cell-scoped latency / VIN_SYS_5V0 Pareto calculation is in
[`pareto-cells.csv`](pareto-cells.csv) and
[`pareto-latency-energy.svg`](pareto-latency-energy.svg). MTP4 is dominated by
MTP-off for both long-prompt KV cells. In the short cells the two choices
trade slightly different latency and named-rail energy, so neither dominates
the other on those two coordinates. These medians do not represent a general
profile recommendation.

Across 56 arms, minimum host and admission availability was 16.88 GiB. All
supervisors passed, every exact-answer check passed, and all sampled cgroup
`high`, `max`, `oom`, and `oom_kill` counters were zero. There were no failed,
unsupported, or pressure-aborted arms. The per-arm clock samples and raw
tegrastats remain available for review.

## Interpretation and limits

This confirms one IQ1_M model, one server configuration, one short and one
long prompt, and MTP/KV settings only. It does not cover expert-cache/context,
prefill/workspace, worker/transfer, graph/speculation interactions, or other
model quantizations. MTP4 reduces long-task decode throughput and does not
show a whole-request latency or board-energy benefit here; no default or user
profile was changed. Phase 6 remains open for its remaining planned factors,
response-model assessment, and broader Pareto coverage. Phase 5's adaptive
persistent-state divergence also remains open, so Phase 8 is not ready to
close.

Reproduce the primary analyses from the repository root:

```sh
python3 tools/integration/audit_mtp_kv_screen.py \
  bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/campaign/campaign.json \
  --run-root bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/campaign \
  --output bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/audit.json

python3 bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/audit_qualification.py
python3 bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/analyze_rail_energy.py
python3 bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/analyze_pareto.py
python3 bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/fit_factorial.py
```
