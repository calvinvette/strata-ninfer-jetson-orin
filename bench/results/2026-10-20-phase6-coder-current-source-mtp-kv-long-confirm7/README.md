# Current-source Coder IQ1_M long-prompt MTP × KV confirmation

This seven-block Orin confirmation compares MTP off and MTP4 with FP16 and
INT8 KV on one held-out, 7,501-token retrieval-plus-arithmetic request. It
repeats the long-task cell on the current Strata source and binary; it does not
compare a second GGUF quantization or establish a general MTP default.

## Scope and identity

- Device: Jetson AGX Orin, ARM64, CUDA 12, SM87; run date 2026-10-20.
- Model: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, pinned revision
  `5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M two-shard GGUF. The local
  files remain under `~/models/strata-orin-validation/Coder-GGUF/IQ1_M/`.
- MTP runtime revision: `de4b8e4d43b917e7706784d8bb445c9af86a3540`; artifacts
  remain under `~/models/strata-orin-validation/mtp/rt/`.
- Current-source CUDA Release binary SHA256:
  `b672187692408e8abcb48beb6ad80282b01954bae819ec48963ac7c6440e4ec9`.
- Request: 7,501 actual prompt tokens, exact 45-token expected answer, 8,192
  configured context, 1,500 MiB expert-cache override, 64-token prefill,
  `--mmap-experts`, eight pool workers, no prompt cache, dynamic clocks.
- Four cells (MTP off/4 × FP16/INT8 KV), seven randomized blocks; all arms ran
  on the same local date and matched at 1,934 expert slots / 3,807 MiB measured
  cache residency. Each arm had one separate 512-token warmup.
- Each arm used a fresh 28 GiB cgroup scope. The ordinary six-GiB host
  availability floor was retained. No service or clock policy was changed.

The source campaign and raw per-arm records are in [`campaign/`](campaign/).
[`audit.json`](audit.json) applies the paired date, prompt-token, KV and
residency rules. [`qualification-audit.json`](qualification-audit.json)
independently checks all responses, supervisor results, memory floors and
cgroup event counters. Model and runtime attribution is in
[`model-source.txt`](model-source.txt) and [`artifact-sha256.txt`](artifact-sha256.txt).

## Result

All 28 arms passed the supervisor and returned the exact held-out answer. The
minimum observed host availability was 16.96 GiB; minimum admission
availability was 10.71 GiB. Across all per-arm memory samples, cgroup
`high`, `max`, `oom` and `oom_kill` counters remained zero. All 28 request
windows had named-rail energy estimates; none was unsupported.

The paired MTP4 effect (seven same-day blocks per KV format) is:

| KV | Client TTFT | Client total time | Prompt throughput | Decode throughput | VIN_SYS_5V0 energy / 45 output tokens |
|---|---:|---:|---:|---:|---:|
| FP16 | +0.86% [ +0.26, +0.92 ] | +0.94% [ +0.34, +1.03 ] | −0.85% | −10.10% | +0.57% [ +0.43, +0.74 ] |
| INT8 | +0.94% [ +0.77, +1.07 ] | +1.06% [ +0.87, +1.16 ] | −0.92% | −8.67% | +0.71% [ +0.06, +0.90 ] |

Brackets are paired bootstrap 95% intervals in percent for TTFT, total time
and VIN_SYS_5V0. Throughput effects are median paired ratios summarized in
[`audit.json`](audit.json); the full paired samples and intervals are there.
For this task, MTP4 reduced decode throughput and slightly increased latency
and named-rail energy in both KV cells. It is dominated by MTP-off on the
recorded latency / VIN_SYS_5V0 Pareto coordinates within each KV cell; see
[`pareto-cells.csv`](pareto-cells.csv) and
[`pareto-latency-energy.svg`](pareto-latency-energy.svg).

The energy values integrate named tegrastats rails over the API request window.
They include board idle and background draw and are not process-attributed or
whole-device measurements. CPU/GPU frequencies were sampled dynamically;
EMC frequency was unsupported because the debug clock path denied access.

## Interpretation and limits

This is a current-source, seven-block held-out confirmation for one long
Coder IQ1_M task. It supports no MTP4 speed or energy claim for this task and
does not select a universal MTP/KV profile. It does not cover the newly
downloaded Coder repository at another quantization, a short-prompt task,
context/cache interactions, or other profiles. Phase 6 remains open for the
remaining planned factors and documented cross-factor evidence. Phase 5 also
remains open because adaptive residency migration still has unresolved
persistent-state divergence. Phase 8 cannot close until the applicable Phase 5
and Phase 6 gates are complete.

Reproduction commands from the repository root:

```sh
python3 tools/integration/mtp_kv_workload_screen.py \
  --config bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/config.json \
  --workloads bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/workloads.json \
  --warmup-workloads bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/warmup-workloads.json \
  --output bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/campaign \
  --workload-cells coder-mtp4-heldout-retrieval-arithmetic-near-limit-7501 \
  --kvs fp16 int8 --windows 0 4 --blocks 7 --seed 20261037 --first-port 19900 \
  --expert-cache-budget 1500 --per-arm-memory-max 28G

python3 tools/integration/audit_mtp_kv_screen.py \
  bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/campaign/campaign.json \
  --run-root bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/campaign \
  --output bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/audit.json

python3 bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/audit_qualification.py

python3 bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/analyze_rail_energy.py

python3 bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/analyze_pareto.py
```
