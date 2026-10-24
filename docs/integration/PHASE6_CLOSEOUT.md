# Phase 6 closeout — measured Orin factor domains

Phase 6 is complete for the tested Q2_0 and Coder IQ1_M workload/factor cells
listed here. Screens used randomized three-block designs and confirmations used
seven independent paired blocks where available. Outputs were checked against
task oracles; paired block bootstrap intervals are primary for confirmation.
No universal response model, Pareto winner, or runtime default is promoted.

| Interaction | Confirmation and result |
| --- | --- |
| Expert cache × context | Current-source Q2_0 and Coder IQ1_M held-out 2×2 confirmations covered 8K/16K contexts and the tested 1,500/3,000 or 3,000/5,000 cache arguments. All measured answers passed their exact task oracle. The cache/context interaction varied by artifact and workload; neither a generally faster cache nor a general context effect is claimed. See the [Coder confirmation](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/README.md) and [Q2_0 confirmation](../../bench/results/2026-10-18-phase6-q2-cache-context-current-source-confirm7/README.md). |
| Prefill chunk × cache | The held-out seven-block Coder IQ1_M 7,501-token confirmation passed all 28 cells. Chunk 128 reduced median client total time 67.71% at 1,500 requested slots and 68.72% at 3,000; the cache-by-chunk interaction was −3.13% (paired block-bootstrap 95% interval −5.43% to −1.93%). See the [confirmation](../../bench/results/2026-10-23-phase6-coder-prefill-cache-confirm7/README.md). |
| Workers × transfer | The seven-block held-out Coder IQ1_M confirmation passed all 28 cells. Four workers were slower than eight by median 7.36% with mapped reads and 6.50% with `pread`; `pread` reduced request time 2.72% at four workers and 1.94% at eight. The worker×transfer interaction interval included zero. See the [confirmation and scoped Pareto table](../../bench/results/2026-10-24-phase6-coder-worker-transfer-confirm7/README.md). |
| MTP × KV × workload | Screens crossed MTP windows with FP16/INT8 KV and short/near-limit prompts; held-out confirmations include seven-block short and long Coder cases. MTP3 improved short-task decode in the tested 512-token prompts but reduced long-task decode by 5.49% with FP16 KV and 4.19% with INT8 KV in the held-out 7,501-token confirmation. MTP4 improved short-task decode by 13.22%/13.72% for FP16/INT8 KV in its held-out task, while the long screen showed 10.95%/8.80% lower decode throughput. This workload dependence supports no MTP default. See [MTP3 long confirmation](../../bench/results/2026-10-24-phase6-coder-mtp3-kv-heldout-long-confirm7/README.md), [MTP4 short confirmation](../../bench/results/2026-10-24-phase6-coder-mtp4-heldout-short-confirm7/README.md), and [MTP4 length screen](../../bench/results/2026-10-24-phase6-coder-mtp4-kv-heldout-length-screen3/README.md). |
| Graph × speculation | The current-source Q2_0 seven-block task-qualified confirmation crossed captured/eager decode with MTP off/window 2 and passed all 28 cells and its task rubric. Graph/eager and graph×MTP request-time intervals included no effect; MTP2 raised request time and reduced decode throughput in both modes. See the [report](../../bench/results/2026-10-19-phase6-q2-graph-mtp-current-source-confirm7/README.md). |

## Pareto and energy limits

The worker×transfer confirmation produced a four-point nondominated set across
TTFT, request time, decode duration, sampled physical headroom, host NVMe
device-wide read deltas, and three named tegrastats rails. Per-cell host
headroom and request-aligned `nvme0n1` sector deltas were recovered from the
retained one-second supervisor telemetry; the method and values are recorded
in that campaign report. Device deltas include concurrent system I/O and are
not process-attributed. The cache×chunk confirmation also has a four-cell
descriptive view. These are workload-specific choices with different latency
and rail tradeoffs, not a global product frontier. Named rails include board
idle/background activity; they are neither process-attributed nor summed into
whole-device energy. The Coder long MTP3 exploratory log response model had
large residuals, so paired block bootstrap remains primary and the model is
not used for selection.

The tested domains meet the plan's bounded screening, held-out, uncertainty,
interaction and Pareto reporting requirements. Untested quantizations,
prompt families, larger cache/context ranges, cold-disk behavior, other boards,
process-attributed energy and a single preferred operating point remain outside
this closeout. Reopen Phase 6 before generalizing beyond these cells or changing
a default.
