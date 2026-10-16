# Coder IQ1_M near-limit MTP window screen — Orin — 2026-10-16

This randomized three-block screen compared MTP off/2/3/4 for one 7,501-token
retrieval prompt at an 8,192-token context. Every arm used the same Strata
binary, Coder IQ1_M GGUF shards, expert profile, FP16 KV format, 3,000 requested
expert-cache slots, prefill chunk 64, eight workers and dynamic clocks. The
screen harness disabled adaptive swaps and prompt cache. Each cell started a
fresh service, issued one 512-token warmup and one measured request, and ran
under a 28-GiB cgroup with a six-GiB physical-availability floor.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, quantization IQ1_M; shard hashes
are in [`../model-sha256.txt`](../model-sha256.txt). The MTP runtime is from the
upstream base checkpoint `Qwen/Qwen3.8-Flash-Next`, revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`; it is not Coder-specific. Runtime
hashes, source/binary identity and experiment inputs are in
[`../mtp-runtime-sha256.txt`](../mtp-runtime-sha256.txt) and
[`../inputs.json`](../inputs.json).

All 12 requests passed and returned the same exact answer:
`EARLY=PLUM-STATIC-614, MIDDLE=GLACIER-KEY-203, LATE=FENNEL-ORBIT-589`.
Each arm generated 38 tokens. MTP2 drafted/accepted 19/18 tokens per request;
MTP3 drafted/accepted 28/24; MTP4 drafted/accepted 30/27. The paired timing
screen results are:

| Window | Paired decode-rate changes by block | Median and three-block bootstrap interval | Timing qualification |
|---:|---:|---:|---|
| 2 | +0.16%, +0.14%, −1.83%* | Not reported across all blocks | Failed: block 2 actual expert residency differed |
| 3 | −2.38%, −0.30%, −1.62% | −1.62%; −2.38% to −0.30% | Qualified screen |
| 4 | +8.03%, +7.65%, +7.50% | +7.65%; +7.50% to +8.03% | Qualified screen |

`*` In block 2 the MTP-off service loaded 3,903 experts (7,615 MiB), while
MTP2 loaded 3,782 (7,380 MiB). Its expert cache therefore had 121 fewer
resident slots, so that pair is excluded from the MTP2 timing estimate. The
other two MTP2 pairs used 3,903 slots on both sides. The cause of this
single-run capacity difference is not isolated; it is retained as an explicit
failed comparability check in [`campaign.json`](campaign.json).

MTP4 raised median paired decode throughput by 7.65% in this screen, but the
client request-time changes were +0.19%, −0.06% and +10.09% across the blocks.
The long prompt dominates request time, so the decode-rate result does not show
an end-to-end request win. MTP3's median decode rate was lower than MTP-off.
These three-block estimates are screens, not held-out confirmation and not
profile recommendations. This covers one retrieval task and FP16 KV only; it
does not establish general long-context quality or a serving default.

Across 4,310 one-second supervisor samples, minimum host availability was
13.30 GiB and minimum admission availability was 8.93 GiB. All 12 runs passed
the six-GiB guard; sampled cgroup `high`, `max`, `oom` and `oom_kill` counters
were zero. Clocks were dynamic, energy was not request-attributed, and EMC
readback is not claimed. Raw memory samples, tegrastats, request records and
engine logs are retained for each block.

Reproduction command:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/mtp_window_screen.py \
  --config bench/results/2026-10-16-phase5-coder-mtp-window-screen/config.json \
  --workloads bench/results/2026-10-16-phase5-coder-mtp-window-screen/workloads.json \
  --warmup-workloads bench/results/2026-10-16-phase5-coder-mtp-window-screen/warmup-workloads.json \
  --output bench/results/2026-10-16-phase5-coder-mtp-window-screen/screen-near-limit \
  --workload-cell coder-mtp-retrieval-near-limit-7501 \
  --windows 0 2 3 4 --blocks 3 --seed 20261017 --first-port 19140
```

The raw per-block paired metrics and qualification failures are in
[`campaign.json`](campaign.json).

The initial MTP2 comparison had one block with unequal residency. A separate
[fixed-cache MTP2 recheck](../screen-near-limit-mtp2-fixed-cache/README.md)
matched 3,378 slots across all pairs, but one MTP2 run had a 9.92-second
streaming gap. Its three-block interval is too wide for a performance conclusion.
