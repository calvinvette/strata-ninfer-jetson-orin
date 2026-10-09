# Multi-phase development plan

Target: apply NInfer's proven design and SM87 lessons to Strata's Flash-Next Orin
runtime while preserving correctness, shared-RAM limits and service behavior.
This is a staged research and implementation plan, not a claim of combined speed.
Only Phase 0 is complete at initialization. Use the [status](STATUS.md) and
[experiment template](templates/experiment.md) to record passes, failures,
unsupported cases and deferred work separately.

## Phase 0 — Preserve the starting points (complete)

- Create the new checkout and remote with Strata history at `0be090c`.
- Pin NInfer at `b07248f2`; copy source, headers, tests, tools, docs, fixtures and
  dependency notices into `reference/ninfer`. Keep it outside the active build.
- Copy selected local raw reports and the dirty plan separately with SHA256,
  origin labels and a retained diff. Do not commit changes in either input port.
- Establish [architecture](ARCHITECTURE.md), [source map](IMPORT_MAP.md),
  [measurement protocol](BENCHMARKS.md), campaign specification and CPU-only checks.
- Exit: remote published, manifest verifies, matrix specifications validate,
  licenses retained, and input working trees unchanged by this bootstrap.

## Phase 1 — Reconstruct controls and instrument the actual workload

Dependencies: Phase 0.

- Build the pinned Strata control and a new-branch control with native ARM64,
  Release CUDA 12.6 and SM87. Preserve binary identity, build options and artifact
  identities. Inspect flags and embedded architecture before running.
- Reuse existing verified Coder IQ1_M/MTP packs by explicit path. Reproduce
  `pp512+tg64` and `pp2048+tg128` as new common workload shapes, then the historical
  172/557/1069-prompt cases. Record actual token counts after formatting.
- If rebuilding the reference NInfer engine, use its separate CMake root and local
  FFmpeg/curl prefix from its Jetson guide. Resolve omitted ranking fixtures only
  if a chosen test uses them. Run its own 27B and pinned v2 35B artifact controls
  as separate model cohorts; do not divide these throughputs by Strata's.
- Collect tegrastats, OS/cgroup memory, swap, disk, cache, workspace, graph and MTP
  counters alongside request times. Record power mode and CPU/GPU/EMC clocks;
  use a shared fixed profile when available, otherwise label dynamic-clock runs.
- Establish independent oracle tolerances for target operations and capture the
  known raw-token logit discrepancy rather than silently adopting it as a pass.
- Exit: same-day repeated controls with raw samples; capability manifest; explicit
  model/template/quantization inventory; setup/core/API baseline passes with skips
  counted separately. No active optimization before the control is reproducible.

## Phase 2 — Define operators and state ownership at integration seams

Dependencies: Phase 1; required before changing execution or formats.

- Map target tensors, quantization blocks and activation contracts to the NInfer
  operator schemas. Record reuse/adapt/incompatible decisions by symbol and shape.
- Identify one authoritative owner for request lifecycle, physical allocations,
  KV/recurrent state and graph lifetime in the existing Strata code. Introduce
  narrow adapters at these boundaries without duplicating scheduling state.
- Add independent oracle fixtures for the first selected operator and exact tests
  for packing/layout transforms. Cover real layer/expert shapes and dispatch edges.
- Reuse NInfer's state/admission/cancellation scenarios in Strata tests where their
  semantics apply; preserve existing OpenAI/Anthropic API contracts.
- Exit: contract and ownership review recorded; incompatible formats fail clearly;
  unchanged default route passes regression checks; chosen numerical tolerance is
  justified before inspecting candidate performance.

## Phase 3 — Admission, memory ownership and transfer experiments

Dependencies: Phase 2; kernel work in Phase 4 may follow independently once its
own contracts are complete.

- Extend Strata's existing shared-memory accounting with NInfer-style unique
  allocation and future reservation semantics, where current accounting lacks them.
  Include transient materialization, MTP, vision and CUDA Graph peaks.
- Test late-workspace pressure, cgroup limits, failed registration, VMM resizing,
  pageable fallback, cancellation cleanup and short recovery after long requests.
- Sweep expert-cache cap × context reservation, then prefill chunk × workspace
  peak. Record actual allocated bytes as well as requested fractions.
- Compare explicit device/pinned copy, bounded mapped reads, async pools and managed
  sequential ownership for specific buffers only. Preserve six GiB headroom for
  ordinary campaigns; require a recorded decision for a lower capacity-probe floor.
- Exit: oracle/checksum and ownership tests pass; no invalid access or headroom
  breach in admitted runs; measured tradeoff includes RAM, copies, faults, disk,
  allocation/transfer latency and end-to-end effect. Reject candidates with only
  a microbenchmark advantage and no relevant product benefit.

## Phase 4 — SM87 kernels and ARM64 CPU contribution

Dependencies: Phases 1–2, plus Phase 3 for any changed allocation lifetime.

- Profile the current end-to-end critical path first: CPU quant/dot/router,
  expert misses and transfer, attention projection, GDN projection/state, MoE and
  launch overhead. Select a measured bottleneck, not the most interesting kernel.
- Port the mathematical operator and packed-data contract before schedule tuning.
  Start with the NInfer Q4/Q5 projection design only where formats match or an
  explicit conversion is independently qualified; account for conversion cost.
- Constrained sweep: row tile {16,32,64}, column tile {64,128}, pipeline stages
  {2,3,4}, eligible token shapes and qualified load/scale variants. Prune by
  shared memory, registers and occupancy before timing. Cooperative launches
  require a valid full-grid residency bound and fallback on this SM count.
- For ARM work, compare scalar/ggml/NEON and workers {1,2,4,8} without changing
  Q8_0 versus Q8_1 rounding contracts. Measure CPU/GPU contention for shared EMC.
- Record numerical error, median/p95 latency, registers, shared memory, spills,
  occupancy and bandwidth. Keep rejected candidates in the ledger, not in default
  dispatch. NInfer's smaller tiles and `ca` loads often lost; do not repeat them
  without a shape, format or hardware reason.
- Exit: real-shape oracle and dispatch tests pass; end-to-end confirmation on
  held-out prompts and contexts; unchanged/default route and all affected backend
  builds pass. A local tile win alone does not change a default.

## Phase 5 — Speculation, state transactions and graph lifetime

Dependencies: Phase 2 and qualified memory/operator paths.

- Establish MTP off/2/3/4 × short/long workload × supported KV format controls.
  Include draft cost, verification cost, accepted/drafted counts, fallback count
  and emitted tokens per round. The best window is workload dependent.
- Adapt NInfer's accepted-prefix state transaction tests to Strata. Check commit
  lengths 0/1/intermediate/all; rejected suffix isolation; long chains; conv/GDN
  state, KV, token history and output publication; cancellation then recovery.
- Evaluate raw-record ReplaySSM only after confirming Flash-Next recurrence and
  precision compatibility. Compare saved snapshot capacity against replay work.
  Directly test state bits for exact reconstruction claims.
- Compare eager versus graph decode with stable addresses, warmed capture,
  bounded pool size and resizing/recapture tests. Remove unused reservations only
  when the corresponding feature is explicitly disabled.
- Exit: committed-state and API tests pass; long-chain drift bounded by the stated
  contract; graph and MTP improvements measured independently and together. DFlash
  remains a separately proposed target-specific feature, never an MTP substitute.

## Phase 6 — Parametric and multivariate optimization

Dependencies: qualified candidates from Phases 3–5. Use [BENCHMARKS.md](BENCHMARKS.md)
and [`campaign.json`](../../bench/integration/campaign.json).

- Screen a manageable grid, then test the interactions supported by the data:
  MTP × workload/KV; context × expert-cache; prefill chunk × cache/workspace;
  workers × transfer policy; graph × speculation. Do not run the Cartesian
  product of every factor or infer interactions from one-factor sweeps.
- Randomize within clock/thermal/artifact blocks and pair same-day baseline and
  candidate runs. Use three screening repetitions and at least seven independent
  confirmation repetitions; use held-out prompts for confirmation.
- Fit response models with stated transformations and interaction terms only
  when design rank and residuals support them. Use bootstrap intervals for paired
  deltas; do not treat successive tokens in one request as independent replicates.
- Optimize a Pareto set: TTFT, decode throughput, tail latency, physical headroom,
  energy/token, quality and disk traffic. Let users select a documented profile;
  do not hide a large latency/memory tradeoff in a single score.
- Exit: reproducible median-based tables/plots, uncertainty, per-cell sample counts,
  infeasible/failed cells, ablations and held-out confirmations. Promote a default
  only for the configuration domain shown to improve within its quality budget.

## Phase 7 — Capacity, quality and sustained service qualification

Dependencies: Phase 6's selected configurations.

- First reproduce 8K/16K/32K request capacity under telemetry. Expand Strata's
  historical 1K–256K reservation ladder only after each prior point and recovery
  pass. Distinguish configured capacity, actual prompt length and generated length.
- Test near-limit ingestion, multi-position retrieval/recall, causal scoring or
  another justified quality task, and post-request recovery separately. A reply
  of `OK` is an ingestion check, not long-context numerical/recall validation.
- Run repeated API/streaming, cancellation during prefill/decode, vision (bounded
  small fixture first), cache reuse and teardown. Only evaluate concurrency 2/4
  if admission and per-request state isolation are implemented and memory-feasible.
- Reach thermal equilibrium and run at least 30 minutes for the selected serving
  profile; log throttling, clocks, power and latency drift. Preserve failed and
  pressure-aborted runs. Do not report them as supported capacity.
- Exit: a bounded support matrix with actual memory floor, quality criterion,
  recovery and sustained performance evidence. Explicitly list exclusions.

## Phase 8 — Integration release and upstreamable changes

Dependencies: all gates relevant to the selected features.

- Split architecture, accounting and kernel changes into reviewable opt-in units.
  Search related upstream issues/PRs before opening another. Keep portability PR
  #1621 focused; this new repository owns the integration research.
- Run native CUDA/ARM runtime tests; rebuild HIP and SYCL for every shared file
  they touch using the maestro1 toolchain records. Report build/help checks and
  GPU/model execution separately; run desktop regression hardware when available.
- Publish commands, revisions, model checksums, supported profiles, raw summaries,
  median graphs, limitations and reproduction steps. Preserve license notices on
  copied/adapted source and identify the parent file/revision.
- Exit: documented supported configuration, review-ready evidence, default-path
  regression results and a rollback path to the pinned control.

## Deferred work

New models/artifact formats, multi-GPU, large-scale/preemptive serving and JetPack
or CUDA upgrades each need an explicit architecture/capability decision. The copied
local NInfer follow-on note is a proposal, not evidence that an upgrade supports
this board. Verify vendor support before scheduling it. If undertaken, compare
toolchains at identical clocks first, then a separate clock-profile experiment.

Phases 1 and 2 are closed with their capability matrices, contracts and
exclusions recorded. Continue with Phase 3's unique-allocation ownership and
transfer experiments before promoting any execution path. Do not change kernels,
quantization, model, toolchain and clocks simultaneously; select each candidate
from measured bottlenecks and qualify its contract first.
