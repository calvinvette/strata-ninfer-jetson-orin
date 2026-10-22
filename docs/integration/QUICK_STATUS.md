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
is also open. The latest Orin CUDA regression suite passed 130 tests with two
optional IQ-fixture tests skipped; integration Python discovery passed 163/163,
and focused accepted-prefix, verifier, batch and graph tests passed. The latest
seven shared-source files were rebuilt from a fresh isolated snapshot for HIP
and SYCL on maestro1 with two jobs; both `strata --help` checks returned zero.
This is x86 compile/link and CLI-startup evidence only, not accelerator runtime
or Orin performance evidence. Build/source hashes are in the linked backend
record in [STATUS](STATUS.md).

## Performance observed

These results are specific to the tested Orin build, model and workload. No
candidate setting has been promoted to a default.

| Experiment | Measured result | Scope |
| --- | --- | --- |
| Expert cache × context, Coder IQ1_M, held-out 7,501-token task, seven same-day blocks | 3,000 vs 1,500 MiB requested cache reduced median client latency 7.95% at 8K context (paired 95% interval 7.93%–15.11%) and 7.71% at 16K (7.23%–7.82%). Cache-by-context interaction was +1.12% (0.22%–8.58%). | MTP off, FP16 KV, exact 48-token answer; one long-task profile. [Report](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/README.md) |
| Expert cache, short Coder task, seven blocks | 3,000 vs 1,500 MiB reduced median client latency 12.83%; TTFT fell 13.47%, with prompt/decode throughput up 15.77%/10.24%. | Short task only; see [STATUS](STATUS.md). |
| MTP × KV, long Coder task, seven-block confirmation | MTP4 reduced decode throughput about 9% across FP16/INT8 KV; client latency increased about 0.6%/1.0%. | No MTP/KV setting promoted; workload and energy tradeoffs remain. See [STATUS](STATUS.md). |
| Prefill chunk × expert cache, Q2_0 near-limit retrieval, seven held-out blocks | Chunk 128 reduced median request time 59.54% at 3,000 slots and 59.74% at 3,500 slots; all 28 requests returned the exact 41-token answer after 7,506 prompt tokens. | Cache × chunk interaction interval included zero; no general default. [Report](../../bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/README.md) |

The [batch-MTP graph lifecycle diagnostic](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md)
admitted eight slots and captured 16 layouts under the default 64-layout cap,
so that initial run did not exercise eviction. A separate opt-in cap-1 test
completed eight concurrent requests and observed 14 LRU evictions and 11
recaptures across four repeated layout keys; all requests returned six tokens,
with 16.50 GiB minimum available RAM and zero cgroup memory events. The default
cap remains 64, confirmed by a no-override run whose six-token single-request
output matched serial MTP2. A supervised 80-request stress exercised 88 unique
layouts: the first eviction came at layout 64, and 26 evictions occurred in
total. All requests completed, minimum host availability was 11.12 GiB, and
784 supervisor samples showed zero cgroup pressure or OOM events. This is
lifecycle and memory evidence only, not a correctness or speed result. Outputs
in the original eight-prompt batch differed from
serial controls; a same-profile single-live follow-up matched serial MTP2,
while a two-request run still diverges at token 60 on slot 1 for MTP-enabled
and MTP-disabled batches. Full state capture corrected the earlier layer-6
pairing: at positions 71–72, each batch slot is closest to its corresponding
isolated serial prompt, but state arrays differ broadly despite equal short
outputs. At position 127, all 248,320 verifier logits differ and the top-two
ranking reverses. Batch-MTP remains unqualified; no throughput claim is made.

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
or adaptive recovery. Opt-in cap-1 and default cap-64 batch graph
eviction/recapture now pass lifecycle stress coverage.
See the [owner transition](../../bench/results/2026-10-22-phase5-coder-longchain-owner-capture/README.md),
[raw state](../../bench/results/2026-10-22-phase5-coder-long-chain-raw-state-pair-pos767/README.md),
and [API cancellation](../../bench/results/2026-10-22-phase5-coder-api-cancellation-current-source/README.md)
records.

## Near-term direction

1. Continue resolving batch-MTP output divergence: capture MTP2 committed state
   from prompt boundary through its first divergent decode window, then isolate
   the first recurrence or verifier operation that changes the row. Extend
   accepted-prefix direct-state and long-chain
   recovery coverage, widen cancellation boundaries beyond the passing Coder
   MTP4 decode/prefill points, and keep adaptive migration opt-in until its
   long-chain state contract is bounded.
2. Continue Phase 6 only on qualified candidates: finish supported interactions,
   held-out confirmation and response-model diagnostics, then report energy and
   Pareto tradeoffs with physical-memory, clock and uncertainty context.
3. Update detailed status and integration notes as evidence lands. Commit and
   push when each phase gate is actually complete; preserve the six-GiB host
   headroom and separate workspace reserve throughout.

Models stay under `~/models/`; build products, credentials and local agent
configuration stay out of Git. Do not combine host RAM and CUDA capacity into a
single memory figure.
