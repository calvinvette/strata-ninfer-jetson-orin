# Coder MTP × KV × prompt-length screen — 1,500 MiB cache — Orin

This randomized three-block screen crossed MTP off/MTP4, FP16/INT8 KV and
512/7,501-token retrieval prompts on the same Coder IQ1_M artifact and candidate
binary, with the expert cache budget set to 1,500 MiB. All 24 fresh-service
arms passed their exact retrieval answer, reported the requested KV format and
actual prompt length, and passed the memory guard. This is a screening result;
it does not qualify a serving profile or close Phase 6.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, IQ1_M, pinned
at revision `5348543e0147355ac9cbcb031184a3546350988e`. The binary SHA256 is
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`, built
from source commit `9dac82fdc3475227fa6eb34125e8160e78efd5c2`. MTP used the
separately sourced upstream base-checkpoint artifact used in the Phase 5 Coder
checks. Other settings were 8 workers, prefill chunk 64, 8K context, disabled
prompt cache and dynamic clocks.

The timing audit requires passing MTP pairs from the same local calendar day
with matching KV, actual prompt length and identical resident expert slots and
cache MiB. Ten of 12 cell pairs qualified; two were excluded: block 1 FP16
near-limit had 1,784/3,516 MiB versus 1,934/3,807 MiB residency, and block 1
INT8 short straddled midnight (Oct 16/17). The ten qualified pairs all had
1,934 slots / 3,807 MiB. The qualified MTP4 decode-throughput changes were
FP16 short +13.42% (n=3), FP16 long +20.19% (n=2), INT8 short +14.20% (n=2),
and INT8 long +6.31% (n=3). Client total-time changes were −3.14%, +0.24%,
+2.11% and +0.50%, respectively. These small-cell estimates are descriptive;
they are not seven-repetition confirmation intervals. The interaction audit
qualifies only two complete three-way blocks, so it cannot support a stable
three-way response estimate.

Across 5,156 one-second samples, minimum host availability was 17.07 GiB and
minimum admission availability was 6.05 GiB. Peak supervised cgroup use was
21.95 GiB under `MemoryMax=28G`; `high`, `max`, `oom` and `oom_kill` event
counters stayed at zero. The admission margin was close to the required
six-GiB floor. Clocks were dynamic; EMC readback was denied and the retained
power samples are not request-attributed energy. No default or serving profile
changed.

The one-block randomized follow-up is stored separately at
[`2026-10-17-phase6-coder-mtp-kv-followup-budget1500`](../2026-10-17-phase6-coder-mtp-kv-followup-budget1500/).
It is needed to restore the third qualified replicate for the affected cells;
the follow-up report will state whether all its pairs qualify. Even with that
block, the campaign is screening evidence only. Phase 6 still requires at
least seven independent held-out confirmation repetitions for selected
effects and the remaining plan interactions.

Reproduce this screen from the repository root on the same Orin setup with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/mtp_kv_workload_screen.py \
  --config bench/results/2026-10-16-phase5-coder-mtp-window-screen/config.json \
  --workloads bench/results/2026-10-16-phase5-coder-mtp-window-screen/workloads.json \
  --warmup-workloads bench/results/2026-10-16-phase5-coder-mtp-window-screen/warmup-workloads.json \
  --output bench/results/2026-10-16-phase6-coder-mtp-kv-workload-screen-cache1500/campaign \
  --workload-cells coder-mtp-retrieval-short-512 coder-mtp-retrieval-near-limit-7501 \
  --kvs fp16 int8 --windows 0 4 --blocks 3 --seed 20261024 --first-port 19500 \
  --expert-cache-budget 1500

python3 tools/integration/audit_mtp_kv_screen.py \
  bench/results/2026-10-16-phase6-coder-mtp-kv-workload-screen-cache1500/campaign/campaign.json \
  --run-root bench/results/2026-10-16-phase6-coder-mtp-kv-workload-screen-cache1500/campaign \
  --output bench/results/2026-10-16-phase6-coder-mtp-kv-workload-screen-cache1500/residency-audit.json
```

The campaign directory retains raw requests, service logs, per-arm settings,
memory and clock samples, tegrastats, supervisor results and randomized design.
The audit tool and its tests are in `tools/integration/audit_mtp_kv_screen.py`
and `tools/integration/test_audit_mtp_kv_screen.py`.
