# Coder IQ1_M long-prompt cache confirmation (in progress)

This seven-block paired confirmation compares requested expert-cache budgets of
1500 and 3000 MiB at a fixed configured context of 16,384 tokens. It uses a
held-out retrieval-and-sum prompt distinct from the preceding cache/context
screen. Each independent service cell has one warmup and three measured requests;
cache order is randomized within each block. MTP, prompt cache and adaptive swaps
are disabled; KV is FP16, prefill chunk is 64 and the worker pool is eight.

The task is formatted to exactly 7,501 prompt tokens. It asks for the exact answer
`EARLY=ALPINE-HARBOR-284, MIDDLE=COBALT-MAPLE-571, LATE=VIOLET-COMET-638,
SUM=1493`; the expected completion is 48 tokens. The model is
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. The binary and configuration
identity are recorded in [design.json](design.json). Models remain under
`~/models/strata-orin-validation/Coder-GGUF`.

The existing Phase 6 screen showed a descriptive 7–8% cache-size effect on
median client request time, but it used three screening blocks and a different
prompt. Do not combine those values with this confirmation. The confirmation is
not complete until all seven blocks pass exact-answer and token-count checks,
physical host and admission headroom stay at or above six GiB, cgroup limits and
events are audited, and paired block bootstrap intervals are calculated. Clocks
are sampled read-only; energy is not measured. No profile or default is promoted
by this experiment alone.

Block 1 is complete: all eight requests (warmup and three measurements in each of
two cells) passed, with exact 7,501/48 prompt/completion counts. Median client
time was 332.4 s at 1500 MiB and 310.7 s at 3000 MiB (single-block descriptive
comparison). Minimum host/admission availability was 17.78/17.09 GiB and
14.18/14.18 GiB, respectively; cgroup pressure and OOM event counters were zero.
This is one pair, not inferential evidence.

Block 2 is running. Its 1500 MiB arm has passed the warmup and first two measured
requests; the third request is in progress. See `per-cell-scopes/` for raw request,
supervisor, memory and clock records. The runner starts at block 2 because block
1 is already complete; it preserves randomized seeds and does not overwrite the
completed pair.

Block 2 is now complete. Both cells passed their warmup and all three measured
requests with exact answers and 7,501/48 token counts. Median client time was
333.6 s at 1500 MiB and 309.7 s at 3000 MiB. Minimum host/admission availability
was 17.88/16.58 GiB and 14.20/14.20 GiB, respectively; the observed 28-GiB
cgroups recorded zero low/high/max/OOM/OOM-kill events. This remains one
additional paired block, not a standalone inferential result.

Block 3 has started with cache1500 first in its randomized order. Six of the
planned fourteen service cells are now complete; the campaign-level conclusion
and bootstrap analysis remain pending.

Block 3's 1500-MiB arm has completed successfully: three exact measured
responses, median client time 333.2 s, minimum host/admission availability
17.80/16.47 GiB, with zero sampled cgroup events. Its paired 3000-MiB arm has
started. The first three measured 1500-MiB block medians are 332.4, 333.6, and
333.2 s; these are descriptive and the planned seven-block analysis is still
pending.

Block 3 is now complete. Both cells passed one warmup and three measurements
with exact answers and 7,501/48 token counts. Median client time was 333.2 s at
1500 MiB and 309.6 s at 3000 MiB, a 7.1% lower median in this single pair.
Minimum host/admission availability was 17.80/16.47 GiB and 14.17/14.17 GiB;
all sampled cgroup event counters remained zero. This pair is descriptive.
Block 4 has started with its randomized first arm.

Across the first three completed paired blocks, the 3000-MiB arm's descriptive
improvements versus 1500 MiB were 6.75%, 7.15%, and 7.10% for client total
time; prompt throughput was 7.46% higher in each block, and decode throughput
was 9.17%, 9.92%, and 10.00% higher. These are three observed block effects;
uncertainty and any conclusion remain pending the planned seven-block audit.

Block 4 is complete. Both cells passed one warmup and three measured requests
with the exact 7,501/48-token task answer. Median client time was 332.9 s at
1500 MiB and 309.2 s at 3000 MiB (7.12% lower for the larger cache in this
pair). Minimum host/admission availability was 17.71/16.87 GiB and
14.14/14.14 GiB, respectively; all cgroup pressure and OOM event counters
were zero. The four paired-block effects so far are descriptive; the planned
seven-block bootstrap and campaign audit remain pending.

Block 5 is complete. Both cells passed one warmup and all three measured
requests with exact answers and token counts. Median client time was 333.5 s at
1500 MiB and 310.1 s at 3000 MiB (7.02% lower for the larger cache in this
pair). Minimum host/admission availability was 17.67/16.00 GiB and
14.15/14.15 GiB, respectively; all sampled cgroup pressure/OOM counters were
zero. This remains a descriptive paired effect; the planned seven-block
analysis is pending. Across the first five pairs, client-total improvements
were 6.75%, 7.15%, 7.10%, 7.12% and 7.03% (median 7.10%); treat this as an
interim descriptive summary, not the planned seven-block inference.

Block 6 is complete. Both cells passed one warmup and all three measured
requests with exact answers and token counts. Median client time was 332.6 s at
1500 MiB and 309.3 s at 3000 MiB (6.99% lower for the larger cache in this
pair). Minimum host/admission availability was 17.76/16.25 GiB and
14.02/14.02 GiB, respectively; all sampled cgroup pressure/OOM counters were
zero. This is a descriptive paired effect; the planned seven-block analysis is
pending.

Block 7 has started in randomized order with the 1500-MiB cell. The campaign
analyzer remains intentionally incomplete until both cells in this final pair
pass all workload and telemetry checks. Its 1500-MiB warmup passed in 344.4 s
with the exact expected answer and token counts, and all three measurements
passed in 335.0, 333.8 and 331.3 s (median 333.8 s). Minimum host/admission
availability was 17.89/17.76 GiB, with zero cgroup events. The paired 3000-MiB
cell's warmup passed in 321.2 s with the exact expected answer and token
counts; all three measured requests passed in 309.7, 310.1 and 310.3 s
(median 310.1 s). Minimum host/admission availability was 14.05 GiB, and all
sampled cgroup pressure/OOM counters remained zero. The seven-block campaign
audit passed: the 3000-MiB cache improved paired median client total time by
7.10% (95% paired-block bootstrap interval 6.99%–7.15%); prompt and decode
throughput improved by 7.46% and 9.17%, respectively. Across all cells,
minimum host/admission availability was 14.02 GiB and cgroup pressure, limit
and OOM event counters remained zero. This result applies to the held-out
7,501-token retrieval/arithmetic workload with context 16,384, Coder IQ1_M,
MTP off, FP16 KV and the recorded runtime configuration; it does not establish
that a larger cache improves other workloads or settings. The campaign wrapper
encountered a post-cell shell error after the last cell finished, so final
completion is verified directly by the cell manifests and passing analyzer.
The wrapper then reran successfully and verified all seven blocks without
modifying the results. A separate analysis of the retained tegrastats samples
estimated named-rail energy in all 42 measured request windows. Paired
block-median `VIN_SYS_5V0` energy per output token was 6.94% lower at 3,000 MiB
(95% interval 6.61%–7.08% lower); `VDD_GPU_SOC` was 4.38% lower (4.26%–4.51%),
and `VDD_CPU_CV` was 21.69% lower (21.64%–22.52%). These rails are separate,
include board idle/background draw and are not process-attributed. See
[`analyze_rail_energy.py`](analyze_rail_energy.py) and
[`rail-energy.json`](rail-energy.json) for request windows and calculation
details.
