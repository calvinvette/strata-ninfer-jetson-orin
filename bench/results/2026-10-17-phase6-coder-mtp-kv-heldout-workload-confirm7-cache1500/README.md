# Held-out Coder IQ1_M MTP × KV × workload confirmation — Orin — 2026-10-17

This seven-block randomized confirmation crosses accepted-only MTP off/MTP4,
FP16/INT8 KV and two held-out retrieval-plus-arithmetic prompts: 512 tokens and
7,501 tokens at an 8,192 context. It uses the Coder `IQ1_M` artifact from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, with the established local Strata
pack. Both native GGUF shards are identified by the existing model manifest;
the model and MTP files stayed under `~/models/strata-orin-validation/`.
This is an MTP/KV/workload comparison within one quantization and engine, not a
comparison between model quantizations or inference engines.

All 56 measured arms returned the exact expected retrieval markers, arithmetic
sum and 45-token completion. The four within-block MTP pairs per block qualified
on date, prompt length and exact resident cache size: 1,934 expert slots /
3,807 MiB. The seven blocks contribute seven independent paired observations
per cell. Effects below are MTP4 versus MTP off; intervals are paired bootstrap
95% intervals over blocks.

| KV | Prompt | Prompt TPS change | Decode TPS change | Client TTFT change | Client total-time change |
| --- | ---: | ---: | ---: | ---: | ---: |
| FP16 | 512 | −2.51% [−5.00, −0.76] | +0.20% [−1.01, +0.59] | +2.56% [+0.78, +5.21] | +2.28% [+0.71, +4.71] |
| FP16 | 7,501 | −1.04% [−1.16, −0.50] | −10.16% [−11.76, −8.07] | +1.06% [+0.51, +1.18] | +1.15% [+0.96, +1.46] |
| INT8 | 512 | −1.47% [−4.64, +1.89] | +1.77% [+0.26, +2.94] | +1.48% [−1.87, +4.79] | +0.93% [−1.84, +4.45] |
| INT8 | 7,501 | −1.03% [−1.13, −0.41] | −7.95% [−9.70, −7.46] | +1.04% [+0.42, +1.15] | +1.21% [+0.50, +1.73] |

The long-prompt decode interaction is negative for both KV formats (FP16
−10.31%, interval [−11.94, −8.61]; INT8 −8.19%, [−20.19, −7.94]). The INT8
interval is sensitive to a slow MTP4 long-prompt arm; it remains included in
the analysis. The three-way MTP × KV × workload interaction intervals include
zero for prompt rate, decode rate, TTFT and client total time. These data do
not support one MTP setting as a general win. No default or serving profile
changed.

The campaign binary SHA256 is
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`; campaign
metadata records source commit `53d7c7a419f214b4133a2319bdcdf127f23ba1c4`.
The tested profile used Q6_K warp dequant, prefill 64, eight pool workers,
context 8,192, requested 1,500 MiB expert-cache budget, prompt cache disabled,
MTP cadence 4 and dynamic clocks. The model is Coder IQ1_M; the separate MTP
checkpoint is the Qwen3.8-Flash-Next runtime checkpoint recorded with its
hashes in the prior [MTP confirmation manifest](../2026-10-16-phase6-coder-mtp4-heldout-confirm7/mtp-runtime-sha256.txt).

There were 57 attempts: 56 passing arms and one retained pressure abort. The
aborted FP16/7,501-token/MTP4 arm reached 5.71 GiB effective admission
availability, below the six-GiB guard, while host availability remained above
22 GiB and OOM counters remained zero. It was rerun in a fresh per-arm 28-GiB
scope and passed; the passing-arm minimum host/admission availability was
17.039/6.279 GiB. Across all attempts, memory-event maxima for `high`, `max`,
`oom` and `oom_kill` were zero. Swap was already in use (1.11–2.28 GiB), so
these are not zero-swap results. GPU clocks varied from 306 to 1,300.5 MHz;
CPU clocks from 729.6 to 2,201.6 MHz. EMC clock readback was denied and `tj`
ranged from 48.75 to 58.5 °C. Energy is not request-attributed; retained
tegrastats rail samples include board idle/background activity and are not
whole-device or process-energy measurements.

The raw per-arm requests, engine logs and supervisor telemetry are retained in
`campaign/`. The machine-readable campaign summary and independently rerunnable
residency audit are `campaign/campaign.json` and `residency-audit.json`.
`cell-effects.csv` contains the paired cell estimates and intervals; the
[decode-rate plot](decode-effects.png) is also available as SVG. The preceding
[512-token-only held-out confirmation](../2026-10-17-phase6-coder-mtp-kv-heldout-confirm7-cache1500/README.md)
is not a separate cohort; this report adds the long workload and full
factorial interaction.

Re-run the residency qualification from the repository root:

```sh
python3 tools/integration/audit_mtp_kv_screen.py \
  bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-workload-confirm7-cache1500/campaign/campaign.json \
  --run-root bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-workload-confirm7-cache1500/campaign \
  --output /tmp/coder-mtp-kv-residency-audit.json
```

This confirmation closes only this Coder IQ1_M MTP × KV × prompt-length cell
set. Other Phase 6 interactions, energy attribution and Pareto analysis remain
open; Phase 5 state/quality qualifications and Phase 7 release gates also
remain open.
