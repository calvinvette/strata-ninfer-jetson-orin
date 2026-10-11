# Integration status

Updated: 2026-10-11. Phases 1 and 2 are complete with their supported, failed,
unsupported and untested scopes recorded. Phase 3 memory ownership and transfer
work is active; its admission screens and focused owner tests are recorded below,
with broader pressure and transfer gates still open. No NInfer execution
component has been promoted into Strata.

| Phase | State | Evidence / next gate |
| --- | --- | --- |
| 0 — Repository and import | Complete | Pinned source/evidence manifest, source mapping, plan, offline planner checks |
| 1 — Same-day controls | Complete | Four same-day paired API blocks; exact workloads/artifacts; protocol and baseline checks; capability matrix records limits; expanded HIP/SYCL builds compile |
| 2 — Operator/state contracts | Complete | Ownership review, incompatible projection-profile rejection, independent RMS/IQ4_NL/Q6_K oracles, GDN prefix checks, default spec1 regression and post-fix spec1/spec4 token plus nine-field persistent-state parity recorded; native/HIP/SYCL build evidence and eleven selector tests pass; no NInfer execution component promoted |
| 3 — Memory and transfers | In progress | Opt-in trace covers ordinary ExpertCache, CUDA segmented-cache mapped VMM handles, shared CUDA VMM physical-chunk lifetimes and per-range map/unmap transitions, primary SessionState, verifier, prefill, MTP and separate pageable/pinned expert-stage host owners, with additional instrumentation for the opt-in layer-dump pinned-host buffer (runtime untested); Orin shrink/regrow lifecycle test preserved slot data and matched 41 allocate/free events; injected pinned-registration failures fell back to working pageable copies under the six-GiB supervisor; one injected expert-stage `cudaHostAlloc` refusal produced an observed pageable owner allocation/free, while five sibling pinned buffers also balanced at teardown; the 10 instrumented allocation/free pairs in this request matched, with zero observed live bytes at teardown; the request and forced-pageable control generated one token above the memory floor (targeted test minimum 7.58 GiB); two randomized fixed-cache 4K staging screens matched tokens and nine state fields; the trace-corrected clocked repeat found +0.10% median prompt time and variable decode results with dynamic CPU/GPU clocks; minimum availability was 8.04 GiB; a randomized 2×2 requested-cache/context screen completed all cells above the six-GiB floor, with actual slots 3903/6519; a 2×2 prefill-chunk/borrowed-vs-owned screen observed separate 202/500 MiB workspace holds and remained above 7.47 GiB; owned chunk 1024/2048 follow-up reserved up to 1520 MiB and remained above 7.72 GiB; an exact 2048-token prompt completed against the 2048 owned chunk with 8.02 GiB minimum availability; the Oct 10 focused 10-test Phase 3 CTest set passed with 23.8 GB minimum availability during a separate bounded 4 GiB cgroup allocation; a fresh Oct 10 ten-test PLE/memory rerun passed with 27.80 GiB minimum availability; 12 and 16 GiB cgroup-limited IQ1_M runs reached prefill then were supervisor-aborted at the effective 6 GiB floor (host availability remained 22.2 and 15.6 GiB); the same request passed under 20/24 GiB caps with 9.58/8.84 GiB minimum effective availability and in a fresh uncapped process at 7.62 GiB; simulated expert-cache allocation failure retried at 4,753 slots and completed; late prefill workspace injection and post-warmup CUDA allocation failure each caused a supervised engine restart and successful one-token service recovery; seven randomized fixed-cache mapped/pread pairs matched all tokens and nine persistent-state fields, with mapped median total request time 4.14% lower (bootstrap median interval −5.57% to −4.02%) and at least 8.01 GiB available; a separate seven-pair 3,903-slot mapped/pread run collected temporary systemd-scope `io.stat` counters, matched tokens and state, and observed a −5.08% mapped request delta plus −1.010 GB median scoped read difference; the pread arms consumed zero prefetched blobs and had zero reported decode wait, so this cell did not measure a request-path pread stall; the artifact-aware Q2_0 PLE oracle passes all seven stages for real layer-1 weights and table rows (three-token block, synthetic hidden/history), reassembles the native key byte-identically, and matches the native projection to the independent decoded path; a separate 64-row real-table reader check is bit-identical; captured graph arm completed with state fingerprints and 13.19 GiB minimum availability, but eager comparison is unsupported because `session_token` lacks the CPU expert-pool hook and `--no-pool` fails profile-filled VRAM tier admission; a seven-pair prefetch-fill/stage confirmation matched tokens and state, with staged median request time 3.11% lower (paired bootstrap interval −5.81% to −1.05%), 0.472 GB fewer scoped reads at the median, 205–325 staged blobs consumed, 1.14–3.40 s aggregate decode wait, and up to 167.6 MiB pageable host staging; dynamic clocks and two large outliers limit this single workload/cache cell; a calibrated root-readable NVMap IOVMM client table measured a repeatable 83,427,328-byte process-owner increase across ten graph instantiations in three IQ1_M service startups; this is the capture/instantiate interval for that configuration, while other graph paths and non-NVMap allocations remain unpriced |
A new randomized [Q2_0 model cache × context admission screen](../../bench/results/2026-10-11-phase3-q2-admission/README.md) passed all four 3,000/5,000-slot × 4K/8K cells with one generated token under the six-GiB floor (15.88–18.52 GiB minimum availability). The reported session-state backing grew by 108,068,864 bytes when context doubled; the owner logs balanced 276/276 allocations and frees in each cell. This supplies an actual Q2_0-model admission point, not capacity, quality or performance qualification. The [Q2_0 active-cgroup admission follow-up](../../bench/results/2026-10-11-phase3-q2-cgroup-admission/README.md) passed the 512-token/one-output request under 10/12/20/24 GiB caps, with minimum effective availability 7.85/6.99/12.92/13.73 GiB; host `MemAvailable` stayed at least 18.48 GiB. The same requested 3,000-slot cache admitted 296/805/3,000/3,000 actual slots, respectively. At 8 GiB, no slots were admitted; prefill completed before the native speculative path failed due to the missing device residency table, with 6.74 GiB minimum effective availability. This is one workload/cache/context point; 8 GiB was not a successful request or a general minimum-capacity threshold. A seven-pair [PLE direct/mmap owner-traced diagnostic](../../bench/results/2026-10-11-phase3-q2-ple-mmap-confirm7/README.md) also balanced 276 allocations/frees per process with zero observed live bytes, but its timings are excluded because tracing adds prompt-path events. A separate three-pair [tracing-off timing screen](../../bench/results/2026-10-11-phase3-q2-ple-mmap-untraced3/README.md) had paired deltas from −9.31% to +13.27% and only a 0.49% difference in median prompt time; the PLE counter was 0.3 ms in both arms. This does not establish a transfer benefit and promotes no mode. The latest [current-binary Q2_0 PLE and Phase 3 rerun](../../bench/results/2026-10-11-phase3-current-ple-memory/README.md) passed all seven PLE stages for three tokens (worst relative L1 `1.148e-7`; 24.64 GiB minimum availability), the focused ten-test CTest set (24.54 GiB minimum), and all 20 owner-observation unit tests. These confirm selected contracts; graph-memory attribution, broad cgroup-pressure behavior and remaining transfer/admission gates remain open. A subsequent [15-test accounting and owner regression](../../bench/results/2026-10-11-phase3-accounting-ctest-current/README.md) passed shared-budget arithmetic, conversation/cache reservations, per-layer cache and convolution-state cache tests alongside VMM, PLE, refusal and pinned fallback coverage (24.63 GiB minimum availability). A seven-pair [prefill chunk 32 vs 128 screen](../../bench/results/2026-10-11-phase3-prefill-paired/README.md), with the same 5,000 cache budget and 512-token prompt, reduced median request time by 63.0% and TTFT by 65.1%, while median decode rate fell 6.8%; all outputs matched and the minimum availability was 8.44 GiB. It is a one-prompt screening cell only; no default changed, and held-out quality/confirmation remains required. The follow-up [three-length default-sharing screen](../../bench/results/2026-10-11-phase3-prefill-interaction-screen/README.md) matched output text in 8/9 chunk pairs (172, 557 and 1,069 prompt tokens); the CPU-sharing-disabled rerun matched only 6/9 ([report](../../bench/results/2026-10-11-phase3-prefill-interaction-noshare/README.md)). Both show higher prefill rates at chunk 128, but longer-prompt output drift leaves quality unqualified. No chunk default is promoted.

With the same 256-slot request, Q2_0 failed after prefill at 8 and 9 GiB
cgroup caps with zero slots admitted, then passed at 9.5 and 10 GiB with all 256
slots and emitted token 32. The observed pass bracket is 9–9.5 GiB for this
exact cell; minimum effective availability was 6.78–8.45 GiB and host
`MemAvailable` stayed above 21 GiB. The separate 10 GiB/3,000-slot cell admitted
296 slots. This is not a general capacity threshold; see the [four-cell
bracket](../../bench/results/2026-10-11-phase3-q2-cgroup256-bracket/README.md).

For a 64-token Q2_0 request with the same 256-slot budget, the 9.5, 10
and 12 GiB scopes were supervisor-aborted before prefill; the 16 GiB cell
completed prefill but was aborted before request completion. The 18 and 20 GiB
cells completed all 64 tokens. Host availability stayed above 21.5 GiB. These
longer-request cells have larger scoped-memory demands than the one-token
admission bracket and do not establish a general capacity threshold; see the
[Q2_0 64-token cap sweep](../../bench/results/2026-10-11-phase3-q2-cgroup256-tg64/README.md).

The artifact-aware Q2_0 PLE oracle was also rerun inside a 10 GiB cgroup
scope and passed all seven stages for three tokens (worst relative L1
`1.148e-7`); minimum effective availability was 9.97 GiB and host
`MemAvailable` remained at least 24.64 GiB. The measured scope peak was 32.1
MiB for this short operator fixture and is not a full-runtime memory estimate.
See the [cgroup PLE run](../../bench/results/2026-10-11-phase3-q2-ple-cgroup10G/README.md).

The requested [Q2_0 PLE and Phase 3 rerun](../../bench/results/2026-10-10-phase3-qfuse-smoke/README.md) passed `ple_parity` plus nine focused memory/owner tests under the six-GiB supervisor (24.09 GiB minimum availability). An opt-in QFUSE serial/batch smoke matched one-token outputs and traced its 320-byte verifier counter allocation/free. The QFUSE full GDN fingerprint differs from the default route; repeated low-16-bit per-layer digests do not establish equality, so GDN parity remains unverified and QFUSE is not qualified on Orin. The state-hash path now checks session sizing and rejects empty or malformed per-layer ranges. The [final session teardown follow-up](../../bench/results/2026-10-11-phase3-session-release/README.md) recorded matching frees for the primary arena and both batch slots; 281 allocations/frees balanced with zero live host/device bytes, and four session/checkpoint CTests passed. Split-stage teardown compiled for CUDA/HIP but still lacks runtime hardware coverage. Phase 3 remains open for broader graph configurations and the remaining transfer and admission measurements.

The [CUDA allocation visibility calibration](../../bench/results/2026-10-11-phase3-cuda-memcharge-calibration/README.md) found that `cuMemGetInfo`, host `MemAvailable`, cgroup usage and `tegrastats` did not show a 512 MiB allocation. A subsequent root-readable [NVMap IOVMM calibration](../../bench/results/2026-10-11-phase3-graph-nvmap-calibration/README.md) tracked that allocation exactly and measured 83,427,328 bytes of net process-owner growth across ten graph-instantiation calls in each of three IQ1_M service startups. This prices that capture interval only; other graph paths remain unqualified. Phase 3 remains open. A distinct [Q2_0 spec2 graph follow-up](../../bench/results/2026-10-11-phase3-q2-graph-nvmap/README.md) measured an identical 72,425,472-byte stable-to-stable NVMap increase across the first request and four successful graph instantiations in three fresh processes; all seven protocol/recovery scenarios passed, with at least 21.17 GiB host availability. The integration trace initially missed the verifier commit graph; the new owner label now accounts for four of four successful runtime graph calls in a post-patch service check. This interval includes adjacent synchronous device allocations and is not an isolated executable size. Phase 3 remains open.

The broader [owner and memory regression rerun](../../bench/results/2026-10-11-phase3-owner-accounting-ctest/README.md) passed all 14 available selected CTests on the current binary, including the Q2_0 artifact-aware PLE oracle and cache/VMM/accounting cases. It ran sequentially under the six-GiB supervisor with 24.60 GiB minimum host availability. This confirms those focused contracts after the graph-owner changes; it does not close the outstanding graph-pool, broad pressure or transfer-measurement gates.

The new [generic captured-graph runtime test](../../bench/results/2026-10-11-phase3-captured-graph-runtime/README.md) captures and replays a real asynchronous CUDA operation, checks its output and observes exactly one `captured-graph` owner event on Orin. Three calibrated NVMap process-owner repeats found no detectable net backing change (0 bytes at 50 ms sample resolution) for this minimal graph. This qualifies the generic wrapper's trace and bounds one graph's NVMap effect, while allocations outside NVMap, legacy model session graphs and model graph-pool bytes remain unmeasured.

Three more Q2_0 64-token requests at a 20 GiB cgroup cap produced two complete, token-identical passes and one supervisor abort at 5.48 GiB effective scope headroom during prefill; host availability remained above 21.65 GiB in every run. The new cgroup `memory.stat` sampler showed file cache at 8.29 GB and anonymous use at 1.63 GB at the passing repeat's peak; cgroup OOM/max events remained zero. This confirms the cap-20 result is workload/process-history sensitive, not a supported threshold. See the [repeatability run](../../bench/results/2026-10-11-phase3-q2-cgroup20G-cache256-tg64-confirm3/README.md).

| 4 — SM87/ARM kernels | In progress | Pinned and current-candidate request profiles both rank Q6_K→FP16 dequantization first by summed kernel duration; the current profile's grids map to five repeated Q6_K matrix shapes in IQ1_M; six-type real-payload F32/BF16 and dedicated five-shape real-payload H16 checks pass, with 51,200 exact FP16 outputs and preserved packed input; linked SM87 kernel uses 22 registers/thread with zero stack, spills, shared or local memory; an isolated full-matrix CUDA-event baseline covers all five real shapes (median 0.198–4.759 ms); three-process CTA-size screen found no consistent winner and did not promote 128/256/512-thread candidates; Nsight Systems CPU sampling observed frequent ExpertPool worker-loop instruction samples, then a 3-block 1/2/4/8/11-worker screen found a correctness-gate failure (output drift at 11 workers and cross-cell state-fingerprint differences), so timings are retained as exploratory and no default changed; runtime Nsight Compute counters and Compute Sanitizer are unsupported here (profiling privilege warning; GPU debugging features disabled); an opt-in accepted-prefix trace captures published IDs and full state after each verifier commit; default CPU prefill sharing caused repeatable first-commit state divergence, while disabling it yielded identical token IDs, full accepted-prefix state and 36 GDN hashes across five processes; the 3-block 1/2/4/8-worker screen with sharing disabled passed all cells with equal cache capacity, output and accepted-prefix state, and minimum 14.06 GiB host availability; its trace-heavy timings were correctness-only. The follow-up [no-trace 3-block worker screen](../../bench/results/2026-10-11-phase4-pool-workers-512-no-trace/README.md) passed output/cache checks in all 12 cells; 8 workers were fastest in all three paired blocks (median request 17.61 s), with 13.24 GiB minimum host availability. This remains one workload/policy and no-trace state was not compared. Output quality and held-out confirmation remain open; no default changed |
| 5 — Speculation and graphs | Not started | Accepted-prefix state, graph lifetime and drift qualification |
| 6 — Multivariate tuning | Not started | Randomized paired campaign, interactions, uncertainty, held-out confirmation |
| 7 — Capacity and service | Not started | Quality, recovery, thermal equilibrium and sustained workload |
| 8 — Release/upstream | Not started | Relevant backend builds, runtime matrix and reviewable changes |

A [long-to-short same-process recovery check](../../bench/results/2026-10-11-phase3-long-short-recovery/README.md) ran a 2,048-token prefill and then a distinct 172-token request in one IQ1_M service process. Both completed all eight requested tokens with no prompt-cache reuse; owner events balanced 52 allocations/frees, and host availability stayed above 13.41 GiB. A separate [long-request disconnect check](../../bench/results/2026-10-11-phase3-cancel-long-prefill-recovery/README.md) closed a streamed 2,048-token request after one second, then recovered with a short request in the same process; the engine read the full prompt, generated no tokens, and reported cancellation. Its 52 allocation/free events also balanced, with 13.33 GiB minimum host availability. This confirms cleanup after disconnect, but active prefill did not stop early. Neither check covers cancellation under memory pressure or qualifies long-context quality. Phase 3 remains open for broader graph, pressure and transfer measurements.

The fresh [current-checkout Q2_0 PLE rerun](../../bench/results/2026-10-11-phase3-ple-rerun/README.md) again passed all seven stages for three tokens (worst relative L1 `1.148e-7`; 24.64 GiB minimum host availability). The sequential 15-test Phase 3 accounting/owner CTest selection also passed (24.60 GiB minimum). This confirms the checked operator and ownership contracts on the current candidate; graph-path attribution, broader pressure and transfer/admission measurements remain open.

An attempted [legacy session-graph runtime probe](../../bench/results/2026-10-11-phase3-legacy-session-graphs/README.md) was rejected before model load because the only local pack is native and requires the native execution path. It did not exercise the untested per-layer/session-token graphs; a compatible legacy pack or direct graph fixture is needed.

A fresh three-pair [pageable/pinned expert-stage check](../../bench/results/2026-10-11-phase3-stage-pin-confirm512/README.md) on the current IQ1_M binary matched all generated IDs and nine persistent-state fields, with both staging owner classes observed. Minimum host availability was 13.21 GiB. One pageable decode arm was a large outlier; timing remains descriptive, and no staging mode is promoted.

The [accepted-prefix state trace](../../bench/results/2026-10-11-phase4-accepted-prefix-trace-fixed/README.md) now records per-commit token IDs and the full state fingerprint after waiting for async commit completion. In four short Orin runs, output IDs matched, but GDN, QSA/KV and MTP state differed at the shared first committed boundary and across same-worker repetitions. A separate end-of-request state-hash control passed with the new code and per-commit tracing disabled. Trace hashing is synchronization-heavy and is correctness-only; worker timing remains disqualified pending a root-cause explanation. The native CUDA and maestro1 HIP builds pass for the changed generator; the SYCL build passes against its separate generator tree.

The [full-width GDN localization](../../bench/results/2026-10-11-phase4-gdn-layer-fullhash/README.md) reproduces drift at GDN ordinal 3 after the first QSA layer: with default CPU prefill sharing, two same-worker runs diverged on token seven and their per-GDN hashes first differed at ordinal 3. In a controlled [CPU-share-disabled repeat](../../bench/results/2026-10-11-phase4-gdn-prefill-share-control/README.md), two processes matched all eight tokens, full accepted-prefix state and all 36 GDN hashes. This supports the heterogeneous CPU/GPU prefill expert path as the cause. A follow-up [three-process no-share confirmation](../../bench/results/2026-10-11-phase4-gdn-prefill-share-confirm3/README.md) matched all tokens, full accepted-prefix state and 36 GDN slices in each process, extending the no-share result to five processes across two runs. This remains correctness evidence only; output-quality and CPU-share performance comparisons remain open. No worker timings are qualified and no default changes. A separate [prefill chunk accepted-state trace](../../bench/results/2026-10-11-phase4-prefill-state-trace/README.md) found chunk 32 and 128 repeatable within setting over two runs each, with identical eight token IDs, but different committed state at the first boundary `L=1069`; all 36 GDN layer hashes differ starting at ordinal 0, alongside PLE/QSA/KV/MTP hashes. This persists with CPU sharing disabled and shows a deterministic chunk-dependent state difference; its numerical magnitude and task-level quality remain unmeasured, so no chunk default is promoted. The [numeric GDN follow-up](../../bench/results/2026-10-11-phase4-prefill-state-numeric/README.md) dumped the first accepted `L=1069` state on one additional process per setting, after a shorter warmup. Chunk 32 vs 128 differs in 98.37% of 29.42 million float32 values; relative L2 is 3.138%, with maximum per-layer relative L2 5.33%. The runs pass the six-GiB floor and produce eight tokens, but do not identify a more accurate state or qualify task quality. The dump path is opt-in and no default is promoted.

The new [fixed-share numerical comparison](../../bench/results/2026-10-11-phase4-prefill-share-state-numeric/README.md) captures the measured request (after a distinct-length warmup) and confirms a 3.172% GDN relative-L2 difference at `L=512` between share-off and fixed 0.5, despite matching output through 64 tokens. Both admitted the same 6,519 cache slots and remained above the six-GiB floor; accepted-prefix state hashes diverged. The no-share and fixed-share cache-3000 three-process controls are now documented with their raw summaries. This is a correctness/diagnostic result, not a performance promotion or quality verdict.

A matched [default-auto CPU-share repeatability check](../../bench/results/2026-10-11-phase4-gdn-auto-share-cache3000/README.md) used the same 3,903 admitted cache slots and eight workers as fixed 0.5-share and share-disabled three-process controls. Auto mode emitted identical eight-token outputs and accepted token IDs, but persistent-state hashes diverged at every observed verifier boundary across processes, so its correctness gate failed and timings are excluded. The two fixed policies were each internally repeatable but ended with different committed state, leaving numerical/task-level accuracy unresolved. The first fixed-share attempt at a 5,000-slot budget is excluded because actual capacity varied. No prefill-sharing policy is promoted.

The [GDN prefix kernel check](../../bench/results/2026-10-09-gdn-prefix-kernel/README.md)
adds direct recurrence and convolution-history prefix evidence in Phase 2. The
model-level accepted-prefix check below now supplies the separate verifier and
publication-boundary state evidence for the observed output-clipping case.

The fresh [Phase 3 follow-up test run](../../bench/results/2026-10-10-phase3-followup-tests/README.md)
passed the artifact-aware Q2_0 PLE test and nine focused memory/VMM tests under
the six-GiB supervisor, with 27.80 GiB minimum physical availability. The base
user namespace lacks `/proc/<pid>/io` and leaf-cgroup `io.stat`, but a temporary
systemd scope with `IOAccounting=yes` enabled scoped read accounting for the
[seven-pair transfer confirmation](../../bench/results/2026-10-10-phase3-transfer-cgroupio-confirmation7/README.md).
A later direct [Q2_0 PLE rerun](../../bench/results/2026-10-10-phase4-ple-rerun/README.md)
also passed under the same six-GiB supervisor (24.53 GiB minimum availability).
A calibrated [NVMap owner trace](../../bench/results/2026-10-11-phase3-graph-nvmap-calibration/README.md) measured a 79.5625 MiB graph-capture/instantiation interval in three IQ1_M service startups. Other graph configurations and non-NVMap allocations remain unpriced; transfer evidence is still scoped to individual workload/cache points. Phase 3 remains open and no path or default was promoted.

The separate [pinned-copy timing screen](../../bench/results/2026-10-10-phase3-copy-latency/README.md)
measured 64 MiB H2D copies at a 2.909 ms median across seven supervised
processes (23.067 decimal GB/s); individual samples include larger outliers.
It isolates the copy operation but does not compare mapped reads or establish
request-level transfer benefit.

The [seven-pair prefetch fill-versus-stage confirmation](../../bench/results/2026-10-10-phase3-transfer-stage-confirmation7/README.md) exercised the stage handoff in real requests. All tokens, nine persistent-state fields and 3,903 actual cache slots matched; minimum availability was 13.11 GiB. Staging reduced median request time 3.11% (paired bootstrap interval −5.81% to −1.05%) and median scoped reads by 0.472 GB. Stage arms consumed 205–325 prefetched blobs, reported 1.14–3.40 s aggregate decode wait, and allocated up to 167.6 MiB pageable host staging. Two large timing outliers, dynamic clocks, and the single prompt/cache point limit the result. The path stays opt-in pending a held-out workload and broader energy/memory assessment.

The [cgroup-accounted mapped/pread comparison](../../bench/results/2026-10-10-phase3-transfer-cgroupio-confirmation7/README.md)
matched tokens, all nine state fields and 3,903 actual cache slots in seven
randomized pairs. Mapped median request time was 5.08% lower, with a paired
bootstrap interval of −8.19% to −3.50%; scoped block reads were a median 1.010
GB lower per request (interval −1.626 to −0.736 GB). Dynamic clocks, one
prompt/output shape and two large request-time outliers limit this result to
screening/confirmation for that cell. The mapped or pread route remains
unchanged by default.

The [Oct 10 owner/PLE follow-up](../../bench/results/2026-10-10-phase3-owner-tests/README.md) adds allocation/free observations for the optional layer-dump pinned host buffer and rebuilds CUDA/HIP. Its actual Orin event is untested because the available native pack requires speculation while layer dumping disables the token graph. The selected PLE/memory batch passed 9/10; `ple_reader_selftest` had transient 110-byte-row keepalive timing failures, then passed in an isolated supervised rerun. The artifact-aware Q2_0 `ple_parity` cell passed in the batch.

The [verifier auxiliary owner follow-up](../../bench/results/2026-10-10-phase3-verifier-aux/README.md) traces verifier profile, Q8-fuse, device-plan, slot-offset, probabilistic-sampling and batch-window device buffers. A traced one-token Q2_0 profile run balanced 282 allocation/free pairs, including a 12,704-byte profile buffer, with zero observed live bytes and 16.39 GiB minimum `MemAvailable`. Later follow-ups exercised Q8-fuse and the probabilistic 4,128-byte token/distribution scratch; Q8-fuse GDN parity remains unqualified, while the probabilistic check covered owner lifecycle only.

The [batch-session owner smoke](../../bench/results/2026-10-10-phase3-batch-session-owners/README.md) traces the primary and batch-slot sessions plus the verifier batch arena. Two independent serial-versus-concurrent Q2_0 runs admitted two slots, matched outputs and all nine state hashes by prompt identity. Each batch session requested 235,034,112 bytes; the verifier batch arena requested 37,120 bytes and freed. Minimum `MemAvailable` was 15.30 GiB. The [final teardown follow-up](../../bench/results/2026-10-11-phase3-session-release/README.md) records frees for the primary and batch arenas, with zero live requested bytes. A [full eight-slot admission smoke](../../bench/results/2026-10-11-phase3-batch-8-slot-teardown/README.md) balanced 287/287 allocation/free events, with all eight batch sessions admitted and freed. Stage teardown is implemented but lacks runtime coverage on this single-GPU host. CUDA and maestro1 HIP builds passed.

The [device-plan owner check](../../bench/results/2026-10-10-phase3-verifier-device-plan/README.md) forces `STRATA_VERIFY_DEVICE_PLAN=1` on the same Q2_0 two-slot workload. The 64-byte skip scratch and 40,000-byte slot-offset copy both allocated and freed; outputs and all nine state hashes matched the default route by prompt identity. Minimum `MemAvailable` was 15.30 GiB. The [probabilistic MTP owner smoke](../../bench/results/2026-10-11-phase3-spec-prob-owner/README.md) offered 21 drafts, accepted 6, and balanced its 4,128-byte verifier scratch; `spec_verify_parity`, `coupled_draft_test`, and `spec_prob_test` passed. Distribution-quality and model-level accepted-prefix parity remain untested for this route.

A held-out [2,048-token mapped/pread confirmation](../../bench/results/2026-10-11-phase3-transfer-heldout-2048/README.md) also matched tokens, nine state hashes and cache use in seven pairs, with 8.09 GiB minimum availability. Mapped request time was 1.31% lower (95% paired interval −2.01% to −0.52%); prompt time was 0.60% higher, while decode was 19.49% lower. Whole-board energy intervals include zero. Dynamic clocks and system-wide I/O/rail counters remain limitations, so this workload cell does not justify a default change.

The seven-pair [fixed-cache mapped/pread energy confirmation](../../bench/results/2026-10-11-phase3-transfer-energy-confirmation7/README.md) matched output IDs, all nine persistent-state hashes, 6,519 cache slots and 49,629 cache hits in every pair under the six-GiB floor (8.15 GiB minimum). Mapped request-time median was 6.26% lower (paired bootstrap 95% interval −9.69% to −4.24%); whole-board VIN_SYS_5V0 median rail energy was 5.39% lower (−8.19% to −0.86%). Two large timing outliers are retained, CPU clocks varied from 729–2,201 MHz, GPU/EMC clocks were unavailable, and rail/device counters include unrelated activity. This adds energy evidence to one transfer cell only; no default changed and Phase 3 remains open.

A held-out [2,048-token mapped/pread confirmation](../../bench/results/2026-10-11-phase3-transfer-heldout-2048/README.md) also matched tokens, nine state hashes and cache use in seven pairs, with 8.09 GiB minimum availability. Mapped request time was 1.31% lower (95% paired interval −2.01% to −0.52%); prompt time was 0.60% higher, while decode was 19.49% lower. Whole-board energy intervals include zero. Dynamic clocks and system-wide I/O/rail counters remain limitations, so this workload cell does not justify a default change.

The seven-pair [fixed-cache mapped/pread energy confirmation](../../bench/results/2026-10-11-phase3-transfer-energy-confirmation7/README.md) matched output IDs, all nine persistent-state hashes, 6,519 cache slots and 49,629 cache hits in every pair under the six-GiB floor (8.15 GiB minimum). Mapped request-time median was 6.26% lower (paired bootstrap 95% interval −9.69% to −4.24%); whole-board VIN_SYS_5V0 median rail energy was 5.39% lower (−8.19% to −0.86%). Two large timing outliers are retained, CPU clocks varied from 729–2,201 MHz, GPU/EMC clocks were unavailable, and rail/device counters include unrelated activity. This adds energy evidence to one transfer cell only; no default changed and Phase 3 remains open.

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

The [pinned registration fallback check](../../bench/results/2026-10-09-pinned-fallback-pressure/README.md)
forces `cudaHostRegister` failure in the existing arena test, confirms the
registration error is cleared, and verifies a pageable copy round trip. This
is complemented by the [expert-stage `cudaHostAlloc` fallback check](../../bench/results/2026-10-10-phase3-stage-hostalloc-failure/README.md):
one precisely targeted allocation failure produced a pageable expert-stage
owner, the request completed, and the pageable plus pinned buffers all had
matching teardown events. Neither test simulates actual memory pressure.

The [expert-cache allocation retry](../../bench/results/2026-10-10-phase3-cache-failure-retry/README.md)
injects one automatic-cache allocation failure in the real IQ1_M Orin path.
The engine retries with a smaller cache, populates its profile and completes a
511-token prompt plus one generated token. This qualifies that retry path under
the six-GiB floor, not actual system pressure, `cudaHostAlloc` fallback, or a
performance difference.

The [late prefill-workspace failure check](../../bench/results/2026-10-10-phase3-prefill-workspace-failure/README.md)
refuses the owned path's 32 MiB GEMM workspace after the FP16 scratch has been
allocated. The CLI fails cleanly, traces frees for the partial prefill owner and
cache, and stays above the six-GiB floor; its session owner remains live until
process exit. A fresh no-fault process completes the same request. A same-server
API probe showed the 32 MiB workspace is allocated during server warmup and
reused by the first client request; allowing warmup therefore did not inject a
request failure. A marker-gated request-time CUDA allocation refusal now
produced HTTP 503 and an engine abort during long prefill; the resident Python
service restarted the engine and the next request succeeded. Separate
per-generation traces record 32 allocations/no frees before abort (reclaimed at
process exit), then 32 allocations/31 frees after restart, with the session
arena still resident. Minimum physical availability was 7.80 GiB. This qualifies
service restart recovery, not in-place engine recovery or graceful cleanup of
the aborted engine; the refused 1 MiB request-path allocation is GEMM host
buffer backing, not the 32 MiB cuBLAS workspace itself.

The initial [mapped-versus-pread file-tier screen](../../bench/results/2026-10-10-phase3-mapped-pread-screen/README.md)
ran three randomized pairs on an exact 512-token/64-output request. Tokens and
nine persistent-state fields matched in all pairs, with 8.17 GiB minimum
availability. Mapped decode median was 22.7% lower, while prompt median was
1.7% higher; this small screen is not a promotion result. Process page faults
were collected, but process-level disk bytes were unavailable. A same-day
randomized repeat now records NVMe partition read sectors: mapped median 7.52
GiB, pread 8.23 GiB, with mapped-minus-pread paired deltas between -742 MB and
-1.19 GB. These whole-device counters include unrelated reads and readahead,
not isolated engine bytes. Request medians again favored mapped in total time;
copy latency, energy and GPU/EMC clocks remain unmeasured, so the full transfer
gate stays open.

The [request-local transfer telemetry follow-up](../../bench/results/2026-10-10-phase3-transfer-telemetry/README.md)
adds engine-side file-tier byte and summed pread-worker-time counters, seeded
after startup so first-request deltas exclude cache population. On a three-pair
512-token/64-output screen, both arms handed out 40,996.1 MB per request; pread
read 2,216–2,298 MB in its workers, which spent a summed 2,516–2,723 ms. Mapped
page-cache residency at handout was 33.4–33.7 GB. Pread cache-residency fields
are omitted because that path does not sample them. The screen matched token
IDs and nine state fields, but remains screening evidence: `/proc/self/io` bytes
are unavailable, device counters are host-wide, and energy/copy/clock data are
still missing.

The initial [energy-instrumented transfer diagnostics](../../bench/results/2026-10-10-phase3-transfer-energy/README.md)
used automatic expert-cache sizing, which selected different resident capacities
across processes and invalidated their state and timing comparisons. The
three-pair [fixed-cache repeat](../../bench/results/2026-10-10-phase3-transfer-energy-fixed-cache/README.md)
held the requested cache at 5,000 (6,519 actual slots) in all six arms. Tokens
and all nine persistent-state fields matched in every pair; median mapped
request time was 4.27% lower, and the `VIN_SYS_5V0` rail estimate was 4.73% lower
as a descriptive paired median. This remains three-pair screening only: clocks
were dynamic, GPU/EMC frequencies were unavailable, rail energy includes
unrelated activity, and process read bytes were unavailable. A subsequent
[seven-pair fixed-cache confirmation](../../bench/results/2026-10-10-phase3-transfer-confirmation7/README.md)
matched tokens and all nine state fields in every pair; mapped median total
request time was 4.14% lower (paired-bootstrap median interval −5.57% to
−4.02%). The physical floor remained 8.01 GiB. This remains scoped to one
workload, with un-attributed device reads and rail energy; no transfer path or
default is promoted. A separate MTP-off one-token control also matched all
state fields when it held 6,519 expert slots fixed, unlike its auto-sized repeat.
For these comparisons, fixed expert residency is a required control.

The traced [API cancellation and recovery run](../../bench/results/2026-10-10-phase3-cancel-recovery/README.md)
passed all seven real-model protocol scenarios, including prefill and decode
cancellation followed by successful requests through the same engine process.
Instrumented expert-cache, prefill, MTP and verifier allocations balanced; the
resident session owner stayed live by design. Minimum physical availability was
7.65 GiB. At that stage, graph-pool bytes had not been priced; the later calibrated
NVMap startup interval is recorded in the [graph-memory follow-up](../../bench/results/2026-10-11-phase3-graph-nvmap-calibration/README.md). This run does not test persistent state parity or injected late-workspace recovery.

A separate [long-then-short service recovery smoke](../../bench/results/2026-10-10-phase3-long-request-recovery/README.md)
completed a 3,522-token prompt and 256-token output, followed by a one-token
request through the same engine. Both returned HTTP 200 and minimum availability
was 7.81 GiB. The service started once. Prefill, expert-cache and MTP owner
buffers were released at orderly shutdown; the trace does not show per-request
workspace release or a unique transient peak. This closes only the basic
post-long-request availability check, not recovery after allocation failure or
state parity.

The candidate [vision-enabled image request](../../bench/results/2026-10-10-phase3-vision-allocation/README.md)
now passes with the optional CUDA encoder built locally. Its 56×56 image request
completed at the six-GiB floor (minimum 7.22 GiB); startup reported 7.43 GiB
available after cache, verifier and MTP setup. This is one small-image smoke
point. A process-tagged CUDA runtime probe measured 871.4 MiB peak in
`strata-vision` and a separate 17.72 GiB engine runtime-allocation high-water
mark; both are attribution ledgers, not a physical-memory total. Host
`MemAvailable` remained the authority (7.21 GiB minimum). The probe misses
driver/internal and graph-executable memory, so transient and graph peak
accounting remains incomplete.

The [captured graph memory screen](../../bench/results/2026-10-10-phase3-graph-capture-screen/README.md) records a valid captured request and the unsupported eager control. At that stage, the available process-exclusive GPU/NVMap counters were uncalibrated. A later root-readable NVMap IOVMM client trace, calibrated against a live 512 MiB CUDA allocation, measured repeatable net process-owner growth across graph startup in the current IQ1_M configuration; see the [three-process follow-up](../../bench/results/2026-10-11-phase3-graph-nvmap-calibration/README.md).

The [CUDA graph allocator probe](../../bench/results/2026-10-10-phase3-graph-memory-probe/README.md)
observed 10 graph instantiations, 1,900 memory snapshots, and zero graph async-
allocator usage. A 4 MiB graph-allocation calibration correctly reported the
driver's 32 MiB reservation after launch. Strata's captured graphs have no async
allocation nodes, so these attributes do not account for their executable or
driver memory. The largest free-memory drop across one instantiate call was
116.8 MiB, a correlated global device delta rather than a graph allocation
measurement; graph peak accounting remains open.

A follow-up [public CUDA Driver allocation probe](../../bench/results/2026-10-11-phase3-graph-driver-probe/README.md)
passed all seven real-model protocol/cancellation cases and observed 10 graph
instantiations, but zero interposable public Driver allocation calls during
instantiation. Its direct 2 MiB Driver allocation/free calibration passed, so
a later calibrated NVMap client trace measured the graph-capture/instantiation startup interval for one IQ1_M configuration; the public Driver probe still documents why its zero allocation-event count cannot be read as zero graph memory. See the [NVMap follow-up](../../bench/results/2026-10-11-phase3-graph-nvmap-calibration/README.md). Phase 3 remains open for other paths. The [IQ1_M/MTP owner-label rerun](../../bench/results/2026-10-11-phase3-iq1-graph-owner-check-rerun/README.md) then matched all ten successful runtime instantiations to integration owner events (three verifier windows, one commit graph, and six MTP graphs). All seven API/cancellation/recovery scenarios passed with 7.72 GiB minimum host availability. This closes attribution for the exercised call sequence only; it does not price graph pools or close Phase 3. The changed CUDA/HIP `strata` target and full SYCL `strata` target also build on maestro1; the SYCL retry needed its installed oneMKL library directory on `LIBRARY_PATH` and emitted transitive Intel runtime-library warnings. These are x86 build checks, not backend runtime evidence. Session pre/post/stage, token-session and generic `CapturedGraph` creation sites now also emit owner events in CUDA/HIP and SYCL. The current native pack bypasses these legacy paths, so their runtime coverage remains untested; the seven-scenario IQ1_M rerun again matched the ten verifier/MTP calls and owner events with 7.84 GiB minimum host availability. The focused Q2_0 PLE/memory set passed 5/5 and integration Python unittest discovery passed 75/75 on this binary. See the [session graph instrumentation report](../../bench/results/2026-10-11-phase3-graph-session-owner-check/README.md).

An actual cgroup-v2 [admission check](../../bench/results/2026-10-10-phase3-cgroup-admission/README.md)
placed the supervisor in a 1 GiB systemd user scope. It saw only 1.0 GiB of
effective cgroup availability despite 24.6 GiB host availability and aborted
before launching its child. This validates the cgroup-aware prelaunch guard,
not behavior under active cgroup pressure. The owner summarizer also now reports
concurrent observed allocation-request peaks across owners per device; it still
excludes uninstrumented allocations and is not the physical memory authority.

The [async-pool transfer screen](../../bench/results/2026-10-10-phase3-async-pool/README.md) tested a transient 64 MiB allocation/copy/kernel/free sequence against pinned-copy, mapped-host and sequential-managed paths. All checksums passed; the pool returned to zero live bytes after reserving 64 MiB. Its 14.93 ms median was slower than the persistent-copy path at 13.16 ms, so no allocation-path change is proposed. This fixed-order single run lacks paired clock and energy evidence.

The [scope-accounted cgroup pressure repeat](../../bench/results/2026-10-11-phase3-cgroup-scope-accounting/README.md) now samples the actual transient `run-*.scope` leaf: a 4 GiB touched allocation peaked at 4.01 GiB under a 6 GiB cap, with 21.39 GiB minimum host availability. The initial sampler summary included its uncapped session ancestor and is retained but excluded. This fixes host-cgroup attribution for the bounded probe; it does not run Strata inside that scope.

The follow-up [bounded cgroup pressure probe](../../bench/results/2026-10-10-phase3-cgroup-pressure/README.md)
held 4 GiB in a 6 GiB transient user scope and retained at least 23.8 GB host
availability. It did not run Strata inside the scope, and the sampler did not
capture the scope's own `memory.current`; active cgroup-limited admission and
recovery were then tested separately in that report: 12/16 GiB scopes safely aborted at the cgroup floor, while the same 512-token/one-output workload passed under 20/24 GiB scopes. The first PLE rerun still
failed preflight on the pack's native-key/BF16-value representation; the
artifact-aware follow-up now passes the real three-token block check, including
the native Q2_0 projection and exact source-block reconstruction. The reader
also matches 64 sampled PLE table rows bitwise; see the [artifact-aware PLE
report](../../bench/results/2026-10-10-phase3-q2-ple-artifact-aware/README.md).

The repeated [cache-cap × context screen](../../bench/results/2026-10-11-phase3-cache-context-repeated-fixed/README.md) ran three measured requests per randomized cell after warmup. All four combinations completed above the six-GiB floor (minimum 8.34 GiB); increasing the cache from 3,903 to 6,519 actual slots requested another 4.96 GiB of device backing and reduced the minimum host availability by about 4.8 GiB. Doubling context raised the instrumented session payload by 108 MiB. Timing is descriptive only because each cell used one process, dynamic clocks and a short prompt. The reusable screen harness has three offline config tests.

The [requested cache × context screen](../../bench/results/2026-10-09-phase3-cache-context-matrix/README.md)
ran a randomized 2×2 configuration matrix on Orin with one short API workload
per process. All cells passed workload completion and stayed above the six-GiB
physical-memory floor. The requested cache values selected identical actual
slot counts across contexts (3903 for request 3000; 6519 for request 5000),
showing the CLI values are lower bounds under this device's sizing policy. The
screen is admission evidence only: one measured request per cell cannot support
latency comparisons or a cache/context performance conclusion.

The [prefill × workspace screen](../../bench/results/2026-10-09-phase3-prefill-workspace-matrix/README.md)
compares 64- and 512-token chunks with cache-borrowed versus separately owned
prompt buffers. Automatic cache sizing emitted the expected 3 GiB VRAM slack
and MTP-bind holds in every cell, plus separate 202 MiB and 500 MiB
prefill-workspace holds for owned buffers. All four short API requests completed;
minimum system availability was 7.47 GiB. This is a resource/admission screen,
not a performance comparison or a test of late allocation failure.

The [larger owned-chunk follow-up](../../bench/results/2026-10-09-phase3-prefill-workspace-large-chunks/README.md)
extended the resource screen to 1024 and 2048 tokens. The largest cell emitted
a 1520 MiB prefill hold, auto-sized 6338 expert slots and retained at least
8.03 GiB system availability. Its 172-token prompt did not fill the configured
chunk. A separate exact 2048-token prompt completed against the owned 2048-token
chunk with 8.02 GiB minimum availability; late allocation failure remains
untested.

The [VMM owner trace](../../bench/results/2026-10-09-vmm-segment-owner-trace/README.md)
records segmented-cache shrink/regrow and shared-chunk transfer lifetimes.
The `vmm_test` transfer moved two 2 MiB handles between ranges while preserving
contents; the trace balanced nine chunk allocations with nine releases and
reports map/unmap transitions separately from backing bytes.

The [VMM address-range follow-up](../../bench/results/2026-10-10-phase3-vmm-va-reservation/README.md)
now traces virtual address reserve/release separately from physical handles.
The Orin `vmm_test` and segmented-cache lifecycle test passed with tracing on;
both balanced two address-range lifetimes and ended with zero live address or
physical bytes. In `vmm_test`, virtual-range peak was 27.3 MB while the unique
physical-handle request peak was 18.9 MB; these are separate dimensions, not
additive memory totals.

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

Fresh Orin checks: all 54 integration harness tests, 15 Jetson setup tests, 312
selected mock API tests, the pinned shared-memory budget test and six selected
branch CPU/core tests pass. The six earlier targeted Phase 3 CTests (VMM transfer,
segmented cache, pinned fallback/shared memory, shared budget and published
prefix) pass. On Oct 10, a fresh supervised run of 10 Phase 3 CTests, including
memory refusal, platform memory, and the PLE table-reader selftest, passed with
27.94 GiB minimum availability. After a one-job build of missing targets, 108 of 112 CTests passed
when excluding the unavailable-model PLE fixture; two tests were skipped and
`expert_parity`/`pool_test` could not read their separate `pack/full/experts.bin`
fixture. On Oct 10 the pinned Q2_0 shards were downloaded under `~/models`, and
a standalone native pack was generated successfully. The first fixture-free
PLE oracle run reached the pack but rejected its native Q2_0 key and BF16 PLE
value layout; the later [artifact-aware PLE check](../../bench/results/2026-10-10-phase3-q2-ple-artifact-aware/README.md)
adapts those exact source representations and passes. The initial failure and
Phase 3 tests remain recorded in the [Q2_0 PLE attempt](../../bench/results/2026-10-10-phase3-q2-ple-test/README.md). The existing GPU conversation-snapshot test also freshly
passes 3901 synthetic state checks; this is not accepted-prefix commit parity. Both control binaries built as native ARM64 Release with
CUDA 12.6.68 and embedded SM87 images. Both source GGUF shards and all 31 MTP
source tensors were independently rehashed against pinned digests. Prepared
runtime packs have new identity hashes, not new numerical qualification.

A separate [Q2_0 runtime admission smoke](../../bench/results/2026-10-10-phase3-q2-runtime-smoke/README.md)
did not reach prefill: the available 48×256 expert profile is incompatible
with Q2_0's 48×512 layout, and the generic MTP converter rejects this artifact's
GGML type-42 tensor. A separate no-MTP one-token native Q2_0 CLI smoke then
completed at a fixed 5,000 expert slots, with 15.71 GiB minimum physical
availability. Its full expert ranking is deterministic fill order, not
routing-derived. The existing Q2_0 MTP runtime also loaded and bound for a
one-token request (977 MiB reported for MTP, 14.88 GiB minimum host
availability), but the token limit left zero draft rounds. This is admission
evidence only; draft execution/acceptance, quality, service behavior and
performance on Q2_0 remain unqualified.
With this exact one-token cell under cgroup limits, 20 GiB completed with
7.98 GiB minimum effective availability; 16 GiB was safely aborted during
prefill when sampled effective availability reached 5.45 GiB, while host
availability remained 15.80 GiB. These are cell-specific admission bounds.
The MTP-loaded one-token cell also completed in a 20-GiB scope with 9.81 GiB
minimum effective and 15.00 GiB minimum host availability; separate-run scope
peaks are not used to infer MTP's incremental RAM cost. Under 16 GiB, the same
MTP-loaded cell reached the draft layer/head load and was supervisor-aborted
during prefill at 5.72 GiB effective availability; host availability remained
15.04 GiB. This is the effective-cgroup admission guard, not an engine/OOM
failure. An opt-in one-token owner trace on Q2_0 MTP balanced 262 allocation
and free events and ended with zero observed live bytes; the tracked concurrent
CUDA requested-byte peak was 7,205,736,400 bytes, with 353,894,400 bytes of
pageable expert-stage host backing. MTP state/scratch requests peaked at
12,977,872 bytes, distinct from its reported 1,024,377,180-byte payload.
A root-readable NVMap client trace, calibrated against a live 512 MiB allocation, measured 83,427,328 bytes of net process-owner growth across ten graph-instantiation calls in three IQ1_M service startups. This interval-specific result does not price other graph or non-NVMap allocations; see the [graph memory report](../../bench/results/2026-10-11-phase3-graph-nvmap-calibration/README.md).
The [MTP weight-owner follow-up](../../bench/results/2026-10-10-phase3-mtp-weight-owners/README.md)
repeats this Q2_0 cell with tracing for dense and routed-expert blobs plus the
draft-head subset: it emits the same token ID 32, and 266 allocations and frees
balance. The observed base weights
total 785.7 MiB and the subset head/vocabulary copies add 178.8 MiB of CUDA
requested payload; shared drafters emit no duplicate base-weight allocations.
The [verifier mapped-host follow-up](../../bench/results/2026-10-10-phase3-verifier-mapped-owner/README.md)
adds host staging registrations/frees to the same Q2_0 load/bind check; all 282
owner allocations and frees balance, including a 495,480-byte mapped-host peak.
With the optional [verifier trace ring](../../bench/results/2026-10-10-phase3-verifier-trace-owner/README.md)
enabled, 283 pairs balance; adding its mapped buffer to verifier teardown closes
the diagnostic-buffer lifetime too. Both runs end with zero observed live bytes.
At the same 5,000 cache slots, configured 8K and 16K contexts also admitted
the one-token/512-input smoke with 15.65/15.70 GiB minimum host availability;
these do not represent long-context ingestion or quality tests.
The [Q2_0 PLE direct/mmap screen](../../bench/results/2026-10-10-phase3-q2-ple-io-screen/README.md)
ran three balanced pairs with identical output token IDs and 15.96 GiB minimum
host availability. The CLI prompt median favored mmap by 3.88%, but the order
was not randomized, clocks were dynamic, no state hashes were collected, and
the engine PLE counter was only 0.2–0.3 ms. This remains descriptive screening;
neither table path is promoted.

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

The [current candidate profile](../../bench/results/2026-10-10-phase4-candidate-request-profile/README.md)
repeats the same pp512+tg64 request shape on the current candidate with the
six-GiB supervisor. Q6_K→FP16 dequantization again ranks first in the measured
window (2.557 s summed over 1,024 instances, 21.52% of summed kernel duration),
followed by spin waits. Approximate request-window alignment, concurrent
streams, profiler overhead and dynamic clocks still prevent critical-path or
speedup conclusions. This begins Phase 4 attribution; it does not authorize a
kernel or dispatch change.



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
