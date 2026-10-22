# Quick status

Updated: 2026-10-22

This is a short orientation to the integration. The [plan](PLAN.md) defines
phase gates; the detailed [status](STATUS.md) is the evidence record, and the
[measurement protocol](BENCHMARKS.md) defines how to interpret results. The
[porting notes](PORTING_NOTES.md) preserve lessons for repeating this work with
Strata and Splash.

## Overall status

Phases 0–4 are complete for their documented scopes. Phase 7 is complete for
its bounded Orin qualification matrix. Phases 5 and 6 remain open, so Phase 8
is also open. Current-source Orin regression checks pass: CTest 132/132 (two
optional IQ-fixture tests skipped), integration Python discovery 163/163, and
the focused accepted-prefix, verifier, MTP verifier, batch, and graph-trace
checks 7/7. The current modified shared source compiles and links for both HIP
and SYCL on maestro1, with both help invocations exiting successfully. Those
remote checks are build evidence only, not runtime or Orin performance
evidence.

## Performance observed

These results are specific to the tested Orin build, model and workload. No
candidate setting has been promoted to a default.

| Experiment | Measured result | Scope |
| --- | --- | --- |
| Expert cache × context, Coder IQ1_M, held-out 7,501-token task, seven same-day blocks | 3,000 vs 1,500 MiB requested cache reduced median client latency 7.95% at 8K context (paired 95% interval 7.93%–15.11%) and 7.71% at 16K (7.23%–7.82%). Cache-by-context interaction was +1.12% (0.22%–8.58%). | MTP off, FP16 KV, exact 48-token answer; one long-task profile. [Report](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/README.md) |
| Expert cache, short Coder task, seven blocks | 3,000 vs 1,500 MiB reduced median client latency 12.83%; TTFT fell 13.47%, with prompt/decode throughput up 15.77%/10.24%. | Short task only; see [STATUS](STATUS.md). |
| MTP × KV, long Coder task, seven-block confirmation | MTP4 reduced decode throughput about 9% across FP16/INT8 KV; client latency increased about 0.6%/1.0%. | No MTP/KV setting promoted; workload and energy tradeoffs remain. See [STATUS](STATUS.md). |
| Prefill chunk × expert cache, Q2_0 near-limit retrieval, seven held-out blocks | Chunk 128 reduced median request time 59.54% at 3,000 slots and 59.74% at 3,500 slots; all 28 requests returned the exact 41-token answer after 7,506 prompt tokens. | Cache × chunk interaction interval included zero; no general default. [Report](../../bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/README.md) |

The new [batch-MTP graph lifecycle diagnostic](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md)
admitted eight slots and captured 16 distinct layouts, below the 64-layout
pool limit, so it did not exercise eviction or recapture. Outputs differed
from the serial target-only control on 6/8 prompts and from the serial MTP2
control on 7/8. A same-profile single-live-request follow-up matched serial
MTP2 exactly, narrowing the mismatch to multi-request interleaving or shared
batch windows. A two-request run reproduces it: slot 0 matches serial MTP2,
while slot 1 diverges at token 60. MTP-disabled batch also differs from serial
target-only at slot 1, and batch-MTP differs from its matched target-only batch
at that token. The concurrent run retained at least 14.77 GiB available
physical RAM (11.39 GiB at admission), with zero scoped cgroup OOM events. It
is a correctness diagnostic, not a throughput comparison. Direct GDN capture
and a per-layer hash sweep show state equality at selected committed lengths,
followed by early decode drift: target-only rows first differ at positions 69
and 72, while the mapped MTP2 row first differs at 76. One target-only request
still returns identical 96-token text; the other first diverges at token 60.
At position 127, all 248,320 MTP verifier logits differ from serial and the
top-two ranking reverses. These are numerical correctness findings, not
throughput results. One serial process also changed the second prompt relative
to a fresh process, so state pairing uses the isolated control and that
request/session behavior needs separate investigation. Batch-MTP remains
unqualified.

Correctness work has found a separate adaptive-recovery issue. In a 256-token
short–short–short Coder IQ1_M chain, adaptive recovery differed on 237/256
tokens, while delayed control was bit-exact at captured positions. At position
515, layer-21 expert 132 changes CPU→GPU ownership on the same input and route;
its owner-specific service rows match an independent oracle, but the CPU/GPU
rows differ in all 2,560 values (relative L2 0.016716). This explains one
contribution, not all later persistent-state drift. Current-source Coder MTP4
decode cancellation matched all 11 state fingerprints at four accepted-prefix
boundaries; early-prefill cancellation also matched all 11 recovery state
fingerprints. These qualify the tested points, not every cancellation boundary
or adaptive recovery. Real model graph-pool resize/recapture still needs
coverage.
See the [owner transition](../../bench/results/2026-10-22-phase5-coder-longchain-owner-capture/README.md),
[raw state](../../bench/results/2026-10-22-phase5-coder-long-chain-raw-state-pair-pos767/README.md),
and [API cancellation](../../bench/results/2026-10-22-phase5-coder-api-cancellation-current-source/README.md)
records.

## Near-term direction

1. Continue resolving batch-MTP output divergence before interpreting graph
   results: capture the MTP2 committed state from prompt boundary through the
   first divergent decode window, then isolate the first batch recurrence or
   verifier operation that changes the row. Drive more than 64 distinct
   layouts to observe actual LRU eviction and recapture.
   Continue Phase 5 transaction coverage by extending accepted-prefix checks to direct
   persistent-state and long-chain recovery contracts, widen cancellation
   boundaries beyond the passing Coder MTP4 decode/prefill points, and test real
   graph-pool resize with safe recapture. Keep adaptive migration opt-in until
   long-chain state behavior has a stated and tested contract.
2. Continue Phase 6 only on qualified candidates: finish supported interactions,
   held-out confirmation and response-model diagnostics, then report energy and
   Pareto tradeoffs with physical-memory, clock and uncertainty context.
3. Update detailed status and integration notes as evidence lands. Commit and
   push when each phase gate is actually complete; preserve the six-GiB host
   headroom and separate workspace reserve throughout.

Models stay under `~/models/`; build products, credentials and local agent
configuration stay out of Git. Do not combine host RAM and CUDA capacity into a
single memory figure.
