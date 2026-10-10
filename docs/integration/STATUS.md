# Integration status

Updated: 2026-10-09. Phases 1 and 2 are complete with their supported, failed,
unsupported and untested scopes recorded. Phase 3 memory ownership and transfer
work is next. No NInfer execution component has been promoted into Strata.

| Phase | State | Evidence / next gate |
| --- | --- | --- |
| 0 — Repository and import | Complete | Pinned source/evidence manifest, source mapping, plan, offline planner checks |
| 1 — Same-day controls | Complete | Four same-day paired API blocks; exact workloads/artifacts; protocol and baseline checks; capability matrix records limits; expanded HIP/SYCL builds compile |
| 2 — Operator/state contracts | Complete | Ownership review, incompatible projection-profile rejection, independent RMS/IQ4_NL/Q6_K oracles, GDN prefix checks, default spec1 regression and post-fix spec1/spec4 token plus nine-field persistent-state parity recorded; native/HIP/SYCL build evidence and eleven selector tests pass; no NInfer execution component promoted |
| 3 — Memory and transfers | In progress | Opt-in trace covers ordinary ExpertCache, primary SessionState, verifier, prefill, MTP and separate pageable/pinned expert-stage host owners; two randomized fixed-cache 4K staging screens matched tokens and nine state fields; the trace-corrected clocked repeat found +0.10% median prompt time and variable decode results with dynamic CPU/GPU clocks; minimum availability was 8.04 GiB; VMM/segmented cache, unique backing, pressure and other transfer experiments remain |
| 4 — SM87/ARM kernels | Not started | Pinned request profile prepared; bottleneck attribution, qualified candidate and request confirmation pending |
| 5 — Speculation and graphs | Not started | Accepted-prefix state, graph lifetime and drift qualification |
| 6 — Multivariate tuning | Not started | Randomized paired campaign, interactions, uncertainty, held-out confirmation |
| 7 — Capacity and service | Not started | Quality, recovery, thermal equilibrium and sustained workload |
| 8 — Release/upstream | Not started | Relevant backend builds, runtime matrix and reviewable changes |

The [GDN prefix kernel check](../../bench/results/2026-10-09-gdn-prefix-kernel/README.md)
adds direct recurrence and convolution-history prefix evidence in Phase 2. The
model-level accepted-prefix check below now supplies the separate verifier and
publication-boundary state evidence for the observed output-clipping case.

The [runtime ownership review](OWNERSHIP_REVIEW.md) records existing owners for
API ordering, engine execution, session state, verifier commits and device
allocations. It adds no duplicate scheduler or allocation ledger. Unique physical
backing and reservation semantics remain Phase 3 work.

The [pinned-stage transfer screens](../../bench/results/2026-10-09-stage-pin-transfer-fixed/README.md)
tested pageable versus pinned file-tier staging on the local Orin under the six
GiB floor. The selected staged path is opt-in and remains pageable by default.
Both three-pair fixed-cache screens matched output and persistent state. The
initial screen showed slower pinned medians; the trace-corrected clocked repeat
showed a small prompt regression and variable decode results, so it does not
establish a product benefit. Host staging is reported separately from device
allocations. The [clocked repeat](../../bench/results/2026-10-09-stage-pin-transfer-clocked/README.md)
records dynamic CPU/GPU frequencies and unsupported EMC sampling. These
screens do not close Phase 3's broader pressure, unique-backing or transfer gates.

Phase 3 has begun with opt-in reservation reporting at auto-cache sizing. The
parser keeps planned cache holds outside allocation totals; the supervised
[Orin observation](../../bench/results/2026-10-09-phase3-reservation-observations/README.md)
records VRAM slack and MTP binding while preserving the six GiB floor. This is
not complete physical ownership accounting. Its 8-token arm also exposed an
unresolved `pooled_full` accepted-prefix mismatch, preserved in the [short-prefix
follow-up](../../bench/results/2026-10-09-short-prefix-state-followup/README.md)
for Phase 5 investigation.

The [accepted-prefix publication check](../../bench/results/2026-10-09-accepted-prefix-publication/README.md)
found identical 32-token output but differing persistent state between spec 1
and spec 4 when the final verifier window exceeded the output budget. Service,
CLI and pipeline use one shared selector for the published prefix; its eleven
host cases pass. A supervised local Orin rerun now passes: spec 1 and spec 4
emit identical 32 token IDs and match all nine recorded state fields, with 23
of 27 drafts accepted. The six GiB physical-memory floor was maintained (minimum
available 8.57 GiB). This closes only the observed final-output-clipping case;
other prefix lengths, EOS, cancellation, long-chain drift and pipeline runtime
remain Phase 5 work. maestro1's HIP rebuild compiles the changed
`src/program/generate.cpp`; its fresh GDN parity build and the clean 123-step
SYCL engine build are recorded in the [Phase 2 backend report](../../bench/results/2026-10-09-phase2-backend-build/README.md).
SYCL uses its separate `sycl/src/program/generate.cpp`. The contract, oracle,
ownership and unchanged-route checks close Phase 2; broader transaction and
runtime cases remain explicit later-phase work.

Inherited results live in [Strata's Orin report](../../bench/results/2026-10-08-jetson-orin/README.md),
[maestro1's backend build report](../../bench/results/2026-10-08-maestro1-builds/README.md),
and [NInfer evidence](../../evidence/ninfer-orin/README.md). These describe their
original revisions and workloads. No integrated-runtime speedup, quality,
capacity, HIP/SYCL execution or desktop byte-identity result is claimed here.

The [Phase 1 harness](PHASE1.md) now supplies bounded process cleanup, durable
partial results, six GiB physical/cgroup admission, telemetry, explicit artifact
and binary inventories, exact formatted workload preparation and an API screening
adapter. The [integration notebook](PORTING_NOTES.md) records lessons for a future
Strata + Splash integration. The first [opt-in owner diagnostic](INSTRUMENTATION.md)
records primary verifier arena events, window graph instantiations, prefill-owned
allocations/views and MTP state/scratch arenas with a separate payload counter.
CUDA and trace-on/off real-model protocol checks pass. Verifier-only and expanded
HIP/SYCL builds pass. No HIP/SYCL GPU runtime execution is claimed. Runtime policy
and default dispatch are unchanged.

Fresh Orin checks: 46 integration harness tests, 15 Jetson setup tests, 312 selected
mock API tests, the pinned shared-memory budget test and six selected branch
CPU/core tests pass. The existing GPU conversation-snapshot test also freshly
passes 3901 synthetic state checks; this is not accepted-prefix commit parity. Both control binaries built as native ARM64 Release with
CUDA 12.6.68 and embedded SM87 images. Both source GGUF shards and all 31 MTP
source tensors were independently rehashed against pinned digests. Prepared
runtime packs have new identity hashes, not new numerical qualification.

Fresh paired controls cover all five exact workloads in four independent process
pairs (40 measured requests plus 40 warmups). Actual cache/KV/MTP resources match.
Three pairs have GPU/EMC observations in every measured request window; the first
pair's missing samples remain explicit. Dynamic clocks were observed, not changed.
Whole-process sampled physical headroom stayed above 8.35 GiB. Both binaries pass
seven real-model protocol/cancellation/recovery scenarios. The existing CUDA RMS
operator passes 25 independent FP64 oracle fixtures and eight invalid-argument
checks against the predeclared tolerance. These are control/correctness results,
not integrated-runtime speedups.

The [paired evidence report](../../bench/results/2026-10-09-paired-api-controls/README.md)
retains raw requests, failures, telemetry, medians, paired uncertainty, plots,
format inventory and the fresh four-token logit discrepancy (KL 1.302).
Multi-token content also varies between identical runtime controls; numerical
and persistent-state parity are not established. The [Phase 1 capability
matrix](../../bench/results/2026-10-09-phase1-capability-matrix.json) records
the full supported/failed/unsupported/not-run inventory and closes Phase 1 with
these exclusions visible. See [contracts](OPERATOR_CONTRACTS.md).

Phase 1 controls used four pairs, which is screening evidence rather than the
seven-pair confirmation required for promotion. HIP/SYCL shared-source builds
pass; their runtime behavior is unqualified.
Current workspace, graph, prefill and MTP observations are partial. Unique
physical ownership and future reservation semantics belong to Phase 3. Startup
free-memory traces and buffer descriptions are coarse observations, not ownership
accounting.
Native packs reject `--spec 0`; omit MTP weights while retaining a supported
native window for MTP-off. No throughput improvement, combined-runtime
qualification, sustained service or later-phase completion is claimed. NInfer
cohorts are not rebuilt here. The offline matrix remains a proposal; run one
model process at a time.

Fresh build, verification, test and native smoke evidence is retained in the
[October 9 control checkpoint](../../bench/results/2026-10-09-integration-controls/README.md).
Both smoke runs emitted token 846 from input 248045; unequal auto-cache allocation
excludes a performance comparison. Failed invocations are retained with reasons.


The [expanded owner report](../../bench/results/2026-10-09-prefill-mtp-owner-trace/README.md)
records seven protocol checks each for owned prefill, borrowed prefill and tracing
off. Default pinned-binary raw logits vary between processes. Explicitly
CPU-sharing-disabled four-token controls are byte identical across two pinned
processes and the candidate, while CPU-reference KL remains 1.385. This is a
narrow diagnostic, not default or whole-model parity. The requested 1024-token
KV residency at a 4K context is clamped to a fully resident path and does not
qualify streaming. The owned harness now saves actual initial capabilities and
can require an observed streaming mode. Verifier-only and expanded HIP/SYCL builds
pass. No backend GPU runtime result is available from maestro1.

Actual streaming startup/recovery now passes seven short-request checks with
reported resident20480/context32768 and cache5215 slots/10155 MiB. Sampled
physical availability stayed above 9.66 GiB. Paging across the resident boundary,
long-context quality and 32K capacity remain untested. The clamped 4K streaming
cell is explicitly rejected before requests and retained as unsupported. The
[capability manifest](../../bench/results/2026-10-09-prefill-mtp-owner-trace/CAPABILITIES.json)
keeps each qualification boundary explicit.

Expanded backend validation passed on maestro1. Verifier-only and expanded
HIP/SYCL builds completed; the fresh-root expanded SYCL build linked at 123/123
steps. Source hashes matched before configuration and after build. Three prior
setup failures are retained in the [backend report](../../bench/results/2026-10-09-expanded-backend-build/README.md).
Compilation is not GPU runtime qualification.


The fresh [IQ4_NL independent codec diagnostic](../../bench/results/2026-10-09-iq4-nl-codec-contract/README.md)
passes 14 cases / 3,726,080 values each for scalar CPU, CUDA F32 and CUDA BF16,
including all finite FP16 scales and a full synthetic 2560x640 expert-down
matrix. Exact represented bits, input preservation and guards pass. Production
code is unchanged. Other codecs, real payloads and NInfer RowSplit conversion
remain unqualified; this is contract preparation, not completed Phase 2.


The [checked projection seam map](../../bench/results/2026-10-09-projection-contract-map/README.md)
records all 48 layers / 108 selected source tensors as incompatible with direct
reuse of the pinned NInfer two-parent GDN/attention profiles. Required-profile
rejection preserves the evidence; no production converter/dispatch is added.
Parent and head layout differences join the codec/hidden-width mismatches.
This is Phase 2 contract evidence; it does not itself qualify a runtime adapter
or authorize a kernel change.


The [first pinned request profile](../../bench/results/2026-10-09-request-profile/README.md)
completes pp512+tg64 warmup/measured requests under Nsight with at least 7.86 GiB
sampled physical headroom. Q6_K→FP16 dequantization is the largest named kernel
by summed duration in both request windows (measured ~2.41 s / 23.7% of GPU
kernel-duration sum). Overlap/spin waits, profiler overhead and unbounded absolute
window alignment prevent a critical-path or speedup claim. This identifies a
hypothesis for later qualified operator/memory work, not an active optimization.



The [independent Q6_K codec diagnostic](../../bench/results/2026-10-09-q6-k-codec-contract/README.md)
passes 15 cases / 42,565,632 exact values each for scalar CPU and CUDA F32/BF16/FP16.
It checks every finite half scale, signed subscales/quants, row slicing and a
full synthetic 10240x2560 GDN QKV matrix. Sampled physical headroom exceeded24.3
GiB. This qualifies selected codec/conversion paths, not projection math,
model quality, reuse or speed.


Backend gate update: verifier-only and expanded HIP/SYCL builds pass. The fresh-root
SYCL retry used one compile job and verified source hashes before configuration
and after build. Three retained setup/configuration failures (CMake compiler
path/cache reset, unset Intel environment handling, and system CMake below the
required version) preceded the successful retry. See the [attempt log and build
identity](../../bench/results/2026-10-09-expanded-backend-build/README.md).
No GPU execution is claimed from maestro1.
