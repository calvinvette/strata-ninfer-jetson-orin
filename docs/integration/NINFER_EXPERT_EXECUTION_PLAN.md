# NInfer expert execution inside Strata

Status: **E0–E5 bounded prototype evidence complete; sampled accepted-prefix and prompt-boundary captures are CUDA-built and smoke-tested; the matched 65K prompt-boundary pair shows measured state divergence before the first generated-token commit, with state also varying between identical warmup and measured prompts within each backend. E6 and E7 remain open pending request-state lifecycle investigation and performance qualification. HIP/SYCL rebuilds for these capture changes are pending compiler availability (updated 2026-10-30).**
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

The ordinary single-request verifier path now invokes the opt-in multi-layer
MoE bundle serializer after its captured device results are available. A
held-out 2K retrieval diagnostic confirmed exact backend equality for routes,
inputs, expert outputs and combined outputs across three selected layers, and
matching final persistent state. The writer had previously been called only
from the batch verifier path, so requested bundles were silently absent for
ordinary windows. See the [writer follow-up](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/moe-bundle-debug7-2049/README.md).
The corrected 160K run then found the first observed backend difference in
layer-7 MoE output (relative L2 `3.82e-8`) after exact agreement through layer
6; the layer-8 MoE input had grown to `6.54e-4`, and route weights changed
without changing expert IDs. Five final persistent-state fields still differ.
The capture-tooling defect is closed, but the amplification path, operator
accuracy, and E6 performance/quality gates remain open. See the [160K bundle
and boundary analysis](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/moe-bundle-fixed-163849/README.md).

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

**Current E6 decision (2026-10-30):** the sampled accepted-prefix diagnostic
showed matching warmup text/state, then measured state differences at the first
checkpoint and token divergence by the 16-token checkpoint. A follow-up
prompt-boundary pair used the same exact 65K prompt for both a 128-token warmup
and 32-token measured request. Warmup boundary and final states matched across
backends. Measured boundary state differed across Strata and NInfer before the
first generated-token commit in GDN, tail, pooled, pooled-full and KV. Within
each backend, the boundary state also differed between identical warmup and
measured prompts. Output text differed after 52 common characters. This points
to request-history or persistent-state variation that precedes generated-token
commit, but does not locate its source. Both experiments use synchronizing
instrumentation and one pair; neither supplies performance evidence. Next,
inspect prompt-cache/session reset and recurrent-state lifecycle, then repeat
minimal boundary controls before resuming throughput qualification. See the
[sampled-capture report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/accepted-prefix-instrumentation-README.md).

**Matched 65K same-backend repeat (2026-10-30):** the current CUDA binary ran
the same 65,536-token prompt twice in one strict-NInfer process, with prompt
cache and PCIe staging disabled and both requests limited to one generated
token. Both prompt-boundary fingerprints matched exactly across all recorded
fields, both responses were `A`, and both requests passed. This confirms
repeatability for this exact input and matched request shape; it does not
resolve the earlier 128-token-warmup/32-token-measurement state difference or
qualify Strata/NInfer parity. The dedicated prompt-boundary hook, absent from
the earlier stale-binary attempt, emitted correctly on the current binary.
That first attempt used the Oct 28 binary and is excluded from project
evidence. No performance, minimum-memory-over-time, energy, or clock result is
claimed; raw logs remain under `/tmp`. A follow-up used a matched 32-token
generation limit; see below.
See the [matched repeat report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/README.md).

**Matched 65K 32-token repeat (2026-10-30):** on the same current binary and
strict-NInfer setup, the identical prompt and generation limit were sent twice
through one process with prompt cache disabled. The first prompt-boundary
fingerprint matched the prior one-token run. The second differed in GDN, tail,
pooled, KV, dead and pooled-full state; PLE, MTP, stale and PLE previous-token
fields matched. Both requests passed, but their 32-token response hashes
differed (`9eb4258b…` then `a26d04bc…`). Thus exact matched request settings
do not guarantee repeatable long-context state or output within one NInfer
process. `session_zero` is called on the no-resume path before each prompt, so
the evidence points to divergence during prompt evaluation or another
request-history-sensitive path after reset; it does not isolate an NInfer
kernel as the cause. No performance or sustained resource claim is made. The
matched Strata-backend control also diverged on its second identical 65K/32
request. Its response hashes matched NInfer by request order, which points to
a shared order-sensitive path and makes an NInfer-only cause less likely. See
the [NInfer report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/32-token-repeat.md)
and [Strata control report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/strata-backend-repeat.md).
Next fingerprint session state immediately after `session_zero`, before
prompt processing, to distinguish reset-state differences from prompt-path
divergence.

**Post-reset capture hook (2026-10-30):** added opt-in
`STRATA_REQUEST_RESET_STATE_HASH` and the API harness flag
`--request-reset-state-hash`. The hook runs directly after the no-resume
`session_zero` calls and stream synchronization, before prompt evaluation. It
fingerprints the full allocated GDN and PLE histories, QSA tail/dead/pooled
index state, and the PLE previous-token window. It does not hash KV bytes:
their old streamed host contents are not live before a request writes cells.
The CUDA build succeeded and the harness tests passed 8/8. A repeated 512-token
smoke produced identical reset fingerprints (`ple_prev=-1,-1`) and identical
prompt-boundary fingerprints. A current-source 65K/32 repeated NInfer pair
then had identical immediate reset fingerprints but differed at the prompt
boundary in GDN, pooled, KV and pooled-full state; response hashes differed as
well. This places the variation after reset and by prompt completion, but the
extra synchronization can perturb the trajectory and the result does not
identify a kernel. The Strata-backend repeat without this reset hook also
diverged, so the behavior is not unique to NInfer. A follow-up added opt-in
`STRATA_PREFILL_STATE_HASH_AT` checkpoints and the harness flag
`--prefill-state-hash-at`. The repeated 65K prompt has matching reset and
recurrent/index fingerprints at 8,192, 16,384, 32,768 and 49,152 tokens; its
final boundary at 65,535 reproduces the prior GDN, pooled, KV and pooled-full
divergence. The earliest observed mismatch is bracketed after 49,152 and at
or before 65,535. Captures synchronize and copy state, so this remains a
diagnostic and not performance or kernel attribution evidence. The 65,536
target emitted no separate sample because the prompt's internal boundary is
65,535. See the [reset-state repeat
report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/reset-state-65k-repeat.md)
and [prompt-position checkpoint
report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/prompt-position-checkpoints.md).
A finer same-process repeat matched compact prefill fingerprints at 53,248,
57,344, 61,440 and 65,535, immediately before the final prompt token is
verified. The first divergence appears immediately after the one-token
verifier window at position 65,535: GDN, pooled state and KV differ, while
PLE, tail, MTP, stale, dead and PLE previous-token state match. This places
the transition in the verifier window and state publication for the last
prompt token, before generated-token commit. It still does not attribute the
change to a kernel or arithmetic cause. See the [final-prompt-token verifier
report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/final-prompt-token-verifier-transition.md).
Per-layer hashes after this window match for the first two ordered GDN states
and first differ at GDN ordinal 2, model layer 2; all 12 QSA layer hashes from
model layer 3 onward differ. A raw verifier capture then found model layer 2's
entering recurrent and convolution state exactly equal, but its input activation
already differed in 2,554/2,560 values (relative L2 `3.10649e-05`). The
difference propagates through layer-2 projections and post-state. A capture at
the preceding model-layer-1 boundary found its residual stream and
hyperconnection term exact, while 1,658/2,560 MoE/output values differed
(maximum `1.73e-06`, relative L2 `5.56115e-05`). A raw layer-1 capture then
found GDN intermediates, its MoE input and pre/post recurrent state all exact;
the first changed captured value is the combined MoE output. Next capture
layer 1's MoE bundle found routes, weights, input and shared output identical;
only expert 320's per-expert output row differed (2,220/2,560 values, relative
L2 `5.24514e-04`). The second request matched the independent Q2_0 × Q8_1
oracle at relative L2 `5.79e-08`, while the first differed at `5.24529e-04`.
The route-weighted expert-row delta predicts the combined-output delta with
cosine similarity `0.99999980`. This localizes the pair's change to that
expert row without identifying the runtime cause. The matched Strata-backend
pair reproduced the same per-request change, with all captured MoE data
byte-identical to NInfer. A focused single-entry grouped replay passed 32
fixed-input repetitions for both backends; direct NInfer D3/D4 matched the
independent FP64 oracle at relative L2 `1.57e-07`. This narrows the issue to
shared service/runtime context. Next capture the actual expert-320 device
weight bytes and Q8_1 activation at the grouped service dispatch, then locate
the first changed intermediate. This remains a request-specific diagnostic,
not a performance conclusion.
See the
[per-layer state report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/verifier-first-layer-state-hashes.md)
and [raw layer-2 transition report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/gdn-layer2-raw-transition.md),
the [layer-1 boundary report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/layer1-boundary-transition.md),
and [layer-1 GDN-to-MoE report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/layer1-gdn-to-moe-transition.md).
The [expert-320 bundle/oracle report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/layer1-moe-expert320-transition.md)
records the per-expert localization.

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

Execution note (2026-10-26): a same-pair 2K prompt capture repeated layer-1
GDN amplification at positions 2043 and 2045. QKV, convolution `h`, and `z`
were exact, while tiny gate/beta deltas preceded `3.42e-5`/`1.31e-5` GDN
output and `9.29e-4`/`1.85e-3` FFN output differences. Same-pair CUDA
recurrence crossover reproduced both arms exactly and found input and
starting-state effects vary by adjacent window. The upstream source of the
gate/beta deltas remains unknown; full state and quality qualification remain
open. See the [layer-1 replay report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#2026-10-26-current-source-layer-1-replay).

Execution note (2026-10-26): two same-day repeats captured layer-0 MoE and
layer-1 GDN stages in the same request pair. Their per-position metrics matched
exactly: layer-0 routes/input were exact, a few expert rows differed at
`~1e-8` scale, and combined output deltas were `2.11e-8`–`3.05e-8`; layer-1
GDN input deltas were `5.48e-8`–`1.25e-7`. The first two requested layer-0
residual-boundary records were not emitted. Follow-up telemetry localized the
missing ordinary-verifier multirow hook; it was then implemented and captured
in a fifth pair. The requests still failed final-state parity. See the [repeat and capture-limit
report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#repeated-layer-0-to-layer-1-capture).

Execution note (2026-10-26): current-source telemetry found the requested
position was outside the slot-batch writer path. Extending the ordinary
verifier boundary capture to multirow windows produced matching-format
layer-0 / position-2043 records in a fifth pair. The input residual and
injection matched bitwise; the combined MoE output differed by `2.90e-8`
relative L2, the next-layer residual by `3.11e-8`, and its read activation by
`6.19e-8`. Inputs, routes and shared output matched exactly; three or four
routed expert rows per position differed around `1e-7` relative L2. This
directly measures the first cross-arm difference at the layer-0 combined MoE
output and its propagation to the next layer. Both arms still failed
persistent-state parity; E6 correctness and performance gates remain open. See
the [multirow boundary capture report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#multirow-ordinary-verifier-boundary-capture).

Execution note (2026-10-26): commit `db95a63c874fa0a7cfc9cff450696cd3a9083990`
rebuilt for Orin CUDA and maestro1 HIP; HIP and SYCL `strata --help` checks
passed with their runtime environments initialized. SYCL uses a separate
source tree unaffected by this CUDA/HIP-only diagnostic change. These checks
do not close E6 correctness or performance gates. See the [backend build
record](../../bench/results/2026-10-26-e7-maestro-current-source-builds/README.md#2026-10-26-follow-up-on-residual-boundary-capture-telemetry).

Execution note (2026-10-26): multirow residual-boundary capture commit
`8ead1358d27b8f8e23c9ac689d62e0d694a373ae` rebuilt on Orin CUDA and maestro1
HIP. The modified verifier compiled and linked; HIP and SYCL model-free help
checks passed with their runtime environments. The fifth paired diagnostic
captured the boundary and localized the first difference to layer-0 combined
MoE output. E6 state and performance qualification remain open. See the
[multirow boundary report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#multirow-ordinary-verifier-boundary-capture)
and [backend build record](../../bench/results/2026-10-26-e7-maestro-current-source-builds/README.md#2026-10-26-follow-up-on-multirow-residual-boundary-capture).

Execution note (2026-10-26): layer-1 captures with the layer-0 mirror showed
exact inputs/routes/shared output but small row deltas in two or three active
experts (`~1e-7`). A per-layer ID-map extension to the opt-in CPU mirror passed
its Orin selector-contract check. Applying position-derived ID lists at both
layers made sampled layer-1 rows/output and GDN state checkpoints bitwise
equal, but final GDN, tail, pooled, pooled-full and KV state still differed.
Next, locate the first later layer that diverges with a final per-layer GDN
state dump. This diagnostic work closes no E6 release gate. See the
[layer-1 intervention report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#layer-1-expert-row-intervention).

Execution note (2026-10-26): mirroring the ten layer-0 Q2_0 experts identified
across positions 2043–2047 made every sampled expert row, combined output and
boundary value match the staged arm exactly. PLE state matched, but the GDN,
tail, pooled, pooled-full and KV fingerprints did not. A repeated capture and
exact CUDA recurrence replay found layer-1 inputs matched at positions
2043–2046; only their differing starting states caused the replayed state
deltas (`1.72e-8`–`1.89e-8` relative L2). The state gap therefore predates the
sampled positions under this intervention. Next, trace the layer-1 state
backward over earlier prompt windows and capture corresponding layer-0 rows.
This is diagnostic evidence only: E6 correctness, quality and performance
gates remain open. See the [mirror/crossover report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#position-union-cpu-mirror-intervention).

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

## Execution update (2026-10-26)

Phase E6 remains open. Per-layer expert mirrors exposed a CPU-fallback versus
CUDA arithmetic difference. On a captured layer-4 expert-106 activation, the
CUDA result matched an independent FP64 Q2_0×Q8_1 runtime-contract oracle to
`6.05e-8` relative L2; CPU was `9.61e-4` away. A second expert put both paths
near `1e-7`, so the larger gap is activation/expert dependent. The active
grouped NInfer route matched Strata's grouped Q2_0/Q8_1 operator exactly but
measured 1.111× and 1.122× Strata latency for 64/128-token top-10 groups. The
separate NInfer-derived D3/D4 candidate failed its oracle and is not called by
the service. Do not continue serial per-layer mirroring as a release gate;
next prioritize held-out task-quality bounds and randomized paired request
measurements for the active path. Exact persistent-state parity remains a
diagnostic result, not a task-quality substitute when CPU and CUDA arithmetic
differ. No performance or quality gate is closed. HIP and SYCL builds and
model-free help checks passed on maestro1 (x86_64 evidence only). Details are
linked in [STATUS](STATUS.md).

A three-pair randomized request screen then compared Strata and NInfer compute
with staging enabled in both arms for the held-out 2K+128 shape. All outputs
and resident maps matched. Paired median changes were +1.91% prompt TPS,
+2.27% decode TPS, −1.81% first-visible TTFT and −1.12% client time; no metric
reached the 5% threshold, so no confirmation campaign was triggered. Minimum
available memory was 11.43 GiB. This narrows the product result: the active
NInfer grouped path has no demonstrated request-level gain on this shape.
Continue to other planned shapes and the task-quality gate before E6 closeout.
See the [staged-compute screen](../../bench/results/2026-10-26-e6-q2-staged-compute-screen/README.md).

The same comparison was expanded to three randomized pairs across all five
8K natural-generation shapes (512+64, 2,048+128, 172+64, 557+64 and
1,069+64). All 15 output hashes and residency maps matched. Paired median
prompt-TPS changes ranged from −4.12% to +1.19%, decode-TPS changes from
−0.82% to +0.86%, and client-time changes from −0.27% to +3.59%. No workload
met the 5% screen threshold, so no seven-pair confirmation was triggered.
Minimum available memory was 11.48 GiB. This completes the 8K staged-compute
screen only; the prescribed context-capacity coverage and remaining task-
quality gates are still open. See the [full 8K screen](../../bench/results/2026-10-26-e6-q2-staged-compute-full-screen/README.md).

The 256K configured-capacity extension used the same paired staged-compute
comparison for a short 2,048+128 request. Its paired medians were +1.57% prompt
TPS, 0% decode TPS, −0.80% first-visible TTFT and −1.09% client time. One
measured output differed in pair 3; a text-capture rerun did not reproduce the
mismatch but did not explain it. Therefore this screen is unqualified for task
quality or performance, and does not establish long-prompt behavior. Minimum
available memory was 7.14 GiB. The low-capacity 1K staged-compute cell is now
complete. Its 512+64 request produced matching outputs and residency maps in
all three pairs; median paired changes were −1.64% prompt TPS, −1.10% decode
TPS, +1.24% first-visible TTFT and +1.08% client time. No 1K median reached
the 5% screen threshold; minimum available memory was 11.67 GiB. These are
capacity-boundary screens only and do not close task-quality or performance
gates. E6 remains open. See the [256K report](../../bench/results/2026-10-26-e6-q2-staged-compute-256k-screen/README.md) and [1K report](../../bench/results/2026-10-26-e6-q2-staged-compute-1k-screen/README.md).

The 2K capacity 512+64 staged-compute cell has also completed three randomized
pairs. Outputs and resident maps matched throughout. Median paired changes
were −0.65% prompt TPS, +3.41% decode TPS, +0.54% first-visible TTFT and
−0.40% client time; none reached the 5% threshold. Minimum available memory
was 11.65 GiB. This remains a screen only. See the [2K report](../../bench/results/2026-10-26-e6-q2-staged-compute-2k-pp512-screen/README.md).

The 4K 512+64 staged-compute screen likewise completed three randomized pairs
with matching output and resident-map hashes. Median paired changes were
−1.97% prompt TPS, +2.27% decode TPS, +2.18% first-visible TTFT and +0.95%
client time. Minimum available memory was 11.60 GiB. None met the 5% threshold;
E6 remains open. See the [4K report](../../bench/results/2026-10-26-e6-q2-staged-compute-4k-pp512-screen/README.md).

At the same 4K capacity, the 2,048+128 request completed three randomized
pairs with matching output and residency hashes. Median paired changes were
−1.44% prompt TPS, +2.30% decode TPS, +1.43% first-visible TTFT and +0.50%
client time; minimum available memory was 11.63 GiB. No performance gate was
reached. See the [4K 2K-prompt report](../../bench/results/2026-10-26-e6-q2-staged-compute-4k-pp2048-screen/README.md).

At configured 16K capacity, the 512+64 staged-compute cell also matched output
and resident-map hashes in all three pairs. Median changes were −2.92% prompt
TPS, 0% decode TPS, +1.83% first-visible TTFT and +1.09% client time. Minimum
available memory was 11.32 GiB. No median met the 5% threshold. See the [16K
report](../../bench/results/2026-10-26-e6-q2-staged-compute-16k-pp512-screen/README.md).

The 32K-capacity 512+64 cell matched outputs and residency in all three pairs.
Median paired changes were −1.28% prompt TPS, −3.41% decode TPS, +1.36%
first-visible TTFT and +1.52% client time. Minimum available memory was
10.92 GiB. This does not reach the 5% screen threshold. See the [32K report](../../bench/results/2026-10-26-e6-q2-staged-compute-32k-pp512-screen/README.md).

At 64K capacity, three 512+64 pairs matched outputs and resident maps, with
10.09 GiB minimum available memory. Median changes were −0.37% prompt TPS,
+1.15% decode TPS, +0.45% first-visible TTFT and +0.06% client time. Pair
spreads were wide (prompt TPS −9.47% to +9.92%), making this inconclusive; it
does not qualify a gain. See the [64K report](../../bench/results/2026-10-26-e6-q2-staged-compute-64k-pp512-screen/README.md).

At 128K capacity, the 512+64 cell matched all measured output and residency
hashes. Median paired changes were +0.45% prompt TPS, 0% decode TPS, −0.59%
first-visible TTFT and −0.08% client time; minimum available memory was
8.47 GiB. No median reached the screen threshold. See the [128K report](../../bench/results/2026-10-26-e6-q2-staged-compute-128k-pp512-screen/README.md).

At configured 256K capacity, a separate 512+64 staged-compute screen matched
outputs and resident maps in all pairs. Minimum available memory was 7.10 GiB.
Median changes were −2.89% prompt TPS, 0% decode TPS, +3.17% first-visible
TTFT and +2.51% client time, but paired spreads were wide and no median passed
the threshold. This does not erase the one output mismatch in the separate
2,048+128 256K screen. See the [512-token 256K report](../../bench/results/2026-10-26-e6-q2-staged-compute-256k-pp512-screen/README.md).

A 4K-capacity 1,069+64 request also completed three randomized staged-compute
pairs with matching outputs and residency. Median paired changes were −0.98%
prompt TPS, 0% decode TPS, +1.10% first-visible TTFT and +1.00% client time;
minimum available memory was 11.59 GiB. No metric passed the 5% screen. See the
[4K 1,069-token report](../../bench/results/2026-10-26-e6-q2-staged-compute-4k-pp1069-screen/README.md).

The 4K 557+64 cell matched output and residency hashes in all pairs. Median
changes were −1.01% prompt TPS, 0% decode TPS, +0.92% first-visible TTFT and
+0.18% client time; minimum available memory was 11.58 GiB. One pair showed a
decode outlier without output divergence, so no stable performance effect is
claimed. See the [4K 557-token report](../../bench/results/2026-10-26-e6-q2-staged-compute-4k-pp557-screen/README.md).

The 4K 172+64 cell matched outputs and resident maps across all pairs. Median
changes were −1.35% prompt TPS, 0% decode TPS, +1.18% first-visible TTFT and
+0.46% client time; minimum available memory was 11.57 GiB. A large decode
and client improvement in one pair did not repeat. See the [4K 172-token
report](../../bench/results/2026-10-26-e6-q2-staged-compute-4k-pp172-screen/README.md).

At 16K capacity, the 2,048+128 cell matched outputs and resident maps in all
pairs. Median changes were −2.58% prompt TPS, 0% decode TPS, +2.56% first-visible
TTFT and +1.83% client time; minimum available memory was 11.29 GiB. Pair
direction varied and no median reached threshold. See the [16K 2K-prompt
report](../../bench/results/2026-10-26-e6-q2-staged-compute-16k-pp2048-screen/README.md).

At 32K capacity, the same 2,048+128 shape matched output and residency hashes
in all pairs. Median changes were −0.44% prompt TPS, −2.30% decode TPS, +0.59%
first-visible TTFT and +0.56% client time; minimum available memory was
10.88 GiB. No performance screen threshold was met. See the [32K 2K-prompt
report](../../bench/results/2026-10-26-e6-q2-staged-compute-32k-pp2048-screen/README.md).

At 64K capacity, the 2,048+128 workload also matched output and resident-map
hashes across three pairs. Median changes were +0.89% prompt TPS, −1.20%
decode TPS, −1.01% first-visible TTFT and −0.48% client time; minimum
available memory was 10.05 GiB. No metric reached the 5% threshold. See the
[64K 2K-prompt report](../../bench/results/2026-10-26-e6-q2-staged-compute-64k-pp2048-screen/README.md).

At 128K capacity, the 2,048+128 cell likewise matched outputs and resident
maps across all pairs. Median changes were −0.46% prompt TPS, 0% decode TPS,
+0.31% first-visible TTFT and −1.16% client time; minimum available memory
was 8.36 GiB. No median met the screen threshold. Pair 3 had a decode-rate
outlier. See the [128K 2K-prompt report](../../bench/results/2026-10-26-e6-q2-staged-compute-128k-pp2048-screen/README.md).

A repeated 256K 2,048+128 three-pair capture diverged on all three measured
output hashes, despite temperature zero and identical resident maps. Median
prompt TPS, TTFT and client-time changes crossed the 5% screen (+5.57%,
−5.27%, −5.66%), but the output gate failed, so timings are not qualified and
no confirmation was run. Distinct completion hashes recur across pair and arm
positions; the evidence does not isolate the backend as the cause. This
generic generation prompt has no independent task-quality oracle. Minimum
available memory was 7.15 GiB. The earlier one-pair matching text-capture
diagnostic is superseded by this repeat. See the [captured repeat report](../../bench/results/2026-10-27-e6-q2-staged-compute-256k-pp2048-repeat/README.md).

An independent 2,048-token retrieval/arithmetic task was also run with the
active staged Strata and strict NInfer grouped-compute paths. Both returned
the exact expected answer in 47 tokens; token IDs, the identical residency
map, and all nine final persistent-state fields matched. Minimum available
memory was 11.59 GiB. This passes one bounded held-out task/state cell, but the
sequential diagnostic supplies no timing evidence and does not close the broad
quality or performance exits. See the [active-compute quality report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-2k/README.md).

The same exact-answer task was extended to a 4,096-token prompt. Strata and
strict NInfer staged compute again returned the expected answer in 47 tokens,
with identical token IDs, residency and all nine final state fields. Minimum
available memory was 11.62 GiB. This strengthens correctness coverage through
4K prompt length but is not a timing estimate or near-limit context test. See
the [4K active-compute quality report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-4k/README.md).

An 8,192-token version under a 16K capacity also passed the exact-answer,
token-ID, resident-map and all-nine-field final-state comparisons between the
active staged compute backends. Minimum available memory was 11.40 GiB. This
extends bounded correctness coverage through an 8K prompt; it is neither
near-limit 16K ingestion nor performance evidence. See the [8K report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-8k/README.md).

The exact-answer task also passed at a 16,384-token prompt under a 32K cap.
Both staged backends matched answer, token IDs, residency and all nine final
state fields. Minimum available memory was 11.00 GiB; OOM counters were zero.
This is bounded correctness evidence, not near-limit 32K throughput. See the
[16K active-compute report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-16k/README.md).


The held-out exact-answer task now passes through 32,768 prompt tokens under a
64K configured cap for both active staged grouped-compute backends. Answer, all
47 output token IDs, residency map and all nine final state fields match;
minimum available RAM was 10.03 GiB. This is sequential correctness evidence,
not a 64K near-limit or performance result. See the [32K report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-32k/README.md).


At 65,536 prompt tokens under a 128K cap, the held-out task passed for both
active staged grouped-compute backends: exact answer, all 47 output token IDs,
resident map and all nine final state fields matched. Minimum sampled
available memory was 8.53 GiB; peak swap use was 6.95 GiB, with zero OOM events
and the six-GiB guard maintained. This is correctness evidence with observed
memory pressure, not a 128K near-limit or performance result. See the [64K
report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-64k/README.md).


The 131,072-token held-out task also passes under a 256K cap for both active
staged grouped-compute backends: exact answer, 47 output token IDs, residency
and all nine final state fields match. Minimum available memory was 6.80 GiB
(0.80 GiB over the enforced floor), peak swap 1.96 GiB and OOM counters zero.
The 43.7-minute sequential diagnostic is not performance evidence. This
correctness cell has a narrow memory margin and does not establish near-limit
256K ingestion. See the [128K report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-128k/README.md).


A 163,840-token held-out retrieval/arithmetic check returned identical exact
text, token IDs and residency for the two active staged grouped-compute paths,
but failed final-state parity in GDN, tail, pooled, pooled-full and KV.
Minimum available RAM was 6.79 GiB, peak swap 1.71 GiB; the supervisor ended on
the checker failure, not the memory guard. This is a correctness failure, not
a memory-unsupported result. Diagnose the source before accepting larger-context
qualification; text equality alone is insufficient. See the [160K report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/README.md).


A corrected accepted-prefix GDN dump for the 160K mismatch found layer 0 exact,
a tiny layer-1 difference (relative L2 `6.87e-10`), then growth at layer 2
(`3.41e-6`) and layer 3 (`4.41e-3`), with global relative L2 `3.60%`. A
follow-up capture found bitwise-equal layer-2 state at the prompt boundary in
one separate run; the later same-run trace below corrects that inference,
then a first observed `y` difference on the first generated token (relative L2
`2.50e-8`, max absolute delta `5.96e-8`). A raw pre-normalization `o` capture
now shows that the difference is already present before normalization at
position 163840 (relative L2 `3.13e-8`); both `o` and `y` jump at position
163877 (`5.11e-4` and `1.41e-3`) where other GDN intermediates first split
substantially. An independent FP64 recurrence replay over all 46 captured
positions matches each raw `o` trace to worst relative L2 `3.52e-7` (Strata)
and `3.58e-7` (NInfer), below the registered `1e-5` operator bound. At
position 163877, the captured `h`, gate and beta inputs already differ
substantially; the first layer-2 input differences in this trace occur at
163844. The replay starts from a separate same-task boundary-state capture, so
it does not establish same-run trajectory parity or locate the upstream layer
operation. An opt-in instrumentation control with capture disabled passed the
2K task with full state parity. A same-run accepted-prefix trace later found a
tiny layer-2 state delta at position 163839 (`1.701e-8` relative L2), but
bitwise-equal captured layer-1 output and next-layer-2 boundary tensors at
generated position 163844. At that position GDN `x`, gate and beta differed.
The fused grouped-residual read capture passed the 2K control with all five
captured outputs equal and final state exact. A 160K capture at position
163844 also found all five fused-read outputs bitwise equal even though final
state still failed. Since a separate pair showed GDN `x` differing at that
same position and the GDN diagnostic copies `mixed` directly as `x`, repeat
with both captures enabled in one pair to resolve the between-run discrepancy.
See the
[GDN localization
note](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/GDN_STATE_LOCALIZATION.md).

**Correction (2026-10-27):** the fused grouped-residual read equality described
above is withdrawn. The 2K and 160K files held zero-filled pinned buffers; the
capture flag was set during allocation before graph copies were queued. Later
2K instrumentation selected the requested row during graph recording but
still failed the runtime capture guard. No fused-read numerical result is
qualified until the graph replay/flag lifecycle is repaired and a nonzero
payload is independently checked. Keep E6 open.


**E6 instrumentation update (2026-10-27):** repaired the fused GR-read capture
path. Its Q8_1 availability boolean had been treated as an early diagnostic
exit, and target graph refresh needed to occur only after staging inputs for
the selected window. A paired 2K check now records nonzero captures and proves
bitwise equality across `xn`, `lo`, `rs`, `inj_out` and `mixed`; same-run GDN
`x` equals captured `mixed` on both backends. Full 48-token retrieval and final
state parity also pass. This supersedes the prior note that the 2K capture
guard remained unresolved, while preserving the retraction of the old
zero-filled 2K/160K data. The simultaneous 160K capture at position 163844 is complete. Both backends
match bitwise for the fused read and same-run GDN `x`, but final recurrent and
KV state still differs by the end of the task. The same-run 163849/163877 trace is complete: `xn` first differs slightly at
163849 (relative L2 `1.38e-8`), and GDN `x` grows to relative L2 `6.88e-4` at
163877. Continue by tracing the 163849 `xn` input to its producer and checking
it against an independent numerical oracle; keep E6 open.


**E6 long-context diagnostic update (2026-10-27):** repaired fused GR-read and
GDN captures now validate at 2K and at 160K position 163844. At 160K, all five
read fields match bitwise across backends, and `mixed` is equal to each
backend's same-run GDN `x`. Exact answer and token IDs still accompany a final
state mismatch in GDN, tail, pooled, pooled-full and KV. Supervised memory
minimum was 6.72 GiB with no OOMs. The prior separate-run GDN `x` difference
at 163844 is not reproduced. The next diagnostic is a paired capture of later
generated positions 163849 and 163877, where earlier traces first observed
large recurrence deltas. Phase E6 is not complete.


**E6 multi-position localization (2026-10-27):** with both fused read and GDN
records captured in one pair, layer-2 `xn` first differs at generated position
163849 by relative L2 `1.38e-8`; each fused `mixed` output exactly equals its
same-run GDN `x`. The GDN `x` delta grows to relative L2 `6.88e-4` at 163877.
This narrows the earliest observed discrepancy to the producer/input of `xn`,
without assigning correctness to either backend. Trace the producer and use an
independent oracle next; full E6 exit criteria remain unmet.


**E6 diagnostic v2 (2026-10-27):** the selected fused-read capture now stores
raw residual `R` before normalized `xn`, with backwards-compatible v1 parsing.
The 2K paired full-answer task passed exact output and persistent-state checks;
all six captured stages matched bitwise, and six comparator tests pass. At the
first small 160K split, a 46-row all-generated-position trace found `R` already
differs at 163849 (58/2,560 values; relative L2 `3.72e-9`), before `xn`
normalization. The first nine positions matched exactly. `R`/GDN `x` differences
also appeared at 163854 and 163875, grew sharply at 163877 (`R` relative L2
`3.70e-5`, GDN `x` `6.88e-4`), then shrank at 163878. Each same-run GDN `x`
equals that backend's GR `mixed` output at every captured position. A
selected-boundary repeat at 163849 then found the layer-1 output, all eight
boundary tensors, every GR-read v2 field and same-run GDN `x` bitwise equal.
The earlier `R`/`xn`/`x` split at this position was not reproduced, so the
onset is not stable enough to assign to its producer. The answer, all 47 token
IDs and resident map match, but final GDN, tail, pooled, pooled-full and KV
state differ. The all-position diagnostic stayed above the 6-GiB floor (6.55
GiB minimum, 1.76 GiB peak swap); the selected-boundary repeat also stayed
above it (6.70 GiB minimum, 0.86 GiB peak swap). Both had zero sampled OOMs
and neither provides performance qualification. See the [all-position
evidence](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/GDN_STATE_LOCALIZATION.md#all-generated-position-gr-read-v2-capture)
and [selected-boundary repeat](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/GDN_STATE_LOCALIZATION.md#selected-boundary-repeat-at-the-reported-first-split).
Next add bounded multi-layer boundary capture at a fixed accepted position,
repeat with identical capture settings, and locate the first reproducible
boundary difference before applying an independent oracle. E6 remains open.

**Diagnostic tooling follow-up (2026-10-27):** implemented opt-in capture of
multiple residual boundaries at one fixed token position. Each layer is emitted
as an existing `STBNDY2` record, and the comparator aligns concatenated records
by layer; the legacy singular capture remains available. Orin CUDA build and
204 integration Python tests pass. The exact source configures for HIP and SYCL
on maestro1, and the changed verifier translation unit compiles for both. A
one-job full HIP build is in progress; full SYCL linking remains pending. The
root filesystem has 1.1 GiB free, while `/mnt/sda2` has 56 GiB free. No
multi-layer model result is available yet. The paired long-context capture is
running on Orin; it preserves the 6 GiB physical-memory floor. maestro1 is used
for compilation only. E6 remains open.

**E6 multi-layer localization update (2026-10-27):** an all-layer 160K pair
captured position 163849 across all 47 model layers. Layer 0 matched exactly;
the first observed split was layer-1 `layer_output_moe` (488/2,560 values,
relative L2 `2.895e-8`), with growing downstream differences. Layer-2 GR-read
raw `R` also differed slightly. The task text, generated token IDs and
residency matched, but final persistent state did not. A lower-density capture
at the same position had matched bitwise, so this does not yet establish a
reproducible MoE discrepancy. The 6-GiB floor held (6.61 GiB minimum; no OOM).
The next paired capture repeats all-layer, GR-read and GDN settings while
adding layer-1 route/input/expert-part/output data, followed by an independent
oracle if the split reproduces. E6 remains open. The exact-source HIP full
build passed on maestro1; the matching SYCL full build is still underway.

**E6 targeted MoE repeat (2026-10-27):** with all 47 boundary layers captured
at position 163849, adding layer-1 MoE internals showed byte-identical route,
input, per-expert parts and combined output across backends. Layers 0–6 match;
the first difference in this run is layer-7 `layer_output_moe` (638/2,560
values; relative L2 `3.82e-8`). Layer-2 GR-read and GDN `x` are exact in this
pair. This differs from the prior run's layer-1 split, confirming onset
sensitivity to run or instrumentation. Both arms match text, token IDs and
residency but fail final persistent-state parity; minimum available memory was
6.69 GiB and OOM counters remained zero. Diagnostic only, not performance
qualification. Next repeat with layer-7 route/input/parts/output capture, then
compare against an independent oracle if reproducible. E6 remains open.

The exact-source maestro1 builds completed for HIP and SYCL. HIP binary SHA256:
`a2edc59edb38fc4e9c859af985a42895b55521fb77f9e0133910cdf0a4e1776b`; SYCL
binary SHA256:
`373288b3696c83016f67961f6427124b4a7d9dc025a9885e554afda1d6e685e4`. SYCL
links successfully, but no suitable device is available on maestro1 for runtime
launch. These checks establish compilation only, not accelerator qualification.

**E6 layer-7 MoE capture (2026-10-27):** adding layer-7 route/input/parts/output
to the all-layer 160K pair found all four MoE captures byte-identical and all
boundaries through layer 7 equal. The first difference in this run is at layer
8 (runtime output relative L2 `2.77e-4`, MoE output `7.62e-3`, next-layer `xn`
`1.63e-3`); layer-2 GR-read and GDN `x` are exact. The previous run had instead
shown a tiny layer-7 split, while a prior run split at layer 1. This changing
onset is run/capture-sensitive and does not assign a fault. Exact text, tokens
and residency still match, but final state does not. Minimum available memory
was 6.66 GiB with zero OOMs. Next capture layer-8 MoE internals at the same
position with all-layer settings. E6 remains open.

**E6 layer-8 MoE capture (2026-10-27):** capturing layer-8 MoE internals with
all boundaries moved the observed first difference back to a small layer-7
MoE-output delta (`3.82e-8` relative L2). Layer-8 input differs slightly, but
route, expert parts and shared/combined output are byte-identical. The prior
pair without layer-8 capture showed a large layer-8 split. This confirms the
instrumentation changes the observed trajectory and prevents assigning a stable
source yet. Exact answer, tokens and residency still match; final persistent
state does not. Minimum available memory was 6.74 GiB, with zero OOMs. Next
implement one-position multi-layer MoE capture for simultaneous layer 1, 7 and
8 diagnostics, then use an independent oracle on a reproducible split. E6
remains open.

**E6 simultaneous MoE bundle attempt (2026-10-27):** the opt-in packed
multi-layer capture and comparator are implemented and committed as
`754bb6e5`. A paired 160K Q2_0 run captured all 47 residual boundaries at
position 163849, but emitted no MoE bundle for either arm. Both arms still
matched exact output, token IDs and residency while persistent state differed;
the new harness correctly marks missing requested bundles as failure. The
capture failure cause is unresolved, so no expert arithmetic oracles have yet
been applied to this run. Minimum available memory was 7.04 GiB, peak swap
6.01 GiB, and sampled OOM-kill counters were zero. See the
[run report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/moe-bundle-163849/README.md).
Next instrument the writer call/lifecycle on a short workload that emits a
boundary record, fix and retest the bundle path, then repeat the paired 160K
capture before applying independent expert oracles. E6 remains open.

**E6 layer-8 GDN diagnostic (2026-10-28):** after fixing ordinary verifier
bundle serialization, a paired 160K run captured residual boundaries, layer-7
and layer-8 MoE bundles, and layer-8 GDN `o`/`y`. The first observed MoE delta
was again layer 7 expert arithmetic at relative L2 `3.82e-8`; at layer 8,
GDN `o`/`y` differed by `6.49e-5`/`7.08e-4`, followed by MoE input at
`7.37e-4`. Routes stayed identical but layer-8 route weights changed; combined
MoE output differed by relative L2 `8.25e-3`. This makes GDN propagation a
candidate amplifier, not a proven cause: repeated captures remain sensitive to
instrumentation and run conditions. Both arms returned matching exact text,
token IDs and residency, but persistent GDN/tail/pooled/pooled-full/KV states
diverged. Minimum available memory was 6.58 GiB, peak swap 1.38 GiB, and OOM
kills were zero. The captured layer-7 outputs for all ten selected experts
were compared with the independent Q2_0/Q8_1 oracle: relative L2 was about
`5.7e-8`–`9.4e-8`, with NInfer closer for one expert and equal reported
precision for nine. Parsing the captured layer-8 stages showed `x` differed
by `6.22e-8`; `qkv`, convolution output `h`, and `z` were exact, while tiny
gate/beta deltas preceded a `7.08e-4` relative difference in `y` and `2.41e-3`
in projected GDN output. This localizes amplification to recurrence/normalization
in this pair, but does not establish a stable cause or end-to-end state parity.
Next repeat with controlled GDN stage captures. See the [diagnostic
report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/moe-layer8-gdn-163849/README.md).
E6 remains open.

**E6 reduced-capture GDN oracle repeat (2026-10-28):** a paired 160K run
captured the committed layer-8 state at 163848 and recurrence inputs/raw output
at 163849, with only layer-7/8 MoE bundles. The independent FP64 recurrence
oracle reproduced raw `o` at relative L2 `1.11e-7` for Strata and `7.99e-8`
for NInfer. Both arms' recurrence calculations are consistent with the
equation oracle for their own inputs and states; NInfer is slightly closer in
this sample. However, the incoming recurrent states already differed by
`2.64e-4` relative L2 at 163848, while the convolution portions matched exactly.
At 163849, `qkv`, convolution output `h`, and `z` matched; small `x`/gate/beta
deltas preceded larger `y` and projected-output differences. The 47-token exact
answer and residency matched but the persistent state did not. Thus this
isolates correct per-arm recurrence execution, not the origin of earlier state
divergence. Minimum available memory was 7.14 GiB, peak swap 6.58 GiB, OOM
kills zero. Next trace the earliest divergent layer-8 state update across the
preceding accepted positions, using the least intrusive practical capture.
See the [oracle repeat report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/moe-gdn-oracle-163849/README.md). E6 remains open.

**E6 layer-8 state timeline (2026-10-28):** a state-only paired capture at
positions 163840–163849 matched exactly through position 163846. The first
recurrent-state delta appeared at 163847 (relative L2 `1.37e-8`, max
`1.49e-8`) and stayed near `1.3e-8` through 163849; convolution state remained
bitwise equal. This sharply differs from the preceding broader capture, where
the position-163848 recurrent state differed by `2.64e-4`. Thus even state-only
and instrumented runs produce different trajectories; neither identifies a
stable root cause. Both arms returned matching exact text, tokens and
residency, but final persistent state differed. Minimum available memory was
6.87 GiB, peak swap 4.50 GiB, OOM kills zero. Next determine whether divergence
reappears after position 163849 with a minimal state-only timeline extended
through the generated answer, then compare the first differing update against
the independent recurrence oracle. See the [timeline report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-state-timeline-163840-163849/README.md). E6 remains open.

**E6 full-answer layer-8 state timeline (2026-10-28):** the state-only
capture extended through all accepted input positions for the 47-token answer.
Layer-8 recurrent and convolution states matched at 163840–163841, then both
split at 163842 (relative L2 `2.30e-4` and `9.10e-4`). Recurrent difference
peaked at `3.81e-3` by position 163869. This conflicts with the preceding
state-only pair, which first split at 163847 by only `1.37e-8`; broad capture
had also produced a different magnitude. The run confirms strong trajectory
sensitivity, not a stable cause. Text, tokens and residency matched; final
persistent state did not. Minimum available memory was 6.54 GiB, peak swap
1.40 GiB, and OOM kills were zero. Next capture layer-8 GDN inputs and the
state update at 163842 and check against the independent recurrence oracle.
See the [full-answer timeline report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-state-timeline-full-answer/README.md). E6 remains open.

**E6 focused layer-8 step at 163842 (2026-10-28):** the committed pre-step
layer-8 state matched bitwise, but incoming GDN `x` already differed by
relative L2 `3.90e-4`. The independent FP64 recurrence oracle reproduced raw
`o` within `1.0e-7` for both backends, while post-step recurrent/convolution
state differed by `2.30e-4`/`9.10e-4`. This locates the cause upstream of the
layer-8 recurrence for this sample; the recurrence formula itself matches the
oracle. The exact answer, tokens and residency matched, but persistent state
did not. Minimum available memory was 6.56 GiB, peak swap 1.31 GiB, OOM kills
zero. Next compare the layer-8 input with layer-7 residual/MoE captures at this
same position. See the [focused step report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-first-split-163842/README.md). E6 remains open.

**E6 same-position upstream capture repeat (2026-10-28):** adding layer-7 MoE
and layer-7/8 boundary captures at 163842 changed the observed result again.
All boundary fields through layer 8, layer-7 expert internals, layer-8 raw `o`,
normalized `y`, and pre/post states matched bitwise; both recurrence oracles
were at `1.32e-7` relative L2. Final persistent state nevertheless differed.
This conflicts with the preceding same-position GDN capture, which showed
`3.90e-4` input and `9.10e-4` post-state deltas. The instrumentation-sensitive
trajectories do not establish a stable earliest split. Do not change the
backend based on these captures. E6 remains open for minimally instrumented
paired repeatability and state parity. See the [same-position report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-upstream-layer7-163842/README.md).

**E6 ordinary-path long-context controls (2026-10-28):** two paired 160K Q2_0
retrievals ran with no optional capture sidecars. Both backends matched all 47
token IDs, exact answer, and residency in both pairs, but final `gdn`, `tail`,
`pooled`, `pooled_full`, and `kv` state differed within each pair. Their raw
state-byte fingerprints for those fields also changed between pairs, for both
backends. This confirms both ordinary-path cross-backend divergence and
run-to-run variation in hashed active state bytes; the hashes do not quantify
the numerical differences. The cause remains unresolved, so the localized
capture trajectories cannot yet support a backend change. Minimum available
memory was 6.64 and 6.59 GiB; peak swap was 4.55 and 1.30 GiB; sampled OOM kills
were zero in each run. See the [first control report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/minimal-paired-control/README.md)
and [repeat 2 report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/minimal-paired-control-repeat2/README.md).
**Follow-up GDN ordinal hashes (2026-10-28):** a GDN-only per-ordinal hash pair
completed with matching answer, token IDs, and residency, but the same five
final persistent state fields still differed. Ordinal 0 matched across both
backends and both runs with per-ordinal hashes; ordinal 1 was the first
cross-backend difference, and ordinals 1–35 changed across repeated runs for
each backend. This localizes observed run-to-run byte variation to GDN state
from ordinal 1 onward, without quantifying numerical deltas or identifying a
cause. A preceding all-QSA-layer hash attempt exceeded the request watchdog
after generation and is not a valid final-state comparison. Do not use that
QSA-layer setting at this context under the current watchdog. See the
[GDN-only report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/minimal-paired-control-gdn-layer-hashes/README.md)
and [watchdog report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/minimal-paired-control-layer-hashes/README.md).
**E6 final-state GDN numeric dump (2026-10-28):** a no-capture 160K pair wrote
both final accepted-prefix GDN arrays. Ordinals 0–2 match or differ only at
relative L2 below `1.1e-9`; ordinal 3 (model layer 4) is `2.985e-3`, rising to
`6.73e-2` at ordinal 26. Whole-array relative L2 is `3.042e-2`. The exact
answer, tokens, and residency match; final persistent-state parity still fails
in the same five fields. These end-state measurements do not identify the
first divergence during prompt processing. Next capture the inputs and GDN
stages around model layer 4 at a fixed accepted position, with a boundary
capture after model layer 3, then repeat under identical capture settings
before attributing the split. That focused pair found layer-4 `x` already
differs by `5.74e-3` relative L2; layer-3's MoE row differs by `1.48e-2`, while
layer-4 raw GDN `o` differs by `2.53e-3`. It did not capture the pre-step
layer-4 recurrent state. Next capture layer-3 QSA and MoE stages plus layer-4
pre/post state at the same position. See the [numeric dump report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/minimal-paired-control-gdn-dump/README.md)
and [focused layer-4 report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-layer4-163885/README.md).
E6 remains open.

The subsequent layer-3 QSA/MoE and layer-4 pre/post capture found differences
already present after model layer 2. Layer-3 QSA selections and MoE route IDs
matched, while their numerical tensors differed; layer-4 state also differed
before token 23. Independent FP64 replay matched each captured GDN recurrence
output within `8.7e-8` and `8.1e-8`, so this pair does not implicate the
layer-4 recurrence. Earlier paired captures disagree on where the first small
split occurs, and instrumentation can change the trajectory. Do not assign a
stable root cause or alter a backend from this evidence. E6's next gate is
repeatability and accepted-prefix state parity under minimally instrumented
ordinary-path paired runs; return to operator localization only if that gate
produces a reproducible split. See the [layer-3 upstream report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-upstream-layer3-163885/README.md).

The repeated ordinary-path numeric GDN dump gate did not pass. Across two
identically configured 160K pairs with matching output token IDs and the same
residency map, same-backend run-to-run GDN relative L2 was `2.857e-2` for
Strata and `2.692e-2` for NInfer. The cross-backend GDN delta in the second
pair was `3.613e-2`, making that comparison confounded by the measured
run-to-run variation. The first material drift occurred at ordinal 3 for
Strata and ordinal 10 for NInfer. This establishes repeatability failure but
does not identify whether it begins in prompt processing or decode. Next
capture accepted-prefix GDN state at selected decode positions in repeated
pairs with identical minimal capture settings; determine whether the first
generated prefix already contains the drift or whether it accumulates during
decode. Keep exact state parity as the release criterion, and do not change a
backend until the mismatch is reproducible and independently attributed. See
the [numeric repeat report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/minimal-paired-control-gdn-dump-repeat2/README.md).

The capture harness now exposes the runtime's `all` GDN commit mode and its
end-of-prefill state snapshot, with a comparator for the latter. Short
2K-workload smoke pairs validated 36-layer accepted-prefix records and selected
prefill snapshots. The prefill snapshot matched at the selected layer, but the
first material cross-backend commit delta moved from model layer 6 to layer 4
across pairs with different capture settings. A commit-only pair aligned with
the layer-6 capture pair. The baseline 2K result used a different configured
context and is not a valid control. This smoke work validates capture plumbing,
not state parity or a root cause. Next collect all-layer state at early, middle
and final accepted decode positions on the 160K task with one fixed capture
configuration in both arms. Repeat that same configuration before assigning
an onset; preserve ordinary-path checks as the correctness reference. See the
[capture smoke report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-2k/gdn-capture-cli-smoke/README.md).

**E6 three-position accepted-prefix capture (2026-10-28):** one minimally
instrumented paired 160K Q2_0 retrieval captured all 36 GDN layers at accepted
positions 163840, 163862, and 163885. Answer, all 47 token IDs, and residency
matched; final GDN, tail, pooled, pooled-full, and KV fingerprints differed.
At the prompt boundary, layers 0–10 matched bitwise and model layer 12 was the
first material delta (relative L2 `1.169e-4`). At positions 163862 and 163885,
layer 0 matched; layers 1–2 differed only at float32 rounding scale (relative
L2 below `1.84e-9`), then layer 4 showed material deltas (`3.255e-3` and
`2.829e-3`). This is evidence of small numerical differences amplifying
through recurrent layers, not a root-cause attribution: it is one captured
pair, and prior instrumented traces had inconsistent onsets. Repeat the same
capture exactly before attributing the split or changing a backend. Run time
was 3,232.6 s; minimum available memory 6.51 GiB; energy was not measured.
See the [three-position report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-commit-all-3pos/README.md).

**E6 exact three-position repeat and trajectory crossover (2026-10-28):**
the same pair reproduced the first material cross-backend delta at the same
sampled layers and nearly the same magnitude: layer 12 at the prompt boundary,
then layer 4 at accepted positions 163862 and 163885. But whole-capture hashes
revealed a crossover: first-pair Strata is byte-identical to repeat NInfer,
while first-pair NInfer matches repeat Strata bitwise at the prompt boundary.
Their generated states split only later (first material at layer 36 and 21,
respectively). The early delta therefore does not yet follow a backend label;
run/arm variation is at least as significant in this sample. Matching answer,
tokens and residency do not establish state parity. No backend change is
justified. The retrieval harness now has an opt-in
`--reverse-staged-backends` flag to run strict NInfer before Strata, with unit
coverage for both orders. Use it for the next paired capture with all other
settings fixed; compare arm order and backend separately. See the
[repeat/crossover report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-commit-all-3pos-repeat/README.md).

**E6 reversed-order accepted-prefix trial (2026-10-28):** the exact paired
capture was run with NInfer first. Answer, token IDs and residency matched;
final persistent state still differed. Unlike the two Strata-first pairs,
the prompt-boundary GDN state matched bitwise across all 36 layers. At generated
positions, the first material differences were at model layer 8 (relative L2
`3.237e-3`) and layer 5 (`7.424e-4`). This single reversed-order trial is
consistent with arm-order sensitivity but cannot establish it, especially
given the same-order cross-run state crossover. Repeat reversed order before
assigning cause. See the [reversed-order report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-commit-all-3pos-reversed/README.md).

**E6 repeated reversed-order pair (2026-10-28):** a second NInfer-first pair
again matched answer, token IDs and residency but failed final-state parity.
The prompt-boundary capture remained within relative L2 `1e-6`; generated
prefixes instead first showed material cross-backend differences at layer 4
for both positions, rather than layers 8 and 5 in the first reverse-order
pair. Across the two reverse-order runs, same-backend prompt-boundary state
also changed materially at layer 12 (`1.169e-4`), and generated same-backend
onsets varied. This suggests possible order sensitivity for prompt-boundary
alignment but does not establish causality; run-to-run state drift remains a
confounder. Next use a small pre-registered process-initialization/run-order
control matrix before further operator localization. The repeat took 3,231.7 s;
minimum available memory was 6.61 GiB, peak swap 5.24 GiB. See the
[repeat report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-commit-all-3pos-reversed-repeat/README.md).

**E6 third Strata-first pair (2026-10-28):** the third same-order pair again
matched answer, token IDs and residency and failed final persistent-state
parity. However, all-layer GDN state was exact across engines at the prompt
boundary and through all layers at position 163862; at 163885, the first
material delta was only at layer 44 (`6.598e-4`). This does not reproduce the
layer-12 prompt and layer-4 generated split from the first two pairs. Same-
backend comparisons to earlier runs also show material state movement. Run-to-
run GDN variation therefore strongly confounds backend attribution. Keep the
state gate open; next isolate process history with matched single-backend
repeats and a preregistered control matrix before operator localization. Run
time was 3,233.6 s; minimum available memory 6.63 GiB, peak swap 5.05 GiB, and
sampled OOM kills zero. See the [third pair report](../../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-commit-all-3pos-strata-first-repeat2/README.md).

**E6 order-balanced GDN repeats (2026-10-28):** completed three pairs in each
arm order. All six matched answer, generated token IDs, and residency across
engines, while all six failed final persistent-state parity. Prompt-boundary
GDN state was below the `1e-6` relative-L2 threshold across engines in four of
six pairs. Generated-prefix first-material-layer values vary across repeated
runs and overlap across arm orders; same-backend drift is material. This
suggests a possible prompt-boundary order interaction but does not establish
it. Do not attribute the divergence to an engine or modify arithmetic yet.
Next run a small preregistered process-history control matrix with matched
single-backend repeats, then return to localization only if trajectories are
repeatable. See the [order-balanced report](../bench/results/2026-10-27-e6-q2-active-compute-quality-160k/generated-gdn-trace/gdn-commit-all-3pos-order-balanced/README.md).

**E6 same-backend NInfer repeat (2026-10-28):** two fresh strict-NInfer engine
processes ran the identical 160K workload and capture positions. They matched
the expected answer, 47 token IDs, and residency, but differed in final
`gdn`, `tail`, `pooled`, `pooled_full`, and `kv` state. Layerwise GDN relative
L2 first crossed `1e-6` at layer 12 at the prompt boundary (`1.1694e-4`), layer
4 at position 163862 (`3.2549e-3`), and layer 2 at position 163885
(`3.4067e-6`). This establishes material within-NInfer run-to-run drift under
the paired harness and confirms that cross-backend attribution remains
confounded. The run took 3,230.7 s; minimum available memory was 6.96 GiB and
sampled OOM kills were zero. Next repeat Strata/Strata under the same settings
to test whether the drift is specific to NInfer or shared. See the
[NInfer repeat report](../bench/results/2026-10-28-e6-q2-active-compute-quality-160k/same-backend-ninfer-repeat/README.md).

**E6 same-backend Strata repeat (2026-10-28):** two fresh Strata engine
processes ran the same 160K workload and captures. They matched answer, 47
token IDs, and residency, but final `gdn`, `tail`, `pooled`, `pooled_full`,
and `kv` state differed. The captured GDN arrays were bitwise equal at prompt
boundary 163840; at position 163862 the maximum relative L2 was `1.65e-9`;
at position 163885 it first crossed `1e-6` at layer 13 (`5.4927e-4`) and
reached `5.2191e-2` at its largest layer. Minimum available memory was 6.47
GiB, with zero sampled OOM kills. Together with the NInfer/NInfer repeat, this
shows within-backend state drift on both paths; the measured early-prefix drift
is larger in the NInfer sample, but one pair per backend is insufficient to
establish distinct backend profiles or a cause. Next repeat these controls if
causal attribution is needed, or proceed to the task-quality gate without
changing arithmetic. See the [Strata repeat report](../bench/results/2026-10-28-e6-q2-active-compute-quality-160k/same-backend-strata-repeat/README.md).

**E6 same-backend context repeatability screen (2026-10-28):** at both 2K and
16K, fresh-process NInfer/NInfer and Strata/Strata pairs matched answer, 47
token IDs, residency, all nine final state fields, and every captured float in
36-layer GDN snapshots at prompt boundary and two generated positions. Pair
runtimes were about 180 seconds at 2K and 471–477 seconds at 16K; minimum
available memory ranged from 10.98 to 11.79 GiB, with no OOM kills. This
contrasts with the 160K same-backend pairs, where final state and GDN diverged.
It supports a long-context repeatability issue but does not locate a threshold
or establish context length as the only cause; the 16K and 160K configured
capacities differ. Next hold configured capacity fixed and screen 32K, then
advance to 64K if repeatability holds. Repeat near any transition before
operator localization. See the [length screen](../../bench/results/2026-10-28-e6-q2-state-repeatability-length-screen/README.md).

**E6 prompt-length/capacity screen (2026-10-29):** at 32K prompt length,
same-backend NInfer/NInfer and Strata/Strata pairs were exact in final state
and bitwise across all 36 captured GDN layers at 65,536 configured capacity.
At the same prompt length, both backends failed final-state parity at 262,144
capacity. At 16K, both backends likewise repeated exactly at 32,768 capacity
but failed at 262,144. All pairs preserved answer, token IDs, and residency;
the large-capacity failures stayed above the six-GiB memory floor and had no
OOM kills. Capacity is a strong candidate condition, but these are single
pairs per cell and the lower-capacity 16K controls are inherited fixtures;
repeat matched cells before causal attribution. Next repeat the 16K and 32K
capacity cells under identical capture settings, then inspect capacity-linked
allocation, dispatch and initialization if the interaction reproduces. Do not
change backend arithmetic based on this screen. [Report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**E6 replicated 32K/262K capacity cell (2026-10-29):** a second fresh-process
NInfer/NInfer pair and a second Strata/Strata pair again matched answer, token
IDs and residency but failed exact final-state parity. At the prompt boundary,
both backends reproduced the first material sampled GDN delta at layer 22
(relative L2 `1.523e-3`); later accepted positions also diverged. Minimum
available memory was 7.21 GiB (NInfer) and 7.14 GiB (Strata), with no OOM
kills. The capacity-associated failure now repeats across both backends.
Repeat the 16K capacity cells with the same capture configuration, and add a
second matched 32K pair at each capacity before assigning a causal mechanism.
The gate remains exact persistent-state parity; no arithmetic changes are
justified. [Report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**E6 replicated 16K/262K capacity cell (2026-10-29):** second same-backend
pairs reproduced the final-state failure for both NInfer and Strata while
answer, tokens and residency remained equal. At prompt boundary and generated
positions, both backends again first crossed relative-L2 `1e-6` at GDN layers
14, 2 and 2, with relative-L2 values `1.478e-5`, `1.479e-5` and `7.689e-6`.
The maximum sampled layer differences were large (`0.061–0.092`). Minimum
available memory was 7.19 GiB (NInfer) and 7.13 GiB (Strata), with no OOM
kills. The corresponding low-capacity 16K pairs had exact state parity, so
repeat the low-capacity cells under these same capture settings next. The
matching onset across backends is a diagnostic clue only; keep exact state as
the gate and do not change arithmetic. [Report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**E6 matched 16K capacity replication (2026-10-29):** second pairs at
32,768 configured capacity were bitwise exact in final state and all 36 GDN
layers at the prompt boundary and two generated positions for both backends.
Second pairs at 262,144 capacity failed final-state parity on both paths.
These are matched prompt length, workload, engine build and capture settings;
minimum available RAM was 10.96 GiB for the lower-capacity pairs, with no OOM
kills. The repeated 16K capacity contrast makes configured capacity the
leading condition in the current screen. Next add a second 32K/65,536 pair,
then audit capacity-dependent QSA allocation/layout, selection and attention
dispatch that can propagate into later GDN state. Keep the exact state gate;
do not change arithmetic yet. [Report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**E6 routed-expert ownership diagnostic (2026-10-29):** at prompt position
16,383/model layer 2, all routed IDs matched across 32,768 and 262,144
capacity. Expert 130 (route rank 8) changed from PCIe-staged GPU execution at
32,768 to CPU execution at 262,144; the other nine owners were unchanged.
The small expert-part difference first seen at that layer therefore compares
NInfer's staged GPU group with Strata's CPU miss path. Startup logs also show
the pinned expert complement fell from 6.00 GiB at 32,768 to 3.97–4.11 GiB at
262,144, while the GPU expert cache remained 3,000 entries. The 47-token
262,144 capture matched answer, token IDs and residency but failed exact GDN,
tail, pooled, pooled-full and KV state parity across MTP modes; minimum
available RAM was 7.12 GiB and OOM kills were zero. Owner captures isolate a
real tier-assignment change but do not establish why the pinned prefix shrinks
or pass the state gate. On the same captured activation and GGUF weights,
`native_expert_parity`'s CPU output matched the 262,144-capacity runtime CPU
output bitwise, and its CUDA output matched the 32,768-capacity NInfer output
bitwise. CPU/GPU outputs differed in 1,825/2,560 values (relative L2
`1.064e-7`, max absolute `7.45e-9`); the independent parity harness passed.
This isolates the small layer-2 change to execution-tier arithmetic for this
expert, without explaining the later state divergence. Next capture owners in
paired controls at 32K/65,536 and 262,144, inspect earlier layers, and account
for allocations that reduce pinned coverage. Runtime tracing found the
device-0 session allocation grows from 0.92 GiB at 32,768 capacity to 6.56
GiB at 262,144; QSA state and buffers in `session_bytes()` scale with
`max_context`. This is consistent with the lower pinned expert complement on
Orin's shared DRAM, while maintaining the required six-GiB headroom. At the
16K prompt/65,536-capacity intermediate, the session was 1.73 GiB, the pinned
complement remained 6.00 GiB, expert 130 remained PCIe-staged, and a full
MTP-off/MTP-4 pair passed all exact state checks. The pair took 513.6 s and
minimum available RAM was 10.01 GiB. A third NInfer repeat at 32K prompt and
65,536 capacity also passed all state checks; GDN at all three captured
positions was bitwise identical, and layer-2 owners matched across repeats.
The session remained 1.73 GiB, pinned complement 6.00 GiB, and minimum
available RAM 10.07 GiB. The matched 32K-prompt/262,144 capture then showed
expert 152 changing from staged GPU at 65,536 capacity to CPU at 262,144; all
other layer-2 owners and route IDs matched. At 262,144, session allocation was
7.04 GiB, pinned complement 4.11 GiB, minimum available RAM 6.91 GiB, and OOM
kills zero. The MTP-off/MTP-4 pair matched answer, tokens and residency but
failed exact persistent-state parity. The high-capacity MoE bundles for model
layers 0–7 were identical between MTP arms, while GDN first differed at entry
2 at the prompt boundary (`3.49e-10` relative L2); later GDN state diverged.
The independent Q2_0 expert-152 parity run passed; the high-capacity runtime
CPU output matched its CPU oracle exactly, while CPU/GPU parity differed in
1,766/2,560 outputs (`9.72e-8` relative L2). This supports a tier-dependent
expert arithmetic difference but does not explain within-capacity GDN drift.
The matched 32K cross-capacity MoE bundles locate the first numerical change
at model layer 1. Inputs, routes, route weights and shared output are bitwise
identical; only active experts 157 and 152 differ. Their 65,536-capacity
NInfer outputs match independent CUDA parity outputs bitwise, while the
262,144-capacity outputs match independent CPU parity outputs bitwise. The
CPU/GPU oracle deltas exactly reproduce runtime differences for both experts
(1,873/2,560 values and `1.201e-7` relative L2 for expert 157; 1,916/2,560
and `1.123e-7` for expert 152). Layer 2 expert 152 likewise explains every
changed expert-part output there. This attributes the early cross-capacity MoE
drift to the active expert execution tier; subsequent differences accumulate
through later layers. It does not explain the separate within-capacity GDN
state mismatch at 262,144. Next hold the nonresident owner tier fixed by
disabling PCIe staging in paired 32K/65,536 and 32K/262,144 runs. Keep exact
persistent-state validation and do not change arithmetic until that control is
complete. Detailed data: [E6 report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**PCIe-disabled owner-tier control (2026-10-29):** repeated the 32K Q2_0
retrieval fixture at 65,536 and 262,144 configured capacity with `--pcie-frac
0.0`, leaving the 3,000-expert GPU cache unchanged. At each capacity, MTP-off
and MTP-4 returned the exact answer and 47 token IDs with identical residency
and exact persistent state. The resulting state fingerprints also matched
across capacities. Layer-2 routing at position 32,768 had the same ten IDs
and owner assignment in both cells: seven nonresident experts on CPU and
three resident experts on GPU, with no PCIe-staged expert. All captured MoE
fields at layers 0–7 were bitwise identical across capacities. This control
eliminated the prior cross-capacity MoE drift and the 262,144 within-capacity
MTP state mismatch observed with staging enabled. It implicates the staging
and owner-path configuration but does not distinguish numeric CPU/GPU
differences from transfer-time data or other staged-path interactions. Pair
times were 790.9 s and 877.5 s; minimum available RAM was 10.06 and 6.98 GiB
respectively, with no OOM kills. These correctness runs are not performance
measurements; energy was not measured and clocks remained dynamic. Next isolate
the staged-path trigger using same-capacity MoE and accepted-state controls;
do not change arithmetic or recommend the no-staging profile as a performance
improvement without measurement. [Detailed report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**Staged-path numeric localization (2026-10-29):** at 32K prompt / 262,144
capacity, the first MoE bundle difference between `--pcie-frac 1.0` and `0.0`
is confined to expert 86 at model layer 1; routes, route weights, input and
shared output are identical. An independent Q2_0 `native_expert_parity` run on
the exact input showed the staged-config runtime output bitwise equal to CUDA,
and the no-staging runtime output bitwise equal to CPU. Their CPU/GPU delta
exactly equals the runtime difference (1,846/2,560 values, relative L2
`1.0366e-7`). The corresponding prompt-boundary committed GDN state first
differs at layer 1 (260,744/817,152 values, relative L2 `8.8824e-10`). Fresh
no-staging repeats were bitwise exact across all 36 GDN layers, and both MTP
modes at this capacity passed final-state parity when staging was disabled.
This localizes the initial high-capacity state trajectory divergence to the
staged-config active-expert arithmetic path, without claiming that the first
small delta alone explains all later state drift. The exact layer-1 owner
label was not directly captured; the one-token diagnostic did not reach the
selected position. Next repeat the 16K/262,144 state cell with staging
disabled, then run minimally-instrumented same-day performance controls. No
arithmetic changes or performance conclusions until those measurements.
[Detailed report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**16K/262K replication (2026-10-29):** disabling PCIe staging at the 16K
prompt / 262,144 capacity also restored exact MTP-off/MTP-4 final-state
parity, with exact answer, tokens and residency. Staged-versus-no-staging
committed GDN state first diverged at layer 1 at the prompt boundary
(298,674/817,152 values, relative L2 `8.2257e-10`, max absolute
`2.98e-8`), consistent with the 32K finding. Minimum available RAM was
7.36 GiB, zero OOM kills, pair runtime 597.2 s. The staged-path state mismatch
is therefore reproduced as a configuration-dependent effect at two prompt
lengths in the 262,144-capacity cell. Energy and performance were not measured.
Next maintain the exact-state condition while preparing minimally-instrumented
same-day performance pairs, then continue the planned E6 workload/context
matrix. The staged path remains experimental. [Detailed report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**16K no-staging backend parity and pilot timing (2026-10-29):** at 262,144
capacity, a same-day Strata-first pair with PCIe staging disabled passed exact
answer, token, persistent-state and residency checks for both Strata and strict
NInfer. Prompt throughput was 61.0 versus 62.8 tokens/s and decode throughput
4.01 versus 4.12 tokens/s. These are single-run observations from an ordered
diagnostic pair, not performance qualification; TTFT and energy were not
measured. Minimum available RAM was 7.11 GiB and OOM kills were zero. Next
repeat under the minimally instrumented protocol with balanced arm order,
then extend the comparison to other prompt lengths while preserving state and
quality gates. E6 and E7 remain open. [Detailed report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**Order-reversed pilot (2026-10-29):** the NInfer-first 16K/262K no-staging
pair also passed exact output, state and residency checks. NInfer measured
61.1/4.00 prompt/decode tokens/s first, while Strata measured 64.9/4.26
second. The apparent lead switched with arm order, consistent with material
cache/order sensitivity. Do not rank backends from these two pairs. Next add
one more pair in each order, then continue the broader E6 context/workload
screen under the memory reserve. [Detailed report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).
[Report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**Balanced 16K backend screen (2026-10-29):** four ordered pairs, two in each
arm order, passed exact answer, token, persistent-state and residency gates.
The descriptive median paired NInfer/Strata rate differences were +0.67% for
prompt throughput and +1.17% for decode throughput; paired ranges crossed zero
and remained within -6.13% to +2.86% for decode and -5.76% to +2.83% for
prompt. The screen does not meet the initial 5% useful-effect threshold, so
seven-block performance confirmation is not justified for this 16K/262K
no-staging cell. Minimum available RAM ranged from 7.10 to 7.31 GiB, with no
OOM kills. This is not product-performance qualification; TTFT and energy were
not measured. Next extend screened correctness/performance observations across
other prompt lengths and workload shapes, keeping failed and unsupported cells
explicit. [Detailed report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**64K no-staging pilot (2026-10-29):** one Strata-first Q2_0 retrieval pair
at 131,072 configured capacity passed exact answer, token, residency and
persistent-state gates. Strata/NInfer prompt rates were 102.65/102.52 tokens/s
and decode rates were 4.55/4.68 tokens/s; the paired differences (-0.13% and
+2.76%) did not reach the 5% screen threshold. This is not a performance
qualification. Minimum available RAM was 8.19 GiB, peak swap 5.34 GiB and OOM
kills zero. The test exercised a 65,536-token prompt, not near-limit 131K
ingestion. Continue with matched screens for other planned pp/tg shapes and
context cells; E6/E7 remain open. [Detailed report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**32K no-staging backend screen (2026-10-29):** three 32,768-token Q2_0
retrieval pairs at 262,144 capacity passed exact answer, token, residency and
persistent-state checks. The median paired NInfer/Strata rate differences
were +0.57% prompt and +0.01% decode; ranges were -0.07% to +7.90% prompt
and -0.46% to +2.76% decode. The +7.90% prompt result occurred only in the
first pair and did not repeat. This cell also misses the initial 5% threshold
and does not proceed to confirmation. Minimum available RAM ranged from 6.97
to 7.08 GiB, with no OOM kills. TTFT and energy were not measured; clocks
remained dynamic. Continue the E6 screen across additional prompt sizes and
the planned pp/tg shapes, preserving quality, state and memory gates. [Detailed
report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**128K no-staging pilot (2026-10-29):** one Strata-first Q2_0 retrieval pair
at 262,144 configured capacity passed exact answer, token, residency and
persistent-state checks. Strata/NInfer prompt rates were 105.38/103.19 tokens/s
and decode rates 3.93/3.83 tokens/s; NInfer was slower by 2.07% and 2.51%.
This is below the 5% threshold and does not warrant performance confirmation.
Minimum available RAM was 6.50 GiB, peak swap 1.43 GiB and OOM kills zero; the
pair ran 2,659.3 s. TTFT and energy were not measured; clocks remained dynamic.
This completes 128K prompt ingestion under 256K capacity, not near-limit 256K.
Continue with planned pp/tg workload shapes and other context cells; E6/E7
remain open. [Detailed report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**pp2048+tg128 no-staging screen (2026-10-29):** one paired Q2_0 synthetic
long-form request at 4,096 configured capacity passed exact generated-token,
all-nine persistent-state and residency checks with PCIe staging disabled.
Strata/NInfer prompt throughput was 44.47/44.55 tokens/s and decode throughput
5.35/5.35 tokens/s; the approximate NInfer gains (+0.18% prompt, +0.12% decode)
are below the 5% screen threshold. Minimum available RAM was 11.58 GiB and OOM
kills were zero. This one-pair instrumented diagnostic has no expected answer,
so it establishes token/state repeatability but not semantic task quality; TTFT
and energy were not measured. E6/E7 remain open. See the [detailed report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**pp512+tg64 no-staging screen (2026-10-29):** one paired synthetic Q2_0
request at 1,024 configured capacity passed exact generated-token, all-nine
persistent-state and residency checks with PCIe staging disabled. Strata/NInfer
prompt throughput was 22.0/21.7 tokens/s and decode throughput 5.1/5.1
tokens/s; approximate NInfer changes (-1.43% prompt, +0.47% decode) are below
the 5% screen threshold. Minimum available RAM was 11.70 GiB, with zero OOM
kills. This one-pair instrumented diagnostic lacks an expected answer, so it
does not establish semantic task quality; TTFT and energy were not measured.
E6/E7 remain open. See the [detailed report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**Three-block pp512+tg64 no-staging screen (2026-10-29):** all three paired
fresh-process runs passed exact generated-token, nine-field persistent-state,
and residency checks at 1,024 capacity; one block used NInfer-first order.
Median paired NInfer/Strata throughput changes were +0.22% prompt and +0.47%
decode, with ranges -1.42% to +1.30% and -0.10% to +1.74%. This does not
reach the 5% useful-effect threshold, so confirmation is not justified for this
cell. Minimum available RAM was 11.70–11.76 GiB, OOM kills zero. Semantic answer
quality, TTFT and energy were not measured. See the [screen report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**Three-block pp2048+tg128 no-staging screen (2026-10-29):** all three paired
fresh-process runs passed exact generated-token, nine-field persistent-state,
and residency checks at 4,096 capacity; block 2 ran NInfer first. Median paired
NInfer/Strata changes were +0.18% prompt and +0.13% decode throughput. Prompt
pair differences ranged -0.11% to +1.82%; decode ranged -19.65% to +0.72%, with
the isolated -19.65% result not repeating. The medians do not meet the 5%
threshold, so confirmation is not justified for this cell. Minimum available
RAM was 11.58–11.64 GiB and OOM kills zero. The synthetic workload has no
expected answer; TTFT and energy were not measured; clocks remained dynamic.
See the [screen report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md).

**Exact 256K retrieval/state check (2026-10-29):** one fresh-process
Strata/strict-NInfer pair passed a held-out 256,000-token retrieval/arithmetic
task at 262,144 configured context with PCIe staging disabled. Both returned
the expected three markers and sum; all 47 generated token IDs, nine final
state fingerprints and residency hash matched. The supervisor recorded 7.04
GB (6.56 GiB) minimum available memory, 0.56 GiB above the six-GiB floor;
peak sampled swap was 6.32 GiB and sampled cgroup pressure/OOM counters stayed
at zero. Prompt rates were 99.68/99.78 tok/s and decode rates 3.88/3.96 tok/s
(Strata/NInfer), differences of +0.10%/+1.98% for NInfer in this single pair.
The approximately 89-minute run establishes one functional near-limit cell,
not a performance advantage, broad quality or sustained-service qualification.
Final-state fingerprints matched, but accepted-prefix state was not captured.
Energy was not measured and clocks remained dynamic. E6/E7 remain open. See
the [report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/quality-retrieval-256k-README.md).

**No-trace 16K API screen (2026-10-29):** three fresh-process Strata/strict-
NInfer pairs completed a 16,384-token prompt and 128-token generation at
32,768 capacity, with PCIe staging/cache and tracing disabled. All six
processes passed and matched warmup/measured content within pairs. Median
paired changes were -0.12% prompt TPS, 0.00% decode TPS, +0.19% TTFT and +0.18%
client total; all bootstrap intervals included zero and no effect met the 5%
screen threshold. Each randomized block happened to run NInfer first, leaving
order as a limitation. The generic workload had no semantic oracle or state
capture. Minimum available memory was 10.78 GiB and sampled cgroup
pressure/OOM counters stayed zero. No confirmation is warranted. E6/E7 remain
open. See the [screen report and chart](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-pp16384-cap32768-README.md).

**No-trace 32K API screen (2026-10-29):** three fresh-process Strata/strict-
NInfer pairs completed a 32,768-token prompt and 128-token generation at
65,536 capacity, with PCIe staging/cache and tracing disabled. All six
processes passed and matched warmup/measured content within pairs. Pair order
was mixed (one NInfer-first, two Strata-first). Median paired changes were
+0.12% prompt TPS, -1.12% decode TPS, -0.07% TTFT and +0.01% client total; all
paired bootstrap intervals included zero and effects were below the 5% screen
threshold. Minimum available memory was 9.95 GiB and sampled cgroup
pressure/OOM counters stayed zero. The generic workload had no semantic oracle
or state capture. No confirmation is indicated; E6/E7 remain open. See the
[screen report and chart](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-pp32768-cap65536-README.md).

**No-trace 64K API screen (2026-10-29):** three fresh-process Strata/strict-
NInfer pairs measured a 65,536-token formatted prompt plus 128 generated
tokens at 131,072 configured context, with PCIe staging, prompt cache and
tracing disabled. All six processes and measured requests passed; warmup
content matched byte-for-byte within each pair, but measured output text differed
in all three pairs. The benchmark sets temperature 0 (greedy); five of six
same-process warmup-to-measured responses also differed, so this reveals an
unresolved repeatability/state issue rather than sampling noise. Median paired
NInfer changes were -0.20% prompt TPS, +3.16%
decode TPS, +0.25% first-visible TTFT and +0.86% client total; every paired
bootstrap interval included zero. A single NInfer decode outlier widened its
interval to -56.63%..+21.58%. Minimum available RAM was 7.12 GiB, peak sampled
swap 6.33 GiB, cgroup pressure/OOM counters zero. This is not
quality-equivalent evidence; decode and client-total effects are confounded by
the changed generated text paths. It does not meet the 5% screen, so no
confirmation is indicated. Next capture accepted-prefix state over repeated
same-request runs under minimal instrumentation before using generated-token
timings as a kernel comparison. The campaign driver stopped before block 2; the persisted third
pair completed under the same settings and planned order through direct
supervisor calls, then the manifest was reconciled from terminal records.
The generic workload has no semantic oracle or state capture; energy was not
measured and clocks remained dynamic. E6/E7 remain open. See the [64K report
and combined figure](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-pp65536-cap131072-README.md).

**Accepted-prefix instrumentation follow-up (2026-10-29):** a paired 65K
prompt/128-token warmup with a 32-token measured continuation captured accepted
prefixes under `STRATA_TRACE`, accepted-prefix tracing and state hashing. All
32 token IDs and all ten state fingerprints matched across Strata and NInfer.
This heavy trace did not reproduce the no-trace divergence: the original
block-0 no-trace measured outputs differed after 52 common characters, while
the traced outputs matched for 32 tokens. Within NInfer, the first measured
token ID stayed the same after changing warmup history, but GDN, pooled,
pooled-full and KV fingerprints changed. The changed warmup also changes prompt
length, so it does not isolate a cause. The trace takes about 76 minutes per
arm and perturbs execution; its rates are excluded. Next use buffered or sampled
state checkpoints, first checking that instrumentation preserves the no-trace
output path. E6/E7 remain open. See the [accepted-prefix diagnostic](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/accepted-prefix-instrumentation-README.md).

**Minimally instrumented pp512+tg64 API screen (2026-10-29):** three
randomized fresh-process pairs at 1,024 context used a warmup and measured
request per process, with PCIe staging, prompt cache and tracing disabled. All
six requests passed and measured content matched within each pair. Median
NInfer/Strata changes were -0.97% prompt TPS, +1.16% decode TPS, +0.88%
first-visible TTFT, and +0.84% client time; all 95% paired bootstrap intervals
crossed zero. No median met the 5% screen threshold; no confirmation is
indicated. Minimum available RAM was 11.66–11.70 GiB, OOM kills zero. State was
not captured, and content equality is not an independent task-quality oracle.
Energy was not measured and clocks remained dynamic. See the [API screen report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-pp512-cap1024-README.md).

**Minimally instrumented pp2048+tg128 API screen (2026-10-29):** three
randomized fresh-process pairs at 4,096 context used a warmup and measured
request per process, with PCIe staging, prompt cache and tracing disabled. All
six requests passed and content matched within each pair. Median NInfer changes
were +4.48% prompt TPS, +0.00% decode TPS, -4.39% first-visible TTFT, and
-2.34% client time; the corresponding 95% paired-bootstrap intervals were
+0.62% to +6.11%, -4.30% to +47.62%, -6.13% to -0.53%, and -14.10% to -0.39%.
The large decode result was isolated to one unusually slow Strata baseline. The
TTFT median remains below 5%; decode is tied, so confirmation is not indicated.
Minimum available RAM was 11.58–11.63 GiB, OOM kills zero. State was not
captured; content equality does not establish task quality. Energy was not
measured and clocks remained dynamic. See the [API screen report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-pp2048-cap4096-README.md).

**Held-out 2K retrieval/state check (2026-10-29):** the exact-length
2,048-token fixture at 4,096 capacity passed with PCIe staging disabled in both
Strata and strict NInfer. Both returned the expected three retrieval codes and
numeric suffix sum; all 47 generated IDs, all nine persistent-state fields,
and residency hashes matched. Minimum available RAM was 11.76 GiB, OOM kills
zero. This is one synthetic task, not broad quality qualification. Rates from
the instrumented run are diagnostic only. See the [functional report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/quality-retrieval-2k-README.md).

The 1K `pp512+tg64`, 4K `pp2048+tg128`, 16K, 32K and 64K no-trace API screens
are included in a combined paired-effect figure with all three blocks and
bootstrap intervals. The chart does not satisfy E6's full context/workload
exit. See the
[figure and sanitized source data](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/README.md#combined-no-trace-api-paired-effect-chart).
