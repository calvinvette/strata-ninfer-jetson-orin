# NInfer expert execution inside Strata

Status: **in progress; E1–E4 have bounded Q2_0 evidence; E4 model coverage is partial as of 2026-10-25**.
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
[current 8K log](../../bench/results/2026-10-25-flashnext-context-capacity-sweep/campaign/coder-iq1m/8192/run/engine.log),
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
have bounded Q2_0 prototype evidence. E4 explicitly leaves the mixed-codec
Coder IQ1_M and ISTA-DASLab IQ3_S models unsupported by
the NInfer selector; E5–E7 remain pending. E2's resident schedule and E3's staged-miss schedule both failed the
initial performance screens. The default remains Strata and the NInfer path
remains experimental. Each stage produces a small source/evidence change and
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

### E4 — Add prefill, small-token execution and model coverage

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
Only the Q2_0/Q2_0 artifact is covered, and it is not performance-qualified.
64/128-token throughput, mixed-codec support and HIP/SYCL qualification remain
open; E4's broad model-coverage objective is therefore only partially complete.

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

### E7 — Release the demonstrated integration

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
