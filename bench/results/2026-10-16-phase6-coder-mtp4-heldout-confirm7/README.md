# Coder IQ1_M held-out MTP4 confirmation — Orin — 2026-10-16

This seven-block paired confirmation compared MTP off with MTP4 on a new
512-token retrieval-plus-arithmetic prompt for the Coder IQ1_M model. Each arm
started a fresh service, ran the same distinct warmup request, then ran one
measured request with prompt caching disabled. The harness randomized arm order
within each block and required matching actual expert residency, KV format,
model and non-MTP configuration.

All 14 requests returned the exact independently specified answer:
`EARLY=EMBER-VAULT-317, MIDDLE=SILVER-MAPLE-846, LATE=TIDAL-COPPER-529, SUM=1692`.
The tokenizer rendered exactly 512 prompt tokens in every run, and every arm
returned 45 completion tokens. `verify_campaign.py` checks each answer against
the separately recorded oracle, validates every pair's actual residency and KV,
and checks the physical-memory floor and cgroup memory events. It passed all
checks.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, IQ1_M,
pinned at revision `5348543e0147355ac9cbcb031184a3546350988e`; the two shard
hashes are retained in `model-sha256.txt`. MTP uses the separate base checkpoint
`Qwen/Qwen3.8-Flash-Next`, revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`; it is not Coder-specific. Its
runtime hashes are in `mtp-runtime-sha256.txt`. The service binary SHA256 is
`c07cf3f634788d055316cbf345a2fa17dd66449cb5ddd8690781dbbd72403c88`, built
from source commit `0464d128`. The repository HEAD at campaign setup was
`925ffecb`; model files and runtime remain under `~/models/strata-orin-validation/`.

| Measure | MTP4 vs MTP-off median paired change | Paired-block bootstrap 95% interval |
| --- | ---: | ---: |
| Decode throughput | +3.65% | +2.25% to +4.85% |
| Client request time | +1.27% | −0.59% to +1.67% |
| Client TTFT | +1.93% | −0.08% to +2.40% |
| Prompt throughput | −1.95% | −2.34% to +0.02% |

MTP4 drafted 42 and accepted 33 tokens in each measured request. The decode
rate increase is repeatable for this held-out task, but request-time results do
not establish an end-to-end win: the prompt dominates these short completions,
and its throughput was slightly lower with MTP4. This is a one-task confirmation
for one model artifact, FP16 KV and an 8K context. It does not qualify a general
MTP profile or compare the Coder artifact against Q2_0 or another engine.

Across 1,108 one-second memory samples, minimum host availability was 13.31 GiB
and minimum effective admission availability was 9.21 GiB. All sampled cgroup
`low`, `high`, `max`, `oom` and `oom_kill` event counters were zero. The six-GiB
floor held in every run. Clocks remained dynamic and were not sampled with a
clock-readback tool; tegrastats and raw power rails are retained, but energy was
not attributed to individual requests. The campaign used `MemoryMax=28G` and
did not change power or clock settings.

Reproduce from the repository root on Orin with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/mtp_window_screen.py \
  --config bench/results/2026-10-16-phase6-coder-mtp4-heldout-confirm7/config.json \
  --workloads bench/results/2026-10-16-phase6-coder-mtp4-heldout-confirm7/workloads.json \
  --warmup-workloads bench/results/2026-10-16-phase6-coder-mtp4-heldout-confirm7/warmup-workloads.json \
  --output bench/results/2026-10-16-phase6-coder-mtp4-heldout-confirm7/campaign \
  --workload-cell coder-mtp4-heldout-retrieval-arithmetic-512 \
  --windows 0 4 --blocks 7 --seed 20261018 --first-port 19320

python3 bench/results/2026-10-16-phase6-coder-mtp4-heldout-confirm7/verify_campaign.py
```

The raw per-arm API records, server configurations, engine logs, supervisor
samples and tegrastats are retained under `campaign/`. This confirmation adds
one held-out Phase 6 cell; Phases 5–7 remain open.
