# Quick status

Updated: 2026-10-22

This is a short orientation to the integration. The [plan](PLAN.md) defines
phase gates; the detailed [status](STATUS.md) is the evidence record, and the
[measurement protocol](BENCHMARKS.md) defines how to interpret results. The
[porting notes](PORTING_NOTES.md) preserve lessons for repeating this work with
Strata and Splash.

## Overall status

Phases 0–4 are complete for their documented scopes. Phase 7 is complete for
its bounded Orin qualification matrix. Phase 8 is complete for one bounded,
opt-in Q2_0 release profile; Phases 5 and 6 remain open for unresolved
accepted-state correctness and broader performance interactions. The latest
Orin CUDA regression suite passed 130 tests with two
optional IQ-fixture tests skipped; integration Python discovery passed 163/163,
and focused accepted-prefix, verifier, batch and graph tests passed. The latest
seven shared-source files were rebuilt from a fresh isolated snapshot for HIP
and SYCL on maestro1 with two jobs; both `strata --help` checks returned zero.
This is x86 compile/link and CLI-startup evidence only, not accelerator runtime
or Orin performance evidence. Build/source hashes are in the linked backend
or Orin performance evidence. Build/source hashes are in the linked backend
record in [STATUS](STATUS.md). See the [Phase 8 closeout](PHASE8_CLOSEOUT.md)
for the exact release scope and exclusions.

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

A new position-76 MTP2 comparison pairs rows by generated token. Prompt 0's
committed GDN state differs from its serial control in 26,965,859/29,417,472
values (relative L2 0.01823), first at model layer 4, despite an identical
64-token output. Prompt 1 did not produce a captured commit at that position.
The batch QSA hash hook stopped at state length 69, so it cannot rule out an
earlier QSA difference. This narrows the observed state onset for one row but
does not explain the two-live output mismatch or pass Phase 5. See the [state
follow-up](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

A 3,000 MiB cache-cap correctness diagnostic is now localized one layer
earlier: layer-10 experts 150 and 2 switch from VRAM to CPU on an otherwise
bit-identical activation and routing row. Independent same-input oracles
confirm the owner-specific outputs. The later layer-11 observation was
downstream of this change, so it is not a cache-only performance comparison.
Phase 5 remains open.

The current candidate also passed a 2026-10-22 bounded Phase 8 smoke: 7,498-token
8K-context retrieval plus same-service recovery, 130 CUDA CTests passed with two
optional fixture skips, and Python integration passed 163/163. This is
functional regression evidence, not a new timing confirmation. [Report](../../bench/results/2026-10-22-phase8-current-source-q2-profile-smoke/README.md).

A separate current-source MTP2 cancellation test matched all five committed
prefixes against two fresh references and recovered on the same service after
the client closed its stream. It strengthens one cancellation boundary set;
adaptive accepted-state drift and the two-live batch mismatch remain open.
[Report](../../bench/results/2026-10-22-phase5-coder-mtp2-cancel-state/README.md).

A separate two-live trace now connects one owner switch to persistent state:
at position 71, layer-1 expert 11 moves VRAM→CPU on an exact-matched activation,
and the first changed committed GDN state is model layer 2. Its weighted part
delta explains the combined MoE output to `3.23e-9` maximum residual; exact
CUDA/CPU owner oracles pass. Both requests still match their six output tokens.
At position 68, all 36 GDN states were bit-identical. This is a single short
correctness trace; Phase 5 remains open. [Details](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

A 3,000 MiB repeat still moves layer-1 expert 11 VRAM→CPU and changes the first
committed GDN state at layer 2. Its activation differs from the 1,500 MiB cell,
so the aggregate state delta cannot be used as a cache-size comparison. The
larger cap did not prevent the selected owner switch; Phase 5 remains open.

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

An MTP2 cancellation run also passed at five accepted-prefix lengths. Both
fresh exact-length controls matched every committed token and state
fingerprint; the canceled service returned `Hello Orin!` on recovery. Minimum
host/admission availability was 13.18/12.53 GiB with zero cgroup events.
This is a bounded cancellation cell only; adaptive long-chain drift and
two-live batch divergence remain open. [Details](../../bench/results/2026-10-22-phase5-coder-mtp2-cancel-state/README.md).

A fresh, supervised per-layer QSA trace now matches the serial MTP2 control at
accepted lengths 70, 72 and 74, then differs in all 12 QSA layers at lengths 76
and 77, starting at model layer 3. Both prompts still match serial for their
ten generated tokens. Minimum available host/admission memory was 16.55/15.10
GiB with no cgroup events. The split trace shows both indexer arrays and K/V
cache state change across all 12 layers from model layer 3 by length 76.
Per-token K/V/indexer and decoder-compute ablations retain the same divergence,
so neither batched path alone explains it. The cause and relation to later
output drift remain unknown. A concurrent duplicate-prompt control found both
batch slots' QSA hashes mutually matched but differed from serial,
while their ten-token outputs remained exact.
See the [batch-MTP report](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

Earlier QSA runs submitted the long request and one-token peer concurrently;
a harness name-check error meant they did not delay the peer after the first
output as intended. They still show QSA drift after the peer finishes. A
corrected MTP2 control submitted the peer after 48 solo-path tokens: QSA
hashes matched at common lengths 121/122, then all 12 indexer/KV hashes
changed from 124 through 163. Direct GDN captures were bit-exact at committed
positions 120/121 and differed across all 36 layers at 123 (relative L2 0.0142).
Output remained exact. The first state change is after handoff during batch-slot
work; the responsible operation and quality bound remain unknown.

Direct numeric captures at committed position 126 found GDN state drift in
all 36 layers for both MTP2 (relative L2 0.00973) and target-only (0.00841),
despite exact 96-token output parity. MTP2 is not required; numerical cause
and quality bound remain unknown.

A delayed target-only control matched GDN state through positions 116–118,
then first differed at 119/model layer 12 (relative L2 0.00780), with exact
output. MTP2 stayed exact at positions 120/121 and first differed at 123/model
layer 1. Per-token KV/indexer and decoder ablations retained MTP2's first QSA
mismatch at length 124, ruling out either batched path alone. State drift
persists; its source and quality bound remain unresolved.

A corrected opt-in layer-12 capture paired rows by explicit position/token and
recorded batch slot IDs. The delayed target-only run matched the serial 96-token
output exactly and matched all captured fields at position 118; at position 119,
layer-12 input `x` and every captured downstream field differed. The batch
scheduler averaged one row per window, so this run did not explain the separate
multirow mismatch. See the [capture report](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md).

A separate two-live target-only run averaged 1.96 rows across 96 windows and
reproduced slot 1's first output mismatch at token 60. At position 127 it
consumed the same token as its fresh serial control, while all captured layer-12
fields differed; input `x` relative L2 was 0.06058. The internal delta therefore
precedes the visible token change, but the model-wide origin remains unknown.
The selected positions and captured arrays repeated bit-for-bit in a second
supervised run; this is bounded to the same prompt pair and build.

At the earlier selected boundary, direct layer-12 committed-state capture found
slot 0 exact through position 70 and changed at 71 (relative L2 0.00379), while
slot 1 was already changed at position 68 (0.00822). Layer-12 input `x` changed
at the same selected positions. Slot 1's earlier onset remains unbounded; see
the linked capture report for paired state and activation metrics.

A six-token all-layer state capture then found the row mapping was reversed in
that run: physical slot 0 matched serial prompt 1, slot 1 matched prompt 0, with
36/36 GDN layers agreeing on each mapping. Slot 0 was exact at position 68 and
first changed at GDN layer 2 by position 71; slot 1 was already changed at
position 68, first at layer 5. Both six-token outputs matched their controls.
Slot-to-prompt assignment varied across runs, so these boundaries are kept
run-local and do not explain token 60.

A same-workload layer-1 MoE capture found exact inputs, GDN fields and shared
expert output for prompt 1 at position 71, while the combined MoE vector differs
in all 2,560 values (relative L2 `0.00086265`). The six generated tokens still
match serial. This narrows the selected boundary to routed expert output,
combination or related per-row state without identifying a specific expert or
operation. Minimum available RAM was 17.465 GiB, with zero cgroup memory events.
[Compact result](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/two-live-layer1-moe-output-summary.json).

A 96-token paired trace repeats the position-71 combined-output delta for
prompt 1 and reaches the known token-60 mismatch. By positions 118–127, both
requests already have changed layer-1 state, GDN fields, MoE inputs and shared
outputs. Minimum available RAM was 17.434 GiB; the added state capture makes
timing diagnostic only. [Selected-position results](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/two-live-layer1-moe-long-chain-summary.json).

An opt-in route/parts trace then showed prompt 1 keeps identical top-10 expert
IDs and weights at position 71, with nine expert outputs exact and only expert
11 changed. Weighting that expert's part delta reproduces the combined MoE
delta to a `3.24e-9` maximum residual. This pins the selected numerical delta
to expert 11's output path, without explaining its numerical cause. The six
output tokens still matched serial; minimum available RAM was 17.643 GiB.
[Compact result](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/two-live-layer1-expert11-summary.json).

## Near-term direction

1. Continue resolving batch-MTP output divergence: capture earlier layer
   boundaries and logits around the reproducible multirow drift, then isolate
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

A dispatch-owner follow-up maps the selected layer-1 position-71 Coder row exactly: expert 11 moves from primary VRAM in serial to CPU in batch, and its recorded CPU output matches the batch part within `5.0e-11` (serialization rounding). This associates the isolated expert delta with an owner change but leaves the numerical cause and later token-60 relationship unresolved. [Details](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md).


The same-input native expert oracle confirms the prompt-1 owner transition (serial GPU and batch CPU outputs each match their owner-specific oracle exactly). Prompt 0's serial CPU output and batch CPU dispatch 3505 both match the exact single-token CPU oracle, to JSON serialization precision (`5.0e-11`). The earlier reported 2.19 relative-L2 difference compared against prompt 1's oracle activation by mistake. Prompt 1's CPU/GPU difference remains real for that activation and needs broader numerical qualification.

A temporary expert-11-first residency profile made the paired layer-1 MoE
output exact and moved the first changed committed GDN state to layer 4. Layer 2
still switches expert 164 from VRAM to CPU with a same-input, oracle-confirmed
owner arithmetic difference. This narrows the correctness investigation only;
it is not performance evidence or a supported profile. The trace joiner now
rejects owner/verifier route mismatches. [Details](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).
