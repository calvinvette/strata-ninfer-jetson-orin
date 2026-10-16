# Coder IQ1_M fixed-cache MTP2 near-limit recheck — Orin — 2026-10-16

This three-block paired recheck followed a residency mismatch in the original
near-limit screen. It compared MTP off with MTP2 on the same 7,501-token
retrieval prompt at 8K context, FP16 KV and a 2,600-slot requested expert-cache
cap. All six fresh services reported the same actual residency: 3,378 expert
slots (6,600 MiB). Adaptive swaps and prompt cache were disabled; each service
received the same 512-token warmup and one measured request. Runs were
randomized within blocks under a 28-GiB cgroup and the six-GiB physical
availability floor.

All six requests passed and returned the exact oracle answer:
`EARLY=PLUM-STATIC-614, MIDDLE=GLACIER-KEY-203, LATE=FENNEL-ORBIT-589`.
MTP2 drafted/accepted 19/18 tokens in each request. Paired decode-rate changes
for blocks 0–2 were +0.35%, −76.66% and −2.35%, giving a median of −2.35% and a
three-block bootstrap 95% interval of −76.66% to +0.35%. The interval is very
wide because block 1's MTP2 request generated 38 tokens in 12,768 ms (2.98
tokens/s), compared with about 3,000 ms (12.6–12.9 tokens/s) in the other five
paired requests. Prompt throughput in that block was 23.72 versus 23.82 tokens/s,
so it does not explain the decode-only pause. The stream records a 9.92-second
gap between two output deltas. One-second tegrastats samples show a brief CPU/GPU
activity burst near that pause, but no sustained clock or thermal change; its
cause is not isolated. The timing checks pass for matched residency and KV,
but this screen does not support a reliable MTP2 performance conclusion.

Median client request time increased 3.47% in the three pairs. The long prompt
dominates request time, and the small sample does not qualify an end-to-end
effect. Treat these measurements as a diagnostic screen only; they do not
confirm MTP2 quality or support a profile recommendation.

Across 2,200 one-second supervisor samples, minimum host availability was
14.26 GiB and minimum admission availability was 9.13 GiB. All runs passed the
six-GiB floor; sampled cgroup `high`, `max`, `oom` and `oom_kill` counters were
zero. Clocks were dynamic, energy was not request-attributed and EMC readback is
not claimed. Raw paired metrics, requests, engine logs, memory samples and
tegrastats are retained in this directory.

The exact configuration, command and seed are recorded in
[`../mtp2-fixed-cache-config.json`](../mtp2-fixed-cache-config.json),
[`../mtp2-fixed-cache-command.txt`](../mtp2-fixed-cache-command.txt), and
[`campaign.json`](campaign.json).
