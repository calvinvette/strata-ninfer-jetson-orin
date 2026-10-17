# Coder MTP × KV × prompt-length follow-up — 1,500 MiB cache — Orin

This randomized one-block follow-up completed all eight cells from the
three-block screen at the 1,500 MiB expert-cache budget. The four MTP-off/MTP4
pairs used identical residency (1,934 expert slots / 3,807 MiB), matched the
requested KV format and actual prompt length, and ran on the same local date,
2026-10-17. All eight arms passed the exact retrieval oracle. This restores a
third qualified screening block for every cell and a third complete factorial
block; it is not the seven-repetition held-out confirmation required before
selecting or promoting a configuration.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, IQ1_M, pinned
at revision `5348543e0147355ac9cbcb031184a3546350988e`. The two model shards
have SHA256 values `e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad`
and `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
The candidate binary SHA256 is
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`, built
from Strata source commit `9dac82fdc3475227fa6eb34125e8160e78efd5c2`. MTP used
the same separately sourced upstream base-checkpoint artifact as the prior
Coder screens. The run used 8 workers, prefill chunk 64, 8K context, disabled
prompt cache, mmap experts and dynamic clocks.

The screen's cache budget yielded stable actual residency. For this follow-up,
MTP4 changed median paired decode throughput by +10.48% for FP16/512 tokens,
+4.34% for FP16/7,501, +13.51% for INT8/512 and +12.78% for INT8/7,501. The
corresponding client total-time changes were −0.96%, −0.09%, −2.03% and +0.35%.
Each is a single-block effect and has no estimable bootstrap interval. These
numbers are a follow-up observation, not a confirmation result.

Combining this block with the two fully matched blocks from the original
screen gives three qualified pairs per cell (12 total) and three fully matched
blocks for the MTP × KV × workload interaction. The source blocks are mapped
explicitly in `combined-analysis-input.json`: original block 0 (Oct 16),
original block 2 (Oct 17), and this follow-up block 0 (Oct 17). The other
original block is excluded because one pair had a residency mismatch and
another crossed local midnight. All retained pairs have 1,934 slots / 3,807
MiB residency. The combined median MTP4 decode-throughput effects are:

| KV | Prompt | Qualified pairs | Decode throughput change (paired-block bootstrap 95% interval) | Client total-time change |
|---|---:|---:|---:|---:|
| FP16 | 512 | 3 | +11.91% (+10.48%, +14.13%) | −2.04% |
| FP16 | 7,501 | 3 | +4.34% (+4.14%, +36.24%) | −0.09% |
| INT8 | 512 | 3 | +14.02% (+13.51%, +14.38%) | −1.18% |
| INT8 | 7,501 | 3 | +6.90% (+6.31%, +12.78%) | +0.35% |

The three-way decode interaction changes were −21.70%, +0.20% and +5.21%
across the three qualified blocks, showing that a stable interaction estimate
is not established by this screening sample. Bootstrap intervals from three
blocks are descriptive and do not substitute for independent confirmation.
No profile or default changed.

Across the follow-up's 1,709 one-second samples, minimum host availability was
17.08 GiB and minimum admission availability was 7.79 GiB. Peak supervised
cgroup use was 20.21 GiB under `MemoryMax=28G`; `high`, `max`, `oom` and
`oom_kill` counters were zero. GPU/CPU clocks varied during the campaign; EMC
readback was denied. Energy was not request-attributed.

Collection completed all eight arms successfully, but the campaign wrapper
then exited with an analysis error while converting a one-repetition
bootstrap interval containing `null`. The raw campaign and per-arm results
were retained. The summary was regenerated from those passing records after
fixing the one-block interval handling in
`tools/integration/mtp_kv_workload_screen.py`; a regression test covers this
case. No model arms were rerun or altered during recovery. The regenerated
campaign and residency audit are `campaign/campaign.json` and
`residency-audit.json`; the three-block pooled screening audit is
`combined-residency-audit.json`.

Reproduce the follow-up from the repository root on the same Orin setup with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/mtp_kv_workload_screen.py \
  --config bench/results/2026-10-16-phase5-coder-mtp-window-screen/config.json \
  --workloads bench/results/2026-10-16-phase5-coder-mtp-window-screen/workloads.json \
  --warmup-workloads bench/results/2026-10-16-phase5-coder-mtp-window-screen/warmup-workloads.json \
  --output bench/results/2026-10-17-phase6-coder-mtp-kv-followup-budget1500/campaign \
  --workload-cells coder-mtp-retrieval-short-512 coder-mtp-retrieval-near-limit-7501 \
  --kvs fp16 int8 --windows 0 4 --blocks 1 --followup-block \
  --seed 20261025 --first-port 19600 --expert-cache-budget 1500

python3 tools/integration/audit_mtp_kv_screen.py \
  bench/results/2026-10-17-phase6-coder-mtp-kv-followup-budget1500/campaign/campaign.json \
  --run-root bench/results/2026-10-17-phase6-coder-mtp-kv-followup-budget1500/campaign \
  --output bench/results/2026-10-17-phase6-coder-mtp-kv-followup-budget1500/residency-audit.json
```

The raw campaign includes each randomized arm's request, service log, actual
configuration, clock/memory samples, tegrastats and supervisor result.
