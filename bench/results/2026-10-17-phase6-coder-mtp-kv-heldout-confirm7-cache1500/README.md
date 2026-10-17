# Coder IQ1_M held-out MTP × KV confirmation — Orin — 2026-10-17

This seven-block randomized confirmation crossed MTP off/MTP4 with FP16/INT8
KV on one held-out 512-token retrieval-plus-arithmetic task, using a 1,500 MiB
expert-cache budget. All 28 fresh-service requests returned the exact
independent answer, `EARLY=EMBER-VAULT-317, MIDDLE=SILVER-MAPLE-846,
LATE=TIDAL-COPPER-529, SUM=1692`, with 512 formatted prompt tokens and 45
completion tokens. All MTP4 runs drafted/accepted 42/33 tokens. Each block
passed in all four cells; every MTP pair matched 1,934 resident expert slots
(3,807 MiB), actual KV format, prompt length and local run date (Oct 17). No
cell was excluded from timing analysis.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, IQ1_M, pinned
at revision `5348543e0147355ac9cbcb031184a3546350988e`. Shard SHA256 values are
`e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad` and
`316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`. MTP is
the separate base checkpoint `Qwen/Qwen3.8-Flash-Next` at revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`; runtime file hashes are retained
in the prior [Coder MTP confirmation](../2026-10-16-phase6-coder-mtp4-heldout-confirm7/mtp-runtime-sha256.txt).
The candidate binary SHA256 is
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`, built
from source commit `9dac82fdc3475227fa6eb34125e8160e78efd5c2`. Campaign tooling
was at repository commit `b32228164eb51a482e3fc871a0330945f6f29541`.

| KV | MTP4 vs off median change | Paired-block bootstrap 95% interval |
| --- | ---: | ---: |
| FP16 decode throughput | +0.59% | +0.15% to +2.39% |
| FP16 client total time | −1.18% | −4.61% to +0.50% |
| INT8 decode throughput | +1.47% | +0.87% to +2.70% |
| INT8 client total time | −3.30% | −4.03% to +1.43% |
| INT8-vs-FP16 MTP decode interaction | +0.93% | −1.39% to +7.40% |
| INT8-vs-FP16 MTP client-time interaction | +0.58% | −4.86% to +1.66% |

MTP4's decode-rate change is small for this prompt, and neither KV format
shows an end-to-end request-time interval excluding zero. The held-out
MTP × KV interaction intervals also include zero. All blocks are retained: one
INT8/MTP-off arm had 7.70 decode tokens/s while its paired MTP4 arm had 12.23;
the other INT8/MTP-off arms were near 12.0. That pair produces a +55.09%
block-level decode interaction and shows the remaining timing variability.
It was not discarded because its correctness, residency and protocol checks
passed. These results do not justify a profile or default change.

The held-out task was previously used for a FP16-only MTP4 confirmation at a
3,000 MiB cache budget. Here it adds seven-block INT8-KV and matched-residency
MTP × KV coverage at 1,500 MiB; it is independent of the short/near-limit
retrieval prompts used in the cache-bounded screen, not a new task independent
of the earlier FP16 confirmation.

Across 1,984 one-second telemetry samples, minimum host availability was
17.09 GiB and minimum admission availability was 6.14 GiB, 0.14 GiB above the
six-GiB floor. Peak supervised cgroup use was 21.86 GiB under `MemoryMax=28G`;
`high`, `max`, `oom` and `oom_kill` counters were zero. GPU clocks ranged
306–1,300.5 MHz and CPU clocks 729.6–2,201.6 MHz; clocks were dynamic, and EMC
readback was denied. `tj` ranged 49.0–57.5 °C. Power-rail samples are retained,
but energy was not attributed to individual requests.

Reproduce from the repository root on the same Orin setup with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/mtp_kv_workload_screen.py \
  --config bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-confirm7-cache1500/config.json \
  --workloads bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-confirm7-cache1500/workloads.json \
  --warmup-workloads bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-confirm7-cache1500/warmup-workloads.json \
  --output bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-confirm7-cache1500/campaign \
  --workload-cells coder-mtp4-heldout-retrieval-arithmetic-512 \
  --kvs fp16 int8 --windows 0 4 --blocks 7 --seed 20261027 \
  --first-port 19700 --expert-cache-budget 1500

python3 tools/integration/audit_mtp_kv_screen.py \
  bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-confirm7-cache1500/campaign/campaign.json \
  --run-root bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-confirm7-cache1500/campaign \
  --output bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-confirm7-cache1500/residency-audit.json
```

The campaign and `residency-audit.json` retain exact answers, per-arm timing,
resident capacity, model/runtime identity, memory and clock telemetry and
block-level interaction values. This confirms the MTP × KV behavior for this
one Coder IQ1_M task and cache profile. Other workloads and the remaining
Phase 6 factors still need confirmation; no setting was promoted.
