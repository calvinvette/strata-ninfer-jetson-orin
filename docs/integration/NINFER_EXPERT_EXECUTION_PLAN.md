# NInfer expert execution inside Strata

Status: **E0–E5 bounded implementation evidence complete; current-source HIP/SYCL builds pass on maestro1; a 6-GiB staged TTFT cell passed seven-pair confirmation, but a new multi-shape screen found unresolved output divergence, so E6 and E7 release gates remain open (updated 2026-10-26)**.
Prepared: 2026-10-25. Planning baseline: integration commit `5829a4a9`;
NInfer reference: `b07248f2528125aeda7550055580204541f1714c`.

## Objective and completion boundary

Keep Strata responsible for model loading, expert residency, physical memory,
routing, request scheduling and persistent state. Execute selected expert
gate/up, activation and down-projection work through an adapted NInfer compute
backend. Cover GPU-resident experts first, then provide a bounded GPU execution
route for selected experts that are absent from the resident cache.

This is a follow-on to [PLAN.md](PLAN.md). Its earlier phase closeouts describe
bounded Strata qualification and optimization work; they do not establish that
NInfer's expert kernels were integrated. Stages E0–E7 below track the missing
execution work separately. The [upstream Qwen3.6 merge plan](UPSTREAM_QWEN36_SM87_PLAN.md)
is a separate project and is not a prerequisite for the Flash-Next integration.

Two outcomes must be reported separately:

- **Implemented integration:** attributable NInfer-derived expert code is built,
  selected and exercised on real model requests; its supported formats, fallback
  coverage, correctness and resource lifetimes are demonstrated.
- **Performance-qualified profile:** same-day paired measurements demonstrate a
  useful end-to-end benefit within the declared quality and memory limits.

An imported snapshot, a wrapper that still calls only the old Strata kernels,
an isolated operator win, or an unpaired TPS chart satisfies neither outcome.
A correct integration that fails the performance gate remains experimental;
record that result without claiming acceleration or closing the performance goal.

## Findings that drive this plan

| Finding | Consequence |
| --- | --- |
| Strata's active resident expert dispatch still calls `native_expert_grouped`; the CUDA expert implementation has not been replaced with NInfer's sparse-MoE code. | Add an actual execution backend and observable dispatch evidence. |
| NInfer's sparse-MoE operator targets hidden width 2,048, expert intermediate width 512, top-8 routing, BF16 activations and particular groupwise codecs. Flash-Next uses widths 2,560/640, top-10 and mixed GGUF codecs. | Adapt the selected expert compute stages to exact Flash-Next geometry, layouts and arithmetic. A direct call to the complete NInfer operator is unsuitable. |
| The historical 8K Coder run allocated 6,938 slots / 13.20 GiB; the current run allocated 3,903 / 7.44 GiB. For the plotted 557-token requests, reported decode hit rates were 96.6–99.1% and 55.4–55.7%. | Match actual residency and policy before attributing a difference to kernels. Active router selections are not necessarily GPU-resident. Speculative lookup denominators also differ. |
| Historical adaptation and MTP were enabled; the current Coder profile disables both, uses eight rather than eleven workers, and changes prefill chunk and CPU contribution. | Benchmark kernel substitution independently, then tune policy in separate experiments. |
| The current Coder configuration already enables the Q6_K warp-dequantization optimization, which showed about 6.4–7.3% request-latency reductions in its scoped confirmations. | Retain this setting identically in the primary control and candidate. Do not count its existing benefit as a new expert-backend gain. |
| Earlier Nsight profiles identified dense-weight dequantization and GPU waits; the IQ3_S campaign recorded 33.81–50.08 GB/request of host-wide NVMe reads. | Reuse existing profiling and counters, then measure the current critical path. GPU expert arithmetic may be hidden by CPU, storage, or synchronization costs. Host disk counters are not process attribution. |

Sources: [active dispatch](../../src/core/verify.cpp),
[NInfer sparse-MoE contract](../../reference/ninfer/include/ninfer/ops/sparse_moe.h),
[original 8K log](../../bench/results/2026-10-08-jetson-orin/rebased-context-sweep/rebased/8192/engine.txt),
[current 8K server log](../../bench/results/2026-10-25-flashnext-context-capacity-sweep/campaign/coder-iq1m/8192/run/server.txt),
[Q6_K qualification](PHASE4_CLOSEOUT.md),
[request profile](../../bench/results/2026-10-10-phase4-candidate-request-profile/README.md),
[IQ3_S measurements](../../bench/results/2026-10-24-iq3s-current-candidate-performance/README.md).

## Architecture to implement

| Owner | Responsibilities |
| --- | --- |
| Existing Strata model frontend and router | Tokenization, model identity, route IDs and weights, top-10 selection, shared expert and residual semantics. |
| Existing Strata `ExpertCache` and `FileExpertSource` | Resident expert selection, exact weight bytes, cache-slot ownership, storage access, bounded staging and any layout-cache lifetime. |
| New NInfer-derived expert backend | Selected expert gate/up projections, activation and down projection for explicitly supported tensor pairs and token shapes. Accept caller-owned weights, buffers and streams. |
| Existing Strata verifier and prefill driver | Construct work batches, coordinate CPU/GPU completion, combine outputs in the required order, and own graph capture and persistent-state publication. |
| Existing Strata memory authority | Account for cache, staging, repacked data, workspace and transition peaks once in Orin's shared physical RAM. |

Extract/adapt useful parts of NInfer's routed D3/D4 computation and its decode,
small-token and prefill schedules. Keep Strata's routing, shared-expert merge and
residual behavior initially; importing NInfer's complete `sparse_moe` would also
replace those model-specific semantics. Investigate additional fusion only after
the smaller interface is qualified.

The first adapter returns one unweighted expert-output row per selected
token/expert pair in Strata's declared representation. Strata applies route
weights and performs its existing shared-expert and residual combination.
Extracting NInfer's down-projection stage must therefore remove its original
merge/residual epilogue, avoiding double weighting or residual addition.

The proposed interface carries model/layer identity, expert IDs, per-expert
gate/up/down pointers and codec metadata, token-to-expert groups, activation
representation, output row mapping, workspace bounds and stream ownership.
Strata's noncontiguous cache slots must be accepted directly or through a bounded
descriptor table; NInfer's contiguous expert-bank addressing cannot be assumed.

The backend must not allocate memory or perform host synchronization during a
captured invocation. Workspace and descriptor capacities are admitted before
capture. Weight views remain valid until GPU completion. Use slot generation or
equivalent ownership checks so eviction/reuse cannot expose stale expert pointers.

Proposed runtime selection: `--expert-backend strata|ninfer`, default `strata`.
Define capability queries by codec pair, geometry, represented types, backend
and token count. Ordinary execution may use a documented Strata fallback;
benchmark strict mode must reject fallback for the declared supported cells.
Report candidate invocations, fallback counts and reasons, routed entries,
resident versus staged work and the fraction actually handled by the new code.
Do not print a generic NInfer-enabled banner when all work fell back.

### Representation policy

- Inventory each model's actual gate/up/down tensor pairs. A distribution name
  such as IQ1_M or IQ3_S does not specify every tensor's codec.
- Prefer adapting NInfer scheduling/fusion to the existing GGUF decoder and
  represented activations. Preserve the current model artifact and source weights.
- If a layout transformation is needed, preserve codes/scales and prove the
  decoded values exactly. Cache the transformed representation only within an
  explicit memory budget; measure fill, transformation and eviction costs.
- Treat FP16/BF16 materialization as an arithmetic change unless exactness is
  demonstrated. Charge its enlarged footprint and rounding behavior to the
  candidate; do not silently lower resident capacity to fund it.
- Requantization or conversion to a different `.ninfer` artifact is a separately
  labeled model/quality experiment. It cannot establish a same-weight kernel gain.

## Implementation sequence

E0 is complete for the bounded controls and current Q2_0 timing audit; E1–E4
have bounded Q2_0 prototype evidence. E5 has MTP-2/MTP-4 cancellation,
accepted-prefix, continuation/recovery and short retrieval/arithmetic evidence.
E4 explicitly leaves the mixed-codec
Coder IQ1_M and ISTA-DASLab IQ3_S models unsupported by
the NInfer selector; E5 is complete for the bounded single-live static Q2_0
profile, with cross-backend state migration, adaptive residency and broader
quality coverage explicitly excluded. E6's 1K–256K context screen is complete.
After a grouped SwiGLU precision correction, one short-request 6-GiB staged
Q2_0 cell passed seven-pair TTFT confirmation, but broader workload/context
coverage and E6's full performance exit remain open. A follow-up 8K
CPU-miss-versus-staged screen found 1,069- and 557-token output hash
mismatches, so their performance effects are not quality-qualified. Current-
source HIP/SYCL builds and help checks passed on maestro1, but accelerator
execution and any release-candidate soak remain open. E7's assessment proposes
no general profile.
The 1,069-token follow-up found exact CPU/NInfer token parity at each paired
request ordinal and exact final-state parity wherever capture was available.
Fresh-engine repeats were stable, while same-service repeats changed output
with cache reuse and with prompt caching disabled. A small opt-in final-state
hash hook now supports the cache-off diagnostic; the Orin CUDA build and direct
check passed, with HIP/SYCL rebuilds still required because the source is shared.
This shared process/request-history signal does not explain the original
multi-workload staged-miss mismatches. The full workload-order replay is
complete and still finds cross-backend final-state differences on all five
requests. A preregistered 1,069-token task-quality diagnostic also completed;
both backends met its content/length criteria but both missed the required
opening word. The task therefore does not qualify either arm or resolve the
output mismatches. Performance confirmation and profile promotion remain
deferred. The position-123 QSA trace initially missed its target because its
row filter was recorded into a reusable CUDA graph before current positions
were staged. The opt-in trace now stages positions before graph recording and
rebuilds the window graph; a paired capture at model layer 3 / position 123
found exact selected K/V and attention outputs, with only F32-scale upstream
input deltas. Final persistent state still differs, so the correctness gate
remains open. See the [staged-miss report and
diagnostic](../../bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/README.md),
[task-quality check](../../bench/results/2026-10-26-e6-q2-quality-1069-512/README.md),
and [position-123 trace report](../../bench/results/2026-10-26-e6-q2-prefix-context-state-sweep/README.md#position-123-qsa-trace).

Execution note (2026-10-26): a repeated position-123 trace found the only
material layer-2 expert-row delta in expert 114. An opt-in CPU Q8_1 dot
selector for that layer/expert made its output exact against staged execution
and restored exact selected layer-3 QSA K/V, attention and projection at the
sampled step, including cache cell 123. Whole-request state still differed.
This supports owner activation-format arithmetic as the local QSA cause but
does not close the staged state or task-quality gate. The grouped CUDA operator
check found no useful resident speedup: one-token timings tied, 64/128-token
groups regressed, and a standalone D3/D4 path failed its oracle. Keep these
diagnostics separate from performance confirmation. See the [trace and
operator report](../../bench/results/2026-10-26-e6-q2-prefix-context-state-sweep/README.md).

Execution note (2026-10-26): applying the CPU Q8_1 mirror across all Q2_0
experts left global GDN relative L2 `4.686e-2`, with the first material state
delta at GDN ordinal 3/model layer 4. At model layer 3, position 123, tiny
input drift (`1.59e-7`) changed one Q8_1 block's FP16 scale despite identical
integer codes; all ten expert rows then differed and the combined output was
`1.156e-3` apart. An independent oracle matched the captured expert-394 rows
for their respective inputs. This identifies a local quantization-scale
boundary, but not a whole-model tolerance. The 5-position/per-layer trace is
recorded in the [E6 diagnostic report](../../bench/results/2026-10-26-e6-q2-prefix-context-state-sweep/README.md#remaining-layer-3-activation-scale-boundary).
E2's resident schedule and the earlier E3 staged-miss schedules failed their
initial performance screens. The
default remains Strata and the NInfer path remains experimental. Each stage
produces a small source/evidence change and
a written decision before the next dependent stage begins.

Execution note (2026-10-25): an isolated `feat/ninfer-expert-e0` worktree now
contains a supervised Orin baseline profile, an opt-in current-source residency
map dump, and a three-pair pinned-product-control screen. The current executable
still uses Strata's existing expert kernels for that pinned-product comparison.
E2 has since added a three-pair same-source backend-off/on screening set with
matching resident maps; it rejects the initial NInfer Q2_0 schedule for
performance. E0's Q2_0 request-phase gap is now measured using same-source
Strata and NInfer services with matched residency-map hashes. The pinned binary
still does not expose its resident-ID map, so its product comparison remains
matched by model/profile/options/slot count rather than exact IDs. See the
[E0 runtime audit](../../bench/results/2026-10-25-phase-e0-expert-runtime-audit/README.md),
[E2 paired screen](../../bench/results/2026-10-25-phase-e2-q2-ninfer-resident-smoke/paired-screen/README.md),
and [Q2_0 phase timing](../../bench/results/2026-10-25-phase-e0-expert-runtime-audit/q2-decode-breakdown/README.md).

Execution note (2026-10-25): E1 inventory confirmed that all routed Q2_0
gate/up/down tensors in the Coder Q2_0 artifact use 2560/640 geometry across 48
layers. The first adapter contract and scalar oracle are in
[E1_Q2_0_EXPERT_CONTRACT.md](E1_Q2_0_EXPERT_CONTRACT.md); synthetic checks pass
4/4, and 32,768 sampled real-payload decoded values match pinned ggml bit-for-bit.
The full FP64 projection oracle ran actual Q2_0 expert weights on a captured
cross-variant Coder IQ1_M activation and matched the current Strata harness's
unquantized reference at relative L1 `3.76e-8`. The target model's own activation
distribution remains an open limitation. NInfer-derived adapter parity now
passes for the captured cross-variant activation; see the E2/E4 reports.

### E0 — Freeze controls and identify where time is spent — complete for the bounded Q2_0 audit

1. Create an isolated integration branch/worktree from the recorded current
   source, preserving existing dirty evidence and both original project checkouts.
   Pin binary, compiler, model, pack, tokenizer and workload identities.
2. Preserve the measurement protocol's pinned Strata control for same-day product
   comparisons where flags are compatible. Add the current Strata backend as the
   kernel-ablation control: the same candidate source with backend off/on isolates
   the new execution path from other changes accumulated in this fork.
3. Start with 8K context, one live request, FP16 KV, MTP off, static residency,
   fixed prefill chunk and workers. Match actual cache bytes, slot count and the
   hash of resident expert IDs; equal command-line cache arguments are insufficient.
   Retain Q6_K optimization identically where applicable. MTP off must be verified
   by draft counters and model configuration, not inferred from native `--spec`.
4. Reuse existing request, cache, CPU-pool, storage and allocation counters. Add
   only missing request/phase markers and timing: resident GPU expert kernels,
   CPU expert computation, lookup/fetch/staging, dense projections, waits and merge.
   Attribute prefill and decode separately. Profile diagnostic runs separately from
   unprofiled throughput runs; demonstrate that disabled instrumentation has no effect.
5. Measure warm cache behavior and ordinary first-request behavior without global
   cache drops. Keep logical expert bytes, physical NVMe reads, page faults and
   CPU/GPU shared-memory traffic distinct. Sum of overlapping kernel durations
   must not be presented as a fraction of request wall time.

**Exit:** reproducible paired controls, current workload/codec/route inventory
and a measured explanation of which work can benefit from expert-kernel changes.
The Q2_0 matched-residency three-pair screen and one same-day decode-phase pair
are recorded in the [E2 paired screen](../../bench/results/2026-10-25-phase-e2-q2-ninfer-resident-smoke/paired-screen/README.md)
and [Q2_0 phase timing](../../bench/results/2026-10-25-phase-e0-expert-runtime-audit/q2-decode-breakdown/README.md).
They identify CPU expert work, job/plan setup and GPU-reach wait separately;
the grouped NInfer operator screen is slower than Strata. Dense and resident
expert kernel families are not separated in a Q2_0 service Nsight trace yet.
This is enough to reject the current schedule and select it for optimization,
not to claim a speedup ceiling or a performance result. The original pinned
product binary's resident map remains unavailable. That limitation is explicit;
it does not invalidate the same-source matched-map experiment. E0 does not
expand into unrelated concurrency diagnosis.

### E1 — Specify and prove the selected expert contract — complete 2026-10-25

1. Map exact NInfer source functions to the proposed Strata adapter, including
   geometry, decoder, activation scaling, SiLU, down projection and output order.
   Record what is reused, adapted or incompatible and preserve Apache-2.0 notices.
2. Start with the actual Q2_0 routed tensor pair as a small implementation target,
   subject to its verified inventory; it is not assumed compatible with NInfer's
   Q4/Q5 formats. Use captured Coder mixed-codec rows to prioritize subsequent pairs.
3. Specify pointer/slot lifetime, duplicate expert handling, empty resident sets,
   zero-job dispatch, partially filled batches, stream completion and graph reuse.
4. Define independent codec and mathematical oracles and numerical budgets before
   inspecting candidate performance. Exercise real payloads, real activation captures,
   edge values, routing permutations and actual Flash-Next dimensions.

**Exit:** a concrete adapter contract and oracle fixtures for the first codec pair.
The [E1 Q2_0 contract](E1_Q2_0_EXPERT_CONTRACT.md) records the supported tensor
pair, source mapping, lifetimes and numerical oracle. Synthetic codec/geometry/
route-map checks pass 4/4; 32,768 sampled values from eight real tensors match
pinned ggml bit-for-bit. A full real-weight FP64 oracle case matches the current
Strata unquantized reference at relative L1 `3.76e-8`. The activation is a
captured cross-variant Coder IQ1_M vector. The E2 prototype's direct and grouped
GPU adapter parity is now recorded, but Q2_0-model-native activation coverage
remains an open release limitation.
Retain fixtures under `~/models/` when they contain model payloads. A stub or an
operator that simply forwards all work to Strata is not the E2 deliverable.

Execution note (2026-10-25): the first CUDA Q2_0/Q2_0 resident adapter is now
implemented behind `--expert-backend ninfer`; default Strata behavior is
unchanged. It adapts NInfer-derived D3 gate/up + SiLU and D4 down-projection
stages to the actual 2560/640 Q2_0 layout, uses Strata's Q8_1 activation
quantizer for grouped cache work, and leaves route weighting/shared/residual
semantics in Strata. Actual-weight single-expert GPU output passes the FP64
oracle, and one grouped GPU resident entry passes comparison against the
existing Strata Q2_0 route. A strict-mode service smoke returned a completion.
The first service attempt exposed the helper's eight-column limit and the adapter
now chunks quantization calls accordingly. This is implementation evidence,
not an acceleration claim. A later three-pair screen matched the resident-map
hash and output hashes, and found the candidate consistently slower; exact
route IDs, broad device-side entry coverage, model-native activation cases and
edge-case qualification remain open. CUDA only; HIP/SYCL builds are not yet
available. See the [E2 smoke report](../../bench/results/2026-10-25-phase-e2-q2-ninfer-resident-smoke/README.md)
and [paired service screen](../../bench/results/2026-10-25-phase-e2-q2-ninfer-resident-smoke/paired-screen/README.md).
An initial same-weight, one-token grouped operator screen measured 85.7 us
median for the NInfer route versus 24.5 us for Strata across seven interleaved
blocks of 1,000 calls. Three randomized same-residency service pairs also found
the candidate 3.4% slower on prompt latency, 7.3% slower on decode latency and
4.4% slower on client completion time by median paired change. This is a
negative screening result, not a performance confirmation; revise or reject
this schedule before considering a larger confirmation campaign.

### E2 — Execute resident experts with NInfer-derived kernels — complete 2026-10-25

1. Promote the narrow NInfer compute code into active Strata source ownership
   outside `reference/ninfer/`; adapt it for Flash-Next shape, codec and activations.
   Keep a provenance map from each promoted function to the pinned reference.
2. Implement one-token decode first, including gate/up, activation and down
   projection, without replacing the router or shared-expert semantics.
3. Wire the opt-in backend through the existing grouped resident-expert dispatch.
   Supply Strata-owned cache pointers and output row indices, and retain the
   established fallback for unsupported codecs/backends.
4. Compare actual GPU-resident expert work on identical weight bytes, activations,
   route IDs and cache contents. Record kernel time, launches, scratch, register
   and shared-memory use, and resource-limited schedules on Orin SM87.
5. Run full service requests with dispatch counters proving that the new code ran.
   Confirm resident-kernel on/off effects independently of new transfer policies.

**Exit:** satisfied for a bounded Q2_0/Q2_0 functional prototype. The strict
real-model request exercised the selected CUDA path; scalar and grouped GPU
outputs passed their independent/current-backend checks; matched one-token
operator and three-block same-residency service screens were recorded. The
screening result rejected this schedule: operator median was 3.50x slower, and
the service median paired changes were +3.4% prompt latency, +7.3% decode
latency and +4.4% client completion time. This closes the implementation audit
for the prototype, not the performance goal. Do not promote it as an optimized
backend or begin E3 by assuming this schedule is suitable. Exact service route
IDs, broad edge cases, model-native activations, kernel resource breakdown and
other backends remain open release limitations. Evidence: [E2 implementation
report](../../bench/results/2026-10-25-phase-e2-q2-ninfer-resident-smoke/README.md)
and [paired screen](../../bench/results/2026-10-25-phase-e2-q2-ninfer-resident-smoke/paired-screen/README.md).

### E3 — Feed missing active experts to the GPU backend — complete 2026-10-25

1. Add a bounded staging route under the existing expert source and memory owner.
   Fetch selected nonresident expert weights into admitted host/device buffers,
   then invoke the same new compute backend on those buffers.
2. Reuse an expert's staged weights across tokens in the same group. Include
   lookup, faults, storage reads, any repack, copy, compute and completion in the
   route cost. Overlap the next group's transfer only when lifetimes permit it.
3. Compare CPU fallback, staged GPU execution and any supported direct mapped
   access on Orin. Shared RAM does not guarantee a pageable file mapping is a
   usable CUDA device pointer; establish registration, aliasing and coherence.
4. Screen a small staging-depth/worker split. Keep CPU fallback available where
   it wins or where memory admission refuses GPU staging. Record the actual route.
5. Test cancellation, short/failed reads, unsupported codecs, allocation refusal,
   buffer reuse and teardown. Never overwrite a slot still used by a captured graph.

**Exit:** all selected experts in the first supported model can be executed by
the new GPU backend when that mode is requested, using a bounded working set.
A separately tuned hybrid mode may retain CPU execution. Publish both coverage
and total route latency so a fast resident-only result cannot hide slow misses.

The existing Strata `GpuPlanSink` already owns bounded staging descriptors,
copy/direct mapped paths, transfer lifetimes and shared-memory admission. The
grouped adapter consumes its staged expert pointers through the same
caller-owned grouped interface; no second cache, allocator or memory ledger was
introduced. A 1-GiB pinned complement with the six-GiB physical floor plus
separate three-GiB workspace reserve exercised both copy-kernel and direct
mapped modes. Each fresh process used the same 3,000-slot resident-map hash.

Three paired CPU-miss versus copy-staged requests reported 106/13,920 (0.8%)
expert slots offloaded to the GPU under `--pcie-frac 0.55`. The staged NInfer arm
was 6.47% slower in decode latency and 2.10% slower in client completion by
median paired change. Three direct-mapped runs completed and handled the same
106 slots, with no evident advantage over copied staging. These are screening
results, not a useful profile. Keep CPU miss fallback and default behavior;
larger complement/staging sweeps remain subject to memory admission and are not
release-qualified. See the [staged-miss report](../../bench/results/2026-10-25-phase-e2-q2-ninfer-resident-smoke/staged-screen/README.md)
and [direct-mapped report](../../bench/results/2026-10-25-phase-e2-q2-ninfer-resident-smoke/direct-screen/README.md).

This closes the bounded Q2_0 staging route integration only; E6's performance
goal remains open.

Execution note (2026-10-25): a fresh randomized three-pair screen at
`--pcie-frac 1.0` selected 265 staged entries (1.9% of 13,920 routed entries)
per request, versus 106 (0.8%) at 0.55. Median client latency improved 1.32%
and TTFT 1.19%, both below the 5% useful-effect threshold. The resident maps
matched in all six services, but all three NInfer text hashes differed from
their CPU-miss controls; no independent quality oracle was run. Minimum
available physical/admission memory was 16.21 GiB. The limited routed coverage
and sub-threshold latency effect do not justify confirmation or promotion. See
the [max-offload screen](../../bench/results/2026-10-25-phase-e3-q2-ninfer-max-offload/README.md).
A second three-pair full-offload screen reduced GPU residency to 1,000 slots
with the same 1-GiB complement. It selected 226 entries (1.6%), produced exact
response-hash matches, and improved median client latency by 0.72% and TTFT by
0.43%. Staged coverage was lower than with 3,000 slots, and the effect remained
below threshold. See the [1,000-slot screen](../../bench/results/2026-10-25-phase-e3-q2-ninfer-cache1k-max-offload/README.md).

Execution note (2026-10-25): a pinned complement sweep at 3,000 slots and
`--pcie-frac 1.0` tested 2, 4 and 6 GiB complements in three randomized pairs
per cell. Staged entries increased from 537 (3.9%) to 922 (6.6%) to 1,364
(9.8%) of routed entries. Median client latency improvements were 1.00%,
3.29% and 4.09%; TTFT improvements were 1.62%, 3.80% and 6.05%. The 2-GiB
and 6-GiB outputs matched their controls; all 4-GiB outputs differed. Minimum
available memory at 6 GiB was 11.36 GiB, retaining both required reserves.
Because the 6-GiB held-out retrieval/arithmetic check returned matching token
IDs but differing final GDN, tail, pooled, pooled-full and KV fingerprints,
the quality gate failed. Do not run seven-pair confirmation or promote this
setting until the state difference is understood and the quality gate passes.
The final GDN comparison found 90.80% of values different (global relative
L2 0.02396); layers 0–2 were exact and layer 3 first differed by about
`1.2e-7`. A one-position layer-3 MoE capture at generated position 557 was
exact across inputs, routes, expert parts and outputs, so it does not explain
the aggregate state difference or rule out earlier prompt-position deltas. A
second capture at the final prompt position, model layer 1, was also exact.
Multi-position layer-3 captures found one difference among positions 512,
520, 530, 540 and 557: at 520, expert 94's row differed on identical input,
route IDs and weights (relative L2 `7.15e-4`); the other sampled rows were
bit-identical. This is the first sampled mismatch, not necessarily the first
divergent position; 513–519 remain unexamined. The [quality diagnostic](../../bench/results/2026-10-25-phase-e3-q2-ninfer-complement6g-quality/README.md)
contains per-expert evidence. A standalone replay using this exact activation
and expert found scalar D3/D4 relative L2 `2.05e-7` against the FP64 oracle,
but grouped resident-route relative L1 `6.71e-4` against Strata, failing its
`2.0e-4` limit. Grouped 64/128-token operator timing was 1.108×/1.121× Strata.
This makes the grouped kernel arithmetic the next implementation target; the
service result is not explained by cache staging alone.
The 6-GiB TTFT screen alone is not a performance qualification: median client
latency remains below the 5% target, each cell has only three pairs, and
persistent-state equivalence is unresolved. See the [complement sweep
report](../../bench/results/2026-10-25-phase-e3-q2-complement-sweep/README.md)
and [quality diagnostic](../../bench/results/2026-10-25-phase-e3-q2-ninfer-complement6g-quality/README.md).

Pre-registration (2026-10-25, before confirmation): for the corrected grouped
SwiGLU kernel at this staged 6-GiB profile, nominate TTFT as the primary metric
because this screen targets prompt-to-first-token delay. Require at least 5%
median paired improvement with the paired 95% interval excluding zero. Treat
client completion as the secondary metric, with no more than 5% regression.
Require matching output hashes and the held-out exact-answer/final-state check
to pass; retain the six-GiB host headroom and three-GiB workspace reserve.

Execution note (2026-10-25): the grouped SwiGLU kernel used `__fdividef` while
Strata's corresponding quantizer used precise `/`. With identical gate/up
intermediates, this changed one Q8_1 code byte at layer 3 / expert 94 / token
position 520, producing the grouped output and final-state differences above.
Replacing approximate division with Strata's expression made the full Q8_1
block and grouped expert output bit-identical in the standalone replay. The
corrected CUDA service build then passed the same 512-token answer, token-ID
and final-state comparison. A fresh randomized three-pair screen measured
median TTFT improvement 6.29% and client completion improvement 4.57%, with
matching measured outputs and resident maps. The seven-pair confirmation
reported TTFT −5.96% with a paired bootstrap 95% interval of −6.23% to −5.80%;
client completion was −4.17% (interval −4.40% to −4.00%). All seven measured
hashes and maps matched. All seven warmup hashes differed across arms and are
retained as a caveat. Minimum available memory was 11.37 GiB. Thus this one
TTFT cell passes its registered effect, quality and memory checks; the single
short request does not close E6 across context sizes or models. Grouped
64/128-token operator timing remains slower (1.098×/1.123× Strata). See the
[corrected parity replay](../../bench/results/2026-10-25-phase-e3-q2-ninfer-complement6g-quality/expert94-parity-fixed/README.md),
[held-out state check](../../bench/results/2026-10-25-phase-e3-q2-ninfer-complement6g-quality/fixed-kernel/README.md),
[three-pair screen](../../bench/results/2026-10-25-phase-e3-q2-ninfer-complement6g-fixed-swiglu/README.md)
and [seven-pair confirmation](../../bench/results/2026-10-25-phase-e3-q2-ninfer-complement6g-fixed-swiglu-confirm7/README.md).

### E4 — Add prefill, small-token execution and model coverage — complete with partial model support

1. The bounded Q2_0 implementation now exercises one-token decode and a
   three-token, three-group, nine-entry prefill-shaped batch. This confirms the
   grouped descriptor/token/output mapping and the 8+1 SwiGLU quantizer chunk
   boundary against Strata's grouped route. Full top-10 grouped shape checks
   also pass at 64 and 128 input tokens. These are functional operator checks,
   not latency sweeps or end-to-end prefill qualification.
2. Q2_0 expert weights are reused through grouped descriptors for multiple
   token/expert entries. The initial operator screen was slower than Strata;
   no fusion or performance claim is made.
3. Header-only inventories identify exact expert codec pairs in Coder IQ1_M
   and ISTA-DASLab IQ3_S. Both are mixed-codec; their full-model expert routes
   are explicitly unsupported by the current Q2_0-only selector. The exact
   Q2_0 artifact remains the only supported codec pair in this prototype.
4. Publish the current model/codec, shape, residency and backend capability
   table. HIP/SYCL runtime cells remain unsupported/unqualified; no shared
   backend implementation was changed in E4.

**Exit:** the bounded Q2_0 shape and codec result and explicit partial status for
the other target variants are recorded in
[E4 model and shape coverage](../../bench/results/2026-10-25-phase-e4-model-codec-coverage/README.md).
Only the Q2_0/Q2_0 artifact has functional adapter coverage, and it is not
performance-qualified. The other model variants are explicitly unsupported.
64/128-token throughput, mixed-codec support and HIP/SYCL qualification remain
open; this stage closes with partial model support as allowed by its exit.

### E5 — Qualify numerical behavior and useful execution policies

Use the numerical policy below throughout implementation; this stage completes
the model and service gates and expands beyond the initial static profile.

1. Test held-out short and long requests, repeated continuation, retrieval and
   scoring, cancellation and recovery. Compare state and numerical results in
   addition to text. Retain original/default-route regression evidence.
2. Qualify captured/eager execution and supported small verifier windows with
   stable allocations. Test accepted-prefix commit and rejected-suffix isolation
   using the newly selected serial backend as the appropriate execution reference.
3. Test MTP off/2/4 where supported, initially with static expert ownership.
   Hold the expert backend constant while selecting MTP by workload.
4. Address adaptive residency as a focused follow-up. Moving weights between a
   cache slot and a staging slot while keeping the same GPU arithmetic may avoid
   the previous CPU/GPU owner change; this is a hypothesis that requires direct
   state checks. CPU/GPU owner migration requires its own numerical contract.
   Preserve a valid static profile while that work remains unresolved.

**Exit:** a bounded model/backend/profile support matrix with correctness,
graph lifetime and service evidence. Do not make concurrency, universal replay,
or every historical adaptive-state investigation prerequisites for a correct
single-request static integration. Any excluded feature remains explicitly open.

Execution note (2026-10-25): strict Q2_0 NInfer services with static 3,000-slot
expert ownership passed accepted-prefix cancellation, same-process recovery and
two fresh exact-length references at MTP-2 and MTP-4. MTP-2 committed seven
tokens at lengths 48/50/52/54 with three accepted drafts; MTP-4 committed nine
tokens at lengths 48/52/56 with six accepted drafts. GDN, PLE, KV, MTP and other
state fingerprints matched at each prefix. Verifier and MTP graph-instantiation
events were observed. Minimum availability was 17.04 and 16.78 GiB, respectively,
above the 6 GiB floor, with zero cgroup memory events. These are short
deterministic prompts at one cancellation boundary each; long/held-out tasks and
adaptive residency remain open. See the [MTP-2 report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-mtp2-cancel-state/README.md)
and [MTP-4 report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-mtp4-cancel-state/README.md).

Separate 512-token-prompt tests compared MTP-off with MTP-2 and MTP-4 under the
same strict NInfer backend. MTP-2 accepted 15/17 drafts and matched all 32
output token IDs, final state and 18 shared accepted-prefix states; MTP-4
accepted 23/33 and matched all 32 IDs, final state and 12 shared prefixes. The
[MTP-2 parity report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-mtp2-prefix-parity/README.md)
and [MTP-4 parity report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-mtp4-prefix-parity/README.md)
record the held-fixed setup and memory telemetry. A subsequent three-request
MTP-off/MTP-4 sequence (initial generation, continuation, then recovery) matched
all token IDs and the nine captured persistent-state fields at every request
boundary. MTP-4 accepted five drafts in each request, with rejected suffixes
before continuation and recovery. See the [repeated continuation report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-mtp4-continuation/README.md).
An exact 512-token retrieval-plus-arithmetic task also passed with strict NInfer
and MTP off/4: both arms returned the exact three codes and suffix sum in 47
tokens, with identical token IDs and final persistent state. The single-run
timings are not an effect estimate. See the [retrieval task report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-retrieval-check/README.md).
A held-out 4,096-token version also returned the exact answer in both arms, with
identical tokens and final NInfer state; see the [long retrieval report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-long-retrieval/README.md).
An 8,192-token exact-answer retrieval/arithmetic check then compared fresh
MTP-off Strata and strict-NInfer engines with the corrected binary. Both
returned all three codes and the exact suffix sum in 47 tokens; token IDs and
all nine final state fields matched. Minimum available memory was 17.70 GiB
with no cgroup memory events. This is one functional retrieval case, not a
timing estimate or near-limit 16K ingestion result. See the [8K retrieval
report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-8k-retrieval/README.md).
The same check at 16,384 prompt tokens with a 32K cap also passed exact answer,
token-ID and all-nine-field final-state comparisons; minimum available memory
was 17.09 GiB, with no cgroup memory events. Each backend was run once, so
timings remain functional diagnostics only. Near-limit 32K ingestion and wider
task coverage remain open. See the [16K retrieval
report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-16k-retrieval/README.md).
The actual-prompt check also passed at 32,768 tokens under a 64K cap: both
backends returned the exact answer and matched token IDs and all nine final
state fields. Minimum available memory was 16.48 GiB with no cgroup memory
events. This remains a single retrieval task and not a performance estimate;
64K near-limit ingestion and broader tasks remain untested. See the [32K
retrieval report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-32k-retrieval/README.md).
The same held-out retrieval also passed with an actual 65,536-token prompt
under a 128K cap. Answer, generated IDs and all nine final state fields
matched; minimum available memory was 14.70 GiB with no cgroup memory events.
This is one 64K functional case and does not qualify near-limit 128K ingestion
or general long-context quality. See the [64K retrieval
report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-64k-retrieval/README.md).
The exact-answer retrieval and state comparison also passed at 131,072 prompt
tokens under a 256K cap. Minimum available memory was 11.40 GiB, with no cgroup
memory events. This is one task at 128K; near-limit 256K ingestion and broader
quality coverage remain open. See the [128K retrieval
report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-128k-retrieval/README.md).
A 240,286-token held-out retrieval/arithmetic prompt under a 262,144-token cap
also completed with both the Strata control and strict NInfer. Both captured
the 2-token and 1-token verifier windows, returned the exact answer, matched all
generated token IDs and all nine final state fields, with minimum available
memory of 11.44 GiB and no cgroup memory events. The earlier 60-second native
watchdog attempt stopped before completion; the bounded retry used an
experiment-only 300-second watchdog allowance and passed. Its single
sequential pair has descriptive timings only, not a performance estimate. See
the [240K retrieval report](../../bench/results/2026-10-25-phase-e5-q2-ninfer-240k-retrieval/README.md).
A pre-fix MTP-off default-Strata/strict-NInfer comparison returned the same
short-task tokens but showed substantial persistent-state movement. The first
committed-token GDN relative L2 was 0.0902; layer captures show a small expert
arithmetic difference at model layer 1 and a larger activation difference by
layer 2. The pre-fix 4K task also had different final state, and a pre-fix
512-token natural-generation task differed at generated token 9. After the
SwiGLU precision fix, the 512-token retrieval, two repeats of the same natural
generation task, and the 4K retrieval all matched token IDs and all nine final
state fields across backends. These reruns resolve those specific discrepancies
for the corrected binary; broader quality and numerical bounds remain open.
See the [corrected generation reruns](../../bench/results/2026-10-25-phase-e5-q2-ninfer-generation-regression/fixed-kernel/README.md)
and [corrected 4K retrieval](../../bench/results/2026-10-25-phase-e5-q2-ninfer-long-backend-regression/fixed-kernel/README.md).
This completes the bounded E5 exit only for single-backend static Q2_0
services. Live migration is unsupported; wider quality coverage remains open.
See the [E5 closeout](NINFER_E5_CLOSEOUT.md). Keep NInfer opt-in and do not
treat exact short-task text as sufficient evidence for other tasks.

### E6 — Demonstrate end-to-end performance and context behavior

Follow [BENCHMARKS.md](BENCHMARKS.md). Use three screening blocks followed by at
least seven independent randomized paired confirmation blocks on held-out prompts.

| Comparison | Held fixed | Question |
| --- | --- | --- |
| Current Strata backend vs new resident backend | Weights, route inputs, resident IDs/bytes, miss policy, MTP, chunk, workers, KV, context | Does the new expert computation itself improve request latency/TPS? |
| Resident-only substitution vs new staged-miss path | Resident backend and cache, same selected experts | Does accelerating missing experts improve completion time after transfer costs? |
| Cache/staging and CPU split experiments | Model and numerical profile | Where does the best feasible memory/compute balance lie? |
| MTP/graph/adaptation experiments | Qualified expert backend | Which additional policies help each workload without violating its contract? |
| Original Strata port vs completed integration | Common supported flags and artifact, with any unavoidable differences disclosed | What product-level gain was delivered? |

Run `pp512+tg64` and `pp2048+tg128`, then the 172/557/1,069-input and 64-output
matrix across configured capacities 1K, 2K, 4K, 8K, 16K, 32K, 64K, 128K and
256K. Skip the 1,069-token input at 1K. Expand sequentially under the guard and
retain failed/unsupported cells. Configured capacity with a short prompt is
separate from near-limit ingestion; qualify actual long prompts and retrieval
progressively before reporting long-context capability.

Use natural generation for serving measurements. Add controlled-token/route
replays where supported to separate kernel cost from changed token routing;
label those diagnostic results and verify output quality independently.

Before confirmation, nominate the primary metric and useful-effect threshold:
initially at least **5% median improvement**, with the paired 95% interval
excluding no improvement, no more than 5% regression in the other nominated
primary metric, no quality failure and no memory-floor violation. Decode kernels
nominate decode TPS; prefill kernels nominate prompt latency/TTFT. These are
decision thresholds, not promised outcomes. Report full-request latency as well.

An enlarged representation may reduce cache capacity. Measure its deployment
tradeoff separately from the controlled kernel comparison; do not conceal the
changed cache in the same label. Record cold/fill costs and the requests needed
to amortize transformation or packing.

**Exit:** operator effects and complete-request effects are both documented;
per-model and combined charts include matched controls and uncertainty. Keep
historical unmatched charts labeled as observations. There is no universal
"best profile" without evidence across the stated workloads and resource limits.

Execution note (2026-10-26): a balanced three-pair, five-shape comparison of
CPU miss fallback and strict NInfer staging at 8K found median +7.04% prompt
TPS, +8.54% decode TPS, −6.56% client TTFT and −7.60% client time for the
1,069-token cell. The measured output hash differed in all three pairs. The
557-token cell also had three output mismatches; its median decode TPS rose
7.99%, but TTFT was effectively unchanged (+0.21%) and client time improved
2.54%. Shorter shapes showed no useful end-to-end effect. All six arms passed
API/token-count checks, had identical startup residency maps and retained at
least 11.42 GiB physical/admission memory. The output divergence has no task
quality oracle yet, so no seven-pair confirmation or profile promotion is
justified. See the [staged workload report](../../bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/README.md).

Execution note (2026-10-26): a 2,048-token held-out retrieval task returned the
exact expected answer and matching token IDs under CPU miss and strict NInfer
staging, with identical residency maps and 4,556 staged reads. The final state
still differed in six fields; a resident-only Strata/NInfer control passed
exact token and all-state parity. The staged GDN state had 3.41% global
relative L2 over 29.4M floats. Sampled MoE routes matched while activation and
output differences grew with depth. This fails the staged state-parity gate;
the task answer does not qualify performance or release. Minimum available
memory was 11.45 GiB. See the [held-out retrieval/state
report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/README.md).
An independent layer-2 oracle that applies the runtime's Q8_1 input and
SwiGLU-intermediate boundaries matched the captured rows for experts 372 and
357 on both routes to about `9e-8` relative L2. This validates those sampled
expert computations for their respective inputs; it does not account for the
activation drift already present at layer 2 or locate the earlier state change.
An oracle check of sampled model-layer-1 experts 97, 74 and 70 also matched at
`5.9e-8`–`1.03e-7` relative L2. Route IDs matched, route weights differed by
at most `6e-8`, and the combined MoE output differed by `1.53e-7` relative L2.
The first GDN state mismatch is state layer 1 at `1.61e-5` relative L2. This
places the earliest observed drift near first-layer aggregation/state update,
but does not identify the operation responsible.
An exact-tokenized 128/256/512/1,024/1,536-token prefix sweep subsequently
confirmed CPU-miss/staged final-state divergence at every length; at 256 tokens
the single generated token differed as well. GDN global relative L2 ranged
from `0.03098` to `0.06257`; the first GDN ordinal above `1e-5` relative L2
moved between ordinal 3/model layer 4 and ordinal 5/model layer 6 with prompt
content. At 128 tokens, model-layer-2 MoE input/output deltas were only
`6.87e-8`/`1.00e-7` relative L2, while the captured model-layer-3 MoE input
was `5.47e-4` apart. A new opt-in residual-boundary capture found only
`5.50e-8` relative L2 at the post-read input to model layer 3, so amplification
occurs within the subsequent QSA attention/residual path before its MoE.
Internal QSA stages remain uncaptured, so the responsible operation is unknown.
These one-token state diagnostics do not provide task-quality or performance evidence; minimum
available memory was 11.43–11.52 GiB. See the [prefix state
sweep](../../bench/results/2026-10-26-e6-q2-prefix-context-state-sweep/README.md).
The same exact-answer held-out retrieval passed token and residency-map checks
at 4K and 8K prompts on CPU-miss and strict staged routes. Final state hashes
still differed in six fields at 4K, 16K and 32K and five at 8K; GDN global
relative L2 was `0.02645`, `0.03159`, `0.02572` and `0.02685`, respectively,
over 29.4M floats. Minimum available memory was 9.93 GiB at 32K. A corrected
4K rerun captured numeric state after the initial dump target was one token
too high. GDN error did not increase monotonically with context length. These
cases broaden exact-answer evidence for this task but do not close state parity
or broader workload quality. The sequential timings are not performance
evidence. The same task at 64K also returned exact answer and token parity,
with matching residency but five differing state fingerprints; GDN relative
L2 was `0.03609` over 29.4M floats and minimum available memory was 8.08 GiB.
The raw 118 MB GDN dumps remain local; checked-in hashes and comparison metrics
are recorded in the context report. This extends task-level functional
evidence only; state parity, broader quality, and staged-miss performance
remain unqualified. See the [4K–64K
follow-up](../../bench/results/2026-10-26-e6-staged-retrieval-context-followup/README.md).
To separate backend arithmetic from the staged route, an opt-in checker mode
now compares Strata and strict NInfer with `--pcie-frac 1.0` in both arms. The
2K one-token cell and full 47-token held-out retrieval matched token IDs,
residency maps and all persistent-state fields; each backend staged the same
97 and 4,556 reads, respectively. This points away from an NInfer-specific
GPU-kernel cause for the CPU-miss versus staged mismatch in this workload.
An accepted-prefix all-layer state capture showed exact GDN state at model
layer 0, `1.076e-9` relative L2 at layer 1 and `9.937e-4` at layer 2, with
`0.03865` global relative L2 across 36 GDN layers. The CPU-miss/staged path
difference and its first triggering operation remain unidentified. These
functional checks do not close staged state parity, broader quality or
performance qualification. See the [2K staged-backend isolation
report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/README.md#staged-backend-isolation).
The three-pair same-day performance screen on this 2K task measured median
decode-rate change `0.00%` for NInfer versus Strata, with only one of three
pairs favoring NInfer; this fails the registered 5%/consistency gate. Median
client latency improved `3.84%`, but it was secondary. Outputs and final state
hashes matched across backends, and both per-request staged-read rows matched.
Per-process resident-map files were not captured in this campaign, so it cannot
qualify performance even apart from the failed decode gate. Seven-pair
confirmation is not justified. See the [staged-backend performance
screen](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/performance-staged-backend-screen/README.md).
A follow-up independent Q8_1 comparison of saved MoE inputs at prompt position
2047 found no activation scale/code difference at sampled layer 1 (all 80
blocks matched). At layer 2, 34 scales and 103 codes differed, with more code
differences at layers 3, 11 and 21. This places the first sampled Q8_1 input
change at layer 2; it does not identify the preceding operation that creates
the change. The per-layer numeric summary and quantizer parity runs are recorded
in the [Q8_1 capture check](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/q8_1-capture-check/README.md).
A supervised stage capture then found the earliest sampled CPU-miss/staged
output delta in model-layer-0 experts 90, 109 and 88: route IDs and inputs
matched; seven other expert parts were bit-identical. The three rows differed
by about `1e-7` relative L2, while both arms matched the independent Q2_0 ×
Q8_1 operator oracle within `5.4e-8`–`9.1e-8`. The combined FFN result
differed by `2.43e-8`; layer-1 projected GDN output was bit-identical. This
points to tiny CPU-versus-GPU arithmetic differences as an early source for
this case, but does not establish the full state or quality impact. Keep E6
state and quality gates open. Details and memory telemetry are in the
[layer-boundary report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md).
An opt-in Q2_0/Q2_0 CPU Q8_1 mirror made three sampled miss-expert rows
bit-identical in an isolated parity check, but a whole CPU-miss request still
differed in six final state fields. Applying the mirror at layer 0 also
changed seven other CPU-executed rows that had matched under the default owner
split; selecting it for all Q2_0 layers did not restore state parity. Keep this
as diagnostic-only; do not promote it or infer a performance benefit. Full
results are in the [layer-boundary report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md).
Adjacent-position captures find only sparse, approximately `1e-7` CPU-miss
expert-row deltas at layer 0, followed by the first sampled material output
amplification in layer 1's GDN/FFN path: GDN output changes by up to
`3.42e-5` and FFN output by up to `1.85e-3` at the two examined positions.
Layer 2 GDN output changes reach `4.74e-3`. Routes and the one generated token
match, but final state does not. This is single-run diagnosis only; the
arithmetic/state cause, quality bounds and performance effect remain open.
Details and compact per-position metrics are in the [adjacent-position
report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#adjacent-position-state-drift-localization).
A CUDA `gdn_step_norm_multi` crossover replay then reproduced each route's
committed layer-1 recurrent state bitwise after positions 2043–2044. Swapping
the captured gate/beta input sequence changed state about 2.6–3.8 times as
much as swapping the starting state for this two-token sample. A one-field
cross-over found gate alone changed state by `3.98e-8` relative L2 after
position 2044, versus `2.27e-8` for beta; combined they changed it by
`4.35e-8`. A second adjacent window (2045–2046) again has a larger isolated
gate effect than beta, but its starting-state effect (`4.22e-8`) exceeds the
combined two-position input effect (`3.51e-8`). Captured `h` and `z` were exact;
normalized output was not evaluated. Local sensitivity depends on the sampled
state/input window, and the source of the upstream deltas and full-model
quality remain unresolved. See the [crossover
report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#cuda-recurrence-crossover-replay).
The CUDA/HIP-compatible parity source rebuilt and linked for HIP on maestro1
at `07ed49d7` with two jobs. The configured SYCL parity target uses a separate,
unchanged `sycl/src/kernels/gdn_parity.cpp`, so this source change did not
require a SYCL rebuild. These are x86_64 compile/link boundaries only. See
the [backend build record](../../bench/results/2026-10-26-e7-maestro-current-source-builds/README.md#2026-10-26-follow-up-on-the-q2_0-cpu-arithmetic-mirror).

Execution note (2026-10-26): an expert-ID filter restricted the diagnostic
Q2_0/Q2_0 Q8_1 mirror to layer-0 experts 83, 88, 90 and 109. At the captured
position, three were routed (88, 90, 109); those were the only CPU expert rows
changed from the default arm, and all ten rows plus the combined layer-0 output
then matched staged GPU output bit for bit. The one-token run retained matching
residency and token ID; PLE state now matched, while GDN, tail, pooled,
pooled-full and KV state still differed. Numeric GDN state was exact at state
ordinal 0, about `1e-9` relative L2 through ordinals 1–3, and first materially
differed at ordinal 4 (`5.07e-6`), compared with the default run's ordinal-2
onset (`9.94e-4`). For this model, every fourth model layer is QSA, so ordinal
4 maps to model layer 5. GDN ordinal 5 reached `0.00329` and global relative
L2 was `0.03792`. This confirms a
local owner-arithmetic contribution and shifts its downstream onset, but does
not resolve later state drift. It is not a quality or performance result. See
the [expert-filter report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#expert-id-filtered-layer-0-mirror).

A further layer-3 capture under the same filter found bit-identical expert
parts and shared output at layer 3 despite a `7.89e-8` relative-L2 input
difference; the combined layer output differed by `1.36e-7`. Routes, generated
token and residency matched, but final state still differed. The GDN dump
retained its first material difference at state ordinal 4 (model layer 5;
`5.07e-6`), with `0.03792` global relative L2. Minimum available/admission
memory was 11.65 GiB. This
shows no material difference in the sampled layer-3 expert operator, but the
state operation that amplifies the incoming delta remains unidentified.
This one-token diagnostic adds no quality or performance qualification. See the
[layer-boundary report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#layer-3-filtered-mirror-follow-up).

A layer-5 GDN state-history capture and CUDA recurrence crossover then found
model-layer-5 committed state already differing at position 2044 (`8.15e-4`
whole-state relative L2), split between recurrent (`3.86e-4`) and convolution
(`8.15e-4`) state. Convolution state was exact at positions 2046 and 2047,
while recurrent state remained different (`2.53e-4` and `2.25e-4`). The
position-2044 start state, replayed over positions 2045–2046,
reproduced both captured backend states bitwise. Swapping GDN inputs changed
the recurrent state by `1.61e-4`/`9.99e-5`, while swapping only the recurrent
start state changed it by `2.71e-4`/`2.30e-4`; isolated gate/beta effects were
around `2e-8`–`3e-8`. At position 2047, GDN `y` and `gdn_out` differences were
`1.69e-4` and `1.95e-3`, followed by a `7.89e-3` layer output difference.
This supports pre-existing recurrent state as the larger local influence in
that selected window, but does not locate the earlier prompt operation that
created it. The replay covers recurrence only, not convolution-state updates,
and does not evaluate normalized output. The
one-token run is not quality/performance qualification; E6 remains open. See
the [layer-5 state-history report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#gdn-state-history-crossover-at-model-layer-5).

An opt-in QSA stage capture at model layer 3, position 125 (token 271) found
the QSA input at `8.16e-8` relative L2, with exact query/current key/current
value and identical 2,051 selected block IDs. Index-query relative L2 was
`9.24e-8`; attention, gated attention, projection and exact next-MoE input
divergence grew to `3.97e-5`, `5.41e-5`, `8.32e-4` and `5.47e-4`. Thus the
measured amplification lies within the QSA attention path, but historical
cached K/V contents and individual attention arithmetic were not captured, so
the precise cause is unresolved. Token IDs matched, while persistent state
still differed. This is localization evidence only, not quality or performance
qualification. The CUDA build, capture analyzer tests and HIP build passed;
SYCL has a separate verifier implementation, while its shared attention header
was rebuilt in the later engine-target check. maestro1 evidence is x86
compile/link only. Minimum available memory was 11.47 GiB; EMC was inaccessible
and energy was not measured. See the
[QSA stage report](../../bench/results/2026-10-26-e6-q2-prefix-context-state-sweep/README.md#qsa-stage-capture-at-model-layer-3).

A separate opt-in capture decoded the 128 selected historical K/V rows that
attention consumed. Of 65,536 values per side, 301 keys and 341 values differed
(`3.91e-5` and `4.93e-5` relative L2). An independent host FP64 attention
replay matched each backend's captured output within `1.97e-7`; the predicted
cross-backend attention delta matched the captured delta within `1.2e-9`
relative L2. For this sampled step, the cached K/V input differences explain
the attention output difference; query, selected IDs and the mathematical
attention operation agree. The earlier attempt with cache capture always
enabled hit the 60-second no-progress watchdog and is excluded; the isolated
opt-in retry completed. This does not locate the earlier source of cached K/V
drift or resolve final-state mismatch. No quality/performance qualification is
made. Minimum available memory was 11.33 GiB. See the [QSA stage and replay
report](../../bench/results/2026-10-26-e6-q2-prefix-context-state-sweep/README.md#qsa-stage-capture-at-model-layer-3).

### E7 — Assess release of the demonstrated integration

1. Run focused regression and at least 30 minutes of sustained service for each
   proposed release profile. Use at least 30 independent requests for tail-latency
   claims. Recheck memory, clocks, thermal behavior, cache/staging reuse and recovery.
2. Rebuild every affected backend and distinguish build/help success from GPU
   execution evidence. maestro1 supplies HIP/SYCL build evidence, not Orin TPS.
3. Publish the source provenance, binary/model hashes, exact launch flags,
   supported codec/shape matrix, dispatch coverage, performance and fallback costs.
   Preserve a one-setting rollback to the Strata backend.
4. Update the main README, integration guide, status, import map and porting notes.
   Record the cache-to-compute interface and ownership lessons for a future Splash
   backend separately from CUDA-specific schedules.

**Exit:** the implemented-integration and performance-qualified outcomes at the
start of this document are assessed explicitly. A bounded release names its
models, hardware, profiles, exclusions and remaining stages; it cannot close
unimplemented expert paths by narrowing the wording of a phase closeout.

Execution note (2026-10-26): current-source HIP and SYCL Release builds passed
on maestro1 at commit `1f9f116b181ef0503f4203f26922b90e213d4615`, and both
binaries passed a model-free `strata --help` check. maestro1 supplies x86_64
build evidence only; it has an Intel HD Graphics 500 and no HIP/SYCL GPU
execution was tested. See the [build report](../../bench/results/2026-10-26-e7-maestro-current-source-builds/README.md).

Execution note (2026-10-25): the assessment finds a bounded CUDA Q2_0 resident
expert path is implemented and exercised, but it is experimental rather than a
release profile. The operator and three-pair service screens failed the useful-
effect threshold; the completed 1K–256K single-sample matrix cannot qualify
performance or quality. No 30-minute NInfer soak was run because no release
profile is proposed. The local CUDA build completed. At the time, HIP/SYCL
build evidence was outstanding; it was later completed on maestro1 as recorded
above. See the [E7 assessment](NINFER_E7_RELEASE_ASSESSMENT.md).

Execution note (2026-10-26): after the state-fingerprint diagnostic source
change, HIP and SYCL were rebuilt from commit
`68de59ab2c6736ca328c83afabe2138123cd7051`. HIP build and CLI help passed.
SYCL compile/link passed after setting `MKLROOT` from the oneMKL environment;
maestro1 has no visible SYCL platform, so the current binary's help startup
aborted. This is not device/runtime qualification. See the [current-source
build addendum](../../bench/results/2026-10-26-e7-maestro-current-source-builds/README.md#2026-10-26-follow-up-on-state-diagnostic-source).

Execution note (2026-10-26): after fixing position-filtered QSA graph recapture,
the complete HIP and SYCL `strata` targets rebuilt from exact source commit
`03806747172378e9eb5a99a2a2194c655675b236` on maestro1 with one build job.
HIP `strata --help` passed. SYCL compile/link passed; `--help` aborted because
maestro1 has no SYCL device. This provides x86_64 compile/link evidence only,
not accelerator runtime or Orin performance qualification. See the [current
source build record](../../bench/results/2026-10-26-e7-maestro-current-source-builds/README.md#2026-10-26-follow-up-on-position-filtered-qsa-capture).

Execution note (2026-10-26): the corrected Orin CUDA binary repeated the
supervised 128-token QSA capture at model layer 3 / position 123. Token,
residency, all compact QSA-stage metrics and selected historical K/V matched
the prior capture exactly. The request still ended with six differing
persistent-state hashes, so this validates the diagnostic and not the E6
correctness or performance gate. See the [repeat capture](../../bench/results/2026-10-26-e6-q2-prefix-context-state-sweep/README.md#position-123-qsa-trace).

Execution note (2026-10-26): the no-trace five-workload staged-miss state
replay completed one pair. Three of five measured response hashes matched,
while final persistent-state fingerprints differed on all five paired
workloads. This is diagnostic evidence without a quality oracle; the staged
miss performance qualification remains open. See the [replay
report](../../bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/README.md#full-order-no-trace-state-replay).

Execution note (2026-10-25): E6's first full top-10 grouped Q2_0 timing screen
passed parity at 64 and 128 tokens but measured 12.18× and 12.31× NInfer/Strata
latency. Replacing the 80-call SwiGLU/Q8_1 chunk loop with a single equivalent
NInfer-side launch changed little. A separate Nsight Systems capture localized
the device cost to NInfer's grouped D3/D4 scalar Q2 loops; Strata uses packed
integer-dot Q2 specializations. A packed `dp4a` adaptation passed grouped
parity and reduced the operator gap to 4.36×, but remained slower. A fresh
three-pair, 8K same-residency service screen found median paired changes of
+0.34% prompt, +1.77% decode, +0.82% client total and +0.36% TTFT, with decode
slower in all three pairs. Outputs and resident-map hashes matched. These
screens do not meet the useful-effect gate, so seven-pair confirmation is not
justified. A follow-up packed four entries per Q2 weight chunk, used two
16-lane rows per warp and specialized the single-entry decode case. Operator
parity passed; grouped NInfer/Strata latency fell to 1.107×/1.120× and the
one-entry ratio to 0.980×. Its new three-pair 8K screen still measured median
+2.74% client total and +2.70% TTFT for NInfer, slower in all pairs with
matching outputs and residency maps. The 256-thread/16-row variation was slower
than the retained 128-thread/eight-row schedule. The one-pair-per-capacity
screening matrix across 1K–256K is
complete: all eligible checks passed, minimum available physical/admission
memory was 11.31 GiB, and all eighteen residency maps matched. Single-sample TPS
and TTFT show no consistent backend advantage; several longer output hashes
differ without an independent quality oracle. The matrix characterizes
configured-context costs and boundaries, but cannot qualify performance or
replace the required matched charts with uncertainty. The E6 performance exit
criteria remain unmet. E7 assessment proposes no profile; see the
[E6 report](../../bench/results/2026-10-25-phase-e6-q2-grouped-throughput/README.md)
and [E7 assessment](NINFER_E7_RELEASE_ASSESSMENT.md).

Corrected-kernel follow-up (2026-10-25): the same five workload shapes were
rerun at 4K and 8K with the precise SwiGLU expression. All 20 measured response
hashes matched their paired controls, and all four residency maps matched. No
consistent backend advantage appeared in the one-pair samples. One 4K/557-token
NInfer measurement had an unexplained 44.35-second client TTFT versus 14.07
seconds for Strata, while its warmup and output hash matched. A randomized
three-pair repeat did not reproduce the spike: median TTFT improved 1.08% and
client completion 0.67%, below the 5% screen threshold. See the [outlier repeat](../../bench/results/2026-10-25-phase-e6-q2-557-repeat3/README.md).
This is not a performance qualification.
See the [corrected context report](../../bench/results/2026-10-25-phase-e6-q2-grouped-throughput/fixed-swiglu-context-check/README.md).

An 8K randomized three-pair screen then repeated all five natural-generation
shapes. All measured outputs and maps matched. Median TTFT changes ranged from
−1.59% to +0.21%; no workload met the 5% threshold, so no seven-pair
confirmation was triggered. One 2,048+128 pair had a 32.6% NInfer decode-time
regression, although its TTFT improved 1.84% and output hash matched; median
client change was +0.05%. E6 therefore remains without a repeatable useful
effect for the resident profile. See the [three-pair 8K report](../../bench/results/2026-10-25-phase-e6-q2-grouped-throughput/fixed-swiglu-8k-paired-screen/README.md).

Execution note (2026-10-25): Nsight Systems was rerun on the four-entry,
16-lane candidate. Its broad harness trace showed similar median per-launch
times for NInfer D3/D4 and native Q2 gate/up/down kernels; the trace combined
several shapes and cannot explain the remaining operator or request-level
gap. Nsight Compute's one-entry profile recorded 64/55 registers per thread
and 53.46%/61.91% achieved occupancy for D3/D4. A separate 64-token/top-10
capture measured achieved occupancy of 65.41%/73.39%, near theoretical
66.67%/75%, with memory throughput 69.86%/70.96%. Profiler-replayed durations
are diagnostic only. The grouped capture does not show a large occupancy
deficit and does not explain the remaining latency gap; no performance claim
is justified by profiling alone. See the [candidate
profiling note](../../bench/results/2026-10-25-phase-e6-q2-grouped-throughput/sub16-single-entry-specialization/README.md).
The subsequent two/four/eight-entry reuse sweep retained four entries: the
two-entry candidate measured 1.234×/1.236× NInfer/Strata latency at 64/128
tokens, while eight entries measured 1.096×/1.117× and regressed the one-entry
case. All passed the operator parity fixture; neither alternative met the 5%
screen threshold, so no service confirmation was run. The four-entry schedule
remains the best measured grouped version, but its grouped and request-level
screens still fail the performance exit.
A restored-source seven-block retest passed parity and measured 1.118×/1.119×
grouped latency at 64/128 tokens, with a 0.980× one-entry ratio. The original
four-entry server and harness hashes were verified after the rebuild.

Execution note (2026-10-25): a temporary fusion of grouped Q2_0 D3,
SwiGLU and Q8_1 packing passed the independent numerical oracle and all tested
single/grouped output boundaries, but regressed grouped latency to 1.280×/1.283×
Strata at 64/128 tokens (the adjacent four-entry control measured 1.103×/1.120× in that
screen). A single-entry timing was 0.950× Strata but is one diagnostic sample.
Nsight Compute found 168 registers/thread and 10.41% achieved occupancy on the
20-block single-entry launch. A later exact grouped invocation used 200 blocks
and achieved 23.92% occupancy against its 25% register-limited theoretical
ceiling, with 40.25% compute and 46.14% memory throughput. Thus severe grouped
grid underfill is not the cause; register pressure and latency are plausible
limits but profiling does not establish causality. The candidate was
removed. No performance gate was met; the four-entry schedule remains the best
tested grouped candidate. The restored CUDA build passed the standard oracle and
grouped parity checks and reproduced 1.109×/1.119× operator ratios. See the
[E6 report](../../bench/results/2026-10-25-phase-e6-q2-grouped-throughput/README.md).

Execution note (2026-10-25): a two-entry version of the temporary fused
kernel also passed all operator parity fixtures, but measured 1.421×/1.418×
Strata latency for 64/128-token top-10 groups (0.946× for one resident entry).
No hardware-counter profile was collected for this schedule; additional
looping and lower weight reuse are candidate explanations, not isolated causes.
It was discarded, and a rebuilt four-entry CUDA target again passed exact
grouped parity. This does not change E6's unmet performance exit.

## Numerical policy

- **Codec/layout:** exact independent decode, offset and guard checks. Moving or
  repacking stored weights must preserve their declared representation.
- **Operator arithmetic:** independent FP32/FP64 mathematical reference with
  explicit activation, intermediate and output representation. Predeclare error
  budgets and finite-value criteria; changing reduction order need not produce
  bit-identical floats, but must pass the agreed contract.
- **Model quality:** document held-out task, log-probability or other justified
  quality limits. Different text alone neither proves failure nor proves quality.
  Do not relax numerical/quality budgets after seeing a fast candidate fail.
- **State/transactions:** directly compare persistent state at accepted prefixes,
  rejection and cancellation. Require exact state when identical arithmetic is
  promised. Any approximate state route needs a separately named contract and
  justified drift bounds; it must not silently replace an exact contract.

## Resource and delivery rules

Keep the single shared physical-RAM authority, six-GiB headroom and separate
3,072-MiB workspace reserve. Include double buffers, transformed weights,
graph pools and transition peaks in admission. Keep all weights and generated
model packs under `~/models/`. Use memory-bounded build jobs and one hardware
campaign at a time. Preserve existing services, clocks, JetPack and CUDA unless
a separately authorized experiment changes them; observe actual clocks instead.

Use the existing reference snapshot and local code first. Shared changes require
CUDA/HIP/SYCL builds before review; unchanged backend fallbacks must compile and
behave as declared. Do not link NInfer's whole application or introduce a second
memory ledger, allocator authority, scheduler or inference service.

Commit and push at each completed stage, and approximately hourly at a finished
task during longer stages. Stage only the intended source and evidence, preserving
the existing dirty benchmark material. Keep raw data, exclusions and negative
results linked from STATUS.md. This planning change starts no build, model
conversion, performance campaign or upstream merge.
