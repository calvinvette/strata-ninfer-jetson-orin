# Coder MTP × KV × prompt-length screen — Orin — 2026-10-16

This randomized three-block screen crossed MTP off/MTP4, FP16/INT8 KV and
512/7,501-token retrieval prompts on the same Coder IQ1_M artifact and candidate
binary. All 24 fresh-service arms returned the exact independent retrieval
answer, reported the requested KV format and actual prompt length, and passed
the six-GiB availability guard. This is a correctness and feasibility pass for
the tested arms; it does not make the timing grid fully qualified.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, IQ1_M, pinned
at revision `5348543e0147355ac9cbcb031184a3546350988e`. Its shard SHA256 values
are `e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad` and
`316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`; these
match the prior Coder IQ1_M report. The tested binary SHA256 is
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`, built
from source commit `9dac82fdc3475227fa6eb34125e8160e78efd5c2`. MTP used the
separately sourced upstream base-checkpoint MTP artifact already used by the
Phase 5 Coder checks. The run used 8 workers, prefill chunk 64, 8K context,
prompt cache disabled, static expert residency, and dynamic clocks. Per KV
format across its three MTP4 blocks, the 7,501-token arms drafted/accepted
90/81 tokens total and the 512-token arms drafted/accepted 117/102 tokens total.

Timing was qualified only when both MTP arms passed with equal actual expert
slots and cache MiB, matching KV format, and the same actual prompt-token
count. Eight of the 12 within-cell MTP pairs met that rule. Four pairs were
excluded because residency differed:

| Block | KV | Prompt | MTP off slots / MiB | MTP4 slots / MiB |
|---:|---|---:|---:|---:|
| 0 | FP16 | 512 | 3,803 / 7,422 | 3,903 / 7,615 |
| 1 | FP16 | 512 | 3,722 / 7,264 | 3,903 / 7,615 |
| 1 | INT8 | 512 | 3,660 / 7,142 | 3,903 / 7,615 |
| 2 | INT8 | 7,501 | 3,903 / 7,615 | 3,841 / 7,496 |

The remaining paired MTP4 decode-throughput changes were +13.65% for FP16 at
512 tokens (n=1), +16.87% for INT8 at 512 (n=2), +7.01% for FP16 at 7,501
(n=3), and +10.46% for INT8 at 7,501 (n=2). Paired client total-time changes
were +0.09%, −1.49%, +0.11% and +0.15%, respectively. These are descriptive
screen estimates with incomplete paired blocks, not confirmation intervals or
evidence of an end-to-end serving win. At the higher interaction level, only
two blocks qualified for the long-prompt MTP × KV comparison; no block had all
eight arms at identical residency, so the three-way interaction is unestimated.
The original unfiltered factorial summary is retained under the explicitly
labelled `unfiltered_comparisons_do_not_use_for_timing` field in `campaign.json`;
use `residency-audit.json` (also embedded as `comparisons`) for qualified pairs
and exclusions.

Across 4,887 one-second memory samples, host availability stayed at or above
13.33 GiB and admission availability at or above 8.94 GiB. Peak campaign cgroup
use was 19.06 GiB under `MemoryMax=28G`; cgroup `high`, `max`, `oom` and
`oom_kill` counters stayed at zero. The `tj` temperature ranged from 47.7 to
58.7 °C. GPU clock observations ranged from 306 MHz to 1,300.5 MHz and CPU
observations from 729.6 to 2,201.6 MHz; clocks were dynamic. EMC clock readback
was denied. Raw tegrastats power rails are retained, but energy is not
request-attributed. No default or serving profile changed.

Reproduce from the repository root on the same Orin setup with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/mtp_kv_workload_screen.py \
  --config bench/results/2026-10-16-phase5-coder-mtp-window-screen/config.json \
  --workloads bench/results/2026-10-16-phase5-coder-mtp-window-screen/workloads.json \
  --warmup-workloads bench/results/2026-10-16-phase5-coder-mtp-window-screen/warmup-workloads.json \
  --output bench/results/2026-10-16-phase6-coder-mtp-kv-workload-screen-reproduction/campaign \
  --workload-cells coder-mtp-retrieval-short-512 coder-mtp-retrieval-near-limit-7501 \
  --kvs fp16 int8 --windows 0 4 --blocks 3 --seed 20261023 --first-port 19450

python3 tools/integration/audit_mtp_kv_screen.py \
  bench/results/2026-10-16-phase6-coder-mtp-kv-workload-screen-reproduction/campaign/campaign.json \
  --output bench/results/2026-10-16-phase6-coder-mtp-kv-workload-screen-reproduction/residency-audit.json
```

The complete raw requests, service logs, per-arm configurations, memory and
clock samples, tegrastats, supervisor results, campaign design and
residency-filtered analysis are retained in this directory. The audit utility
and its unit tests are in `tools/integration/audit_mtp_kv_screen.py` and
`tools/integration/test_audit_mtp_kv_screen.py`. This screen does not close
Phase 6: residency-matched follow-up screening and at least seven independent
held-out confirmation repetitions are still required for any selected effect.
