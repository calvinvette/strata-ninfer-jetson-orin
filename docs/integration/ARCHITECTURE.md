# Integration architecture

Status: intended architecture; interfaces below are design contracts, not claims
about implemented features. See [decisions](DECISIONS.md) for the chosen scope.

## Product boundary

The initial product remains one Jetson AGX Orin 32 GB, Linux ARM64, JetPack 6.2 /
CUDA 12.6, SM87, one active model and one active generation request. Preserve
Strata's OpenAI/Anthropic serving behavior and file-backed Flash-Next expert path.
Use the verified Coder IQ1_M pack first. Coder, Qwen3.8-27B and Qwen3.6-35B-A3B
are different models; similar names do not make their layers or artifacts compatible.

NInfer supplies implementation references and contracts. Its resident-model,
groupwise-int `.ninfer` target is not substituted for Strata's GGUF/native packs.
A new target or converter needs a separate tensor inventory, layout/quantization
specification, tokenizer/template identity, memory estimate and correctness gate.
NInfer's v3 artifact rejection by its v1/v2 reader is a concrete reason to reject
unknown formats early. Do not route by extension alone or silently reinterpret data.

## Ownership to establish in Strata

| Boundary | Owns | Existing or reference location |
| --- | --- | --- |
| Protocol adapter | HTTP/CLI transport, request parsing, streaming schemas, acquisition of media | Strata `serve/`; NInfer `src/serve/`, `src/product/` |
| Model frontend | Tokenizer/template, prepared prompt identity, multimodal preprocessing, stop/output semantics | Existing Strata frontend; NInfer family `impl/frontend/` |
| Request controller | Admission, lifecycle, cancellation, scheduling, and publishing committed output | Strata current controller; NInfer `src/runtime/engine/` |
| Target execution | Exact weights and dimensions, KV/recurrent state, provisional speculation, prefill/decode schedule and graph lifetime | Strata `src/core/`, `src/prefill/`; NInfer family `impl/runtime/` |
| Physical resources | Unique allocations, reservations, expert residency, transfers and transition peaks | Strata `expert_cache`, `expert_source`, `DeviceArena`, shared-memory budget; NInfer resource-plan references |
| Operators | Closed mathematical or state-transition contract and hardware-specific implementation | Strata `src/kernels/`; NInfer `include/ninfer/ops/`, `src/ops/` |

Apply these boundaries incrementally at an actual change. Do not create a second
mutable memory ledger or scheduler alongside the existing owner. A controller may
read a stable resource summary; only the physical owner mutates allocation facts.
Keep exact-model facts outside shared request scheduling. Avoid building a generic
model plugin framework to transfer one useful operator.

## One physical budget with several resource constraints

CPU and GPU consume the same LPDDR. Host and device APIs describe access and
lifetime, not independent capacities. At startup, allocation and transition:

1. Sample OS/cgroup availability and CUDA allocation limits. Use the most limiting
   applicable value; never sum host capacity and CUDA capacity.
2. Count each unique allocation once, including real duplicate host/device copies.
   Track future reservations separately and retire a reservation when materialized.
3. Account for weights, expert cache, host complement, pinned staging, KV, recurrent
   and speculative state, prompt/vision workspaces, graph pools and transfer peaks.
4. Preserve physical host headroom and bounded late-workspace reserve. Initial
   Strata policy retains 6 GiB plus its separate 3 GiB auto-cache workspace reserve.
   NInfer's historical 1.2 GiB abort floor is not the new product's headroom default.
5. Check transition peaks as well as final occupancy. Recheck current availability
   before committing a plan; external processes can invalidate a prior snapshot.

Physical RAM availability does not prove a specific KV extent, graph pool or cache
slot is allocatable. Retain allocator geometry and typed capacity constraints.
File-backed expert cache misses also consume disk bandwidth and page-cache space.
Measure logical expert bytes separately from physical storage reads.

Explicit `cudaMalloc` remains the control. Experiment with async pools, pinned
staging, mapped reads or managed sequential ownership by buffer class. Orin's
measured `concurrentManagedAccess=0` makes a global managed-memory substitution
invalid. ARM publication barriers, CUDA completion ordering and CPU/GPU ownership
must be specified and tested for every shared buffer.

## Numerical and state contracts

Each transferred operator needs represented input/output types, dimensions,
packed-format decode, rounding/cast boundaries, an independent FP32/FP64 oracle
(or exact codec oracle), accepted errors and dispatch boundaries. NInfer Q4/Q5
groupwise weights are not Strata IQ1_M/Q2_0/K-quant blocks. Transfer scheduling
ideas first unless the storage and operation contracts match exactly.

For speculative execution, maintain committed state separately from provisional
verification state. The accepted prefix must commit KV, recurrent/conv state,
token history, sampler state and output consistently before publishing a token.
Cancellation and failure reach one terminal state and release owned resources.
Tests must cover accepted lengths 0, 1, an intermediate value and the full window,
rejected suffix mutation, repeated rounds and recovery.

ReplaySSM is a candidate only if the target's actual recurrence can satisfy the
contract. Preserve raw represented inputs and verify-produced gate bits; fold
only the accepted prefix. A claim of bitwise state reconstruction requires exact
persistent-state comparisons against the same sequential arithmetic path. A
tolerance-based oracle pass is a different claim. Plausible final text proves neither.

Graph capture/replay requires stable buffer addresses, valid ownership through
completion, explicit capture boundaries and qualified resizing/recapture. Pair
graph and eager runs; test cancellation, reuse and cache resize before admission.

## Hardware dispatch

Keep portable/ARM CPU and CUDA/HIP/SYCL boundaries explicit. SM87-specific kernels
sit behind capability checks with a qualified fallback. ARM spin hints do not
replace atomic ordering. NEON work must preserve activation-quantization contracts.

For CUDA, inspect SM count, shared memory, registers, occupancy and cooperative
grid residency on the actual device. Do not inherit desktop residency floors or
Blackwell-only FP8/FP4 instructions. CUDA 12.6 codec support does not imply native
FP4 tensor-core execution. Inspect compiled targets for SM87 rather than relying
on the build host architecture.

NInfer's R64C128S2 attention projection is a candidate schedule, not a universal
Orin tile. Its 48 KiB staging constraint is specific to that route; use queried
device/function limits and occupancy for each new route. Retain small-token paths
and test dispatch boundaries around the reference T=21 threshold if reused.

## Integration mechanics

Keep `reference/ninfer` unchanged as a comparison source. Promote a narrow set of
files into normal Strata source/test ownership only with a documented contract,
adaptation notice, build flag, oracle and actual-model shape tests. Do not include
the entire NInfer CMake project from Strata or start a second inference service to
serve one request. Retain imported Apache notices on derived files.

Each promoted change is opt-in until qualified. The disabled path must preserve
the established default behavior; compare exact generated artifacts/outputs where
deterministic and applicable, and directly test numerical/state contracts. Claims
about desktop byte identity require desktop execution evidence. HIP/SYCL builds
on maestro1 check source portability, not Orin performance or GPU runtime.
