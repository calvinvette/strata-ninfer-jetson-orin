# Coder IQ1_M short-task MTP window screen — Orin — 2026-10-16

This three-block randomized screen compared MTP off/2/3/4 for one 512-token
retrieval-plus-arithmetic prompt at an 8,192-token context. Every arm used the
same Strata binary, Coder IQ1_M GGUF shards, expert profile, FP16 KV format,
3,000 requested expert-cache slots, prefill chunk 64, eight workers and dynamic
clocks. The screen harness disabled adaptive swaps and prompt cache. Each cell
started a fresh service, issued one 512-token warmup and one measured request,
and ran under a 28-GiB cgroup with a six-GiB physical-availability floor.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, quantization IQ1_M; shard hashes
are in [`../model-sha256.txt`](../model-sha256.txt). The MTP runtime is from the
upstream base checkpoint `Qwen/Qwen3.8-Flash-Next`, revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`; it is not Coder-specific, and its
hashes are in [`../mtp-runtime-sha256.txt`](../mtp-runtime-sha256.txt). The
binary SHA256, source revision and full experiment inputs are recorded in
[`../inputs.json`](../inputs.json).

All 12 requests passed and returned the same exact answer:
`EARLY=CITRUS-AXLE-431, MIDDLE=MARBLE-THICKET-782, LATE=OXIDE-KITE-265, SUM=1478`.
Each arm generated 47 tokens. MTP2 drafted/accepted 24/23 tokens per request;
MTP3 drafted/accepted 34/31; MTP4 drafted/accepted 39/34. Paired decode-rate
results against MTP off were:

| MTP window | Median paired decode-rate change | Three-block bootstrap interval | Paired blocks |
|---:|---:|---:|---:|
| 2 | +7.40% | +6.01% to +12.29% | 3 |
| 3 | +11.84% | +9.41% to +17.04% | 3 |
| 4 | +13.61% | +7.38% to +14.08% | 3 |

These intervals are screening estimates from only three paired blocks. They
do not qualify a preferred window or a default. The result covers one short
task and FP16 KV only. The separate [near-limit prompt screen](../screen-near-limit/README.md)
has its own paired-capacity qualification details; further KV formats,
held-out confirmation repetitions and broader quality checks remain necessary
under Phases 5–7.

Across the 12 supervised runs, minimum host availability was 13.29 GiB and
minimum admission availability was 9.79 GiB. All runs passed the six-GiB guard;
the saved per-run memory samples and supervisor records retain the raw telemetry.
Clocks were dynamic, energy was not request-attributed and EMC readback is not
claimed.

Reproduction command:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/mtp_window_screen.py \
  --config bench/results/2026-10-16-phase5-coder-mtp-window-screen/config.json \
  --workloads bench/results/2026-10-16-phase5-coder-mtp-window-screen/workloads.json \
  --warmup-workloads bench/results/2026-10-16-phase5-coder-mtp-window-screen/warmup-workloads.json \
  --output bench/results/2026-10-16-phase5-coder-mtp-window-screen/screen-short \
  --workload-cell coder-mtp-retrieval-short-512 \
  --windows 0 2 3 4 --blocks 3 --seed 20261016 --first-port 19100
```

Raw paired comparisons are in [`campaign.json`](campaign.json); each block's
requests, engine log, supervisor memory samples and tegrastats are retained
beside it.
