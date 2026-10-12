# Integration status

Updated: 2026-10-13. Phases 1 and 2 are complete with their supported, failed,
unsupported and untested scopes recorded. Phase 3 memory ownership and transfer
work is active; its admission screens and focused owner tests are recorded below,
with broader pressure and transfer gates still open. No NInfer execution
component has been promoted into Strata.

The focused [SessionLoopScratch owner check](../../bench/results/2026-10-11-phase3-session-loop-scratch-owner-retest/README.md) traces a 65,536-byte mapped/pinned host allocation and one matching free; repeated teardown is idempotent. The serial [Phase 3 owner/PLE regression](../../bench/results/2026-10-11-phase3-session-owner-ctest/README.md) passed 23/23. CUDA relink and maestro1 HIP compile identities are retained. The validated native pack bypasses the legacy session-loop route; broader unique-backing and graph accounting remain open.

The fresh [Q2_0 PLE and owner/graph regression](../../bench/results/2026-10-11-phase3-followup-fresh/README.md) passed the artifact-aware PLE oracle and all 19 selected ownership/graph tests on the current candidate. The seven PLE stages passed for three tokens (worst relative L1 `1.148e-7`); CTest passed 19/19 with 24.52 GiB minimum host availability. This reconfirms selected contracts only; graph-pool pricing, broad pressure behavior and remaining transfer/admission cells remain open.

The [2026-10-12 Q2_0 PLE follow-up](../../bench/results/2026-10-12-phase3-ple-followup/README.md) repeated the current-binary oracle and selected owner/graph checks: all seven PLE stages passed for three tokens (worst relative L1 `1.148e-7`), CTest passed 19/19, and integration Python discovery passed 111/111. Minimum host availability was 24.66 GiB for PLE and 24.53 GiB for CTest under the six-GiB supervisor. This refreshes contract evidence only; Phase 3 pressure, graph-backing, and transfer/admission gates remain open.

A fresh [Q2_0 PLE and Phase 3 regression refresh](../../bench/results/2026-10-12-phase3-ple-refresh/README.md) passed the artifact-aware PLE oracle (all seven stages, three tokens, worst relative L1 `1.148e-7`), the selected 19/19 ownership/graph CTests, and integration Python discovery (113/113). Minimum host availability was 24.58, 24.48 and 24.54 GiB, respectively, under the six-GiB supervisor. This reconfirms selected contracts on the current candidate; broad pressure recovery, complete physical backing and transfer/performance qualification remain open.

The fresh [64K configured-context Q2_0 cache/owner screen](../../bench/results/2026-10-12-phase3-q2-owner-64k/README.md) completed the same 512-token prompt plus one output token at 3,000 and 5,000 cache slots. Minimum host `MemAvailable` was 16.94 and 14.36 GiB. Both unique requested-allocation ledgers balanced 278/278 events with zero requested bytes live at exit. Session backing stayed at 1,856,067,072 bytes; the expert cache grew from 4,147,200,000 to 6,912,000,000 requested bytes, exactly matching the device-peak increase. Pageable staging stayed at 353,894,400 requested host bytes. The 5,000-slot point also passed under 24- and 18-GiB cgroup caps with 12.98 and 6.67 GiB minimum effective availability, respectively; both ledgers balanced and neither scope recorded OOM kills. The explicit 3,072 MiB workspace reserve was retained; these runs emit no auto-cache reservation metadata. This sequential screen is configured-reservation admission evidence, not randomized performance, 64K prompt ingestion, full physical accounting or a general capacity limit.

Three fresh Q2_0 processes passed the [injected automatic expert-cache refusal/retry](../../bench/results/2026-10-12-phase3-q2-cache-failure-retry/README.md) at a 64K context reservation. Retry capacities were 8,082, 6,626 and 8,043 slots as available memory varied; each completed the 512/1 request with output token 32 and balanced 278 allocation/free events to zero live requested bytes. Minimum host availability was 10.27, 12.33 and 10.48 GiB, with no OOM kills. A fourth run passed the same injected retry in a `MemoryMax=24G` scope at 7,967 slots, with 12.93 GiB minimum effective cgroup headroom. This qualifies the simulated retry path for this workload, not physical CUDA OOM recovery or a general capacity threshold.

The fresh [Q2_0 auto-cache reservation reconciliation](../../bench/results/2026-10-12-phase3-q2-auto-reservation/README.md) completed a 512-token/one-output request with 10,408 actual cache slots and generated token 32. The emitted 500 MiB prefill hold exceeded that owner's 333.8 MiB unique requested-allocation peak; the distinct 3,072 MiB workspace slack remained reserved. The six-GiB supervisor measured 8.40 GiB minimum host availability and no OOM events. This reconciles one planned hold with one actual owner peak; graph/driver backing and other configurations remain outside the comparison.

The same report now includes a randomized three-per-cell auto-cache × configured-context screen. All six 512/1 requests selected token 32 and stayed above the six-GiB floor (7.32 GiB minimum). Median unique requested device peaks differed by 44.3 MiB between 8K and 64K contexts, while session allocation grew 1.41 GiB and median cache allocation fell 1.37 GiB. The 500 MiB prefill hold and 3,072 MiB workspace slack stayed fixed; the measured prefill-owner peak was 333.8 MiB in every process. This supports the configured-reservation accounting for these cells, not physical backing or a general headroom guarantee.

A fresh [Q2_0 8K prefill cancellation/recovery run](../../bench/results/2026-10-13-phase3-q2-cancel-8k/README.md) disconnected after 1.014 seconds with 512/8,192 prompt tokens read, then returned `Hello Orin!` through the same live service. Under a 28-GiB cgroup cap, minimum host/effective availability was 17.524 GiB and OOM counters stayed zero. The 304/303 owner ledger left only the 1,485,606,400-byte service-lifetime weight arena requested-live. Runtime metrics show an effective verifier window of four (`spec:4`, `mtp_max:2`) because default suffix drafting expands CLI `--spec 2`; the launch setting and effective value are both recorded. This adds one actual 8K cancellation cell, not broad recovery or capacity qualification; Phase 3 remains open.

The same exact [8K cancellation/recovery cell at a 22-GiB cap](../../bench/results/2026-10-13-phase3-q2-cancel-8k-22G/README.md) also passed: cancellation followed 512/8,192 prompt tokens and the same service returned `Hello Orin!`. Minimum host availability was 17.510 GiB and effective cgroup headroom was 13.157 GiB, with zero OOM kills. Requested owner events again ended with only the service-lifetime weight arena live. This is a repeat at another scope ceiling, not a general capacity bound.

A fresh [Q2_0 cancellation/recovery run under a 22-GiB cgroup cap](../../bench/results/2026-10-12-phase3-q2-cancel-recovery-22G/README.md) disconnected during a 2,048-token prompt after 512 tokens were read, then recovered with `Hello Orin!` in the same service. The supervisor measured 9.35 GiB minimum effective cgroup headroom, above the six-GiB guard, with no OOM kills. The owner trace had 304 allocations and 303 frees; all transient/request owners were released, leaving only the expected 1,485,606,400-byte service-lifetime weight arena. This repeats one bounded pressure/cancellation cell and does not establish general recovery or capacity behavior.

The Q2_0 [32K request plus same-process recovery check](../../bench/results/2026-10-12-phase3-q2-long-request-recovery/README.md) completed a 32,768-token prompt and one output token, then served a 21-token follow-up with four output tokens in the same engine process at both 3,000 and 5,000 cache slots. Both requests passed under a 20-GiB cap and emitted the same token IDs. Minimum host availability was 16.38/13.89 GiB and effective headroom 8.86/8.17 GiB. Each 304/303 owner ledger left only the 1,485,606,400-byte service-lifetime weight arena, confirming request/session owners released after the long request and recovery. Endpoint state differed across cache capacities, including on the follow-up; no same-capacity cold control was added for that short prompt. This is one Q2_0 workload/context and cache comparison, not a quality, timing or broad recovery claim.

The [actual 32K prompt cache/pressure screen](../../bench/results/2026-10-12-phase3-q2-actual32k-22G/README.md) completed the same exact prompt at 3,000 and 5,000 slots under separate 22-GiB cgroup caps. Both generated token ID 32 and passed with at least 9.92 GiB minimum effective headroom and no OOM kills. Requested device peaks were 7,021,083,648 and 9,785,883,648 bytes, with 304/303 owner events in both runs and only the service-lifetime weight arena live at exit. Five persistent-state fields differ; 35 of 36 per-layer GDN hashes differ between cache sizes despite matching final token IDs. Timing is excluded and the state mismatch remains unresolved. This is actual long-prompt admission evidence, not cache-capacity, quality, or performance qualification. The follow-up [32K prompt at a 64K context reservation](../../bench/results/2026-10-12-phase3-q2-actual32k-context64k/README.md) passed at both cache sizes under a 22-GiB scope: minimum effective headroom was 7.47 GiB at 3,000 slots and 9.68 GiB at 5,000. Both balanced 304/303 owner events and left only the service-lifetime weights live. As before, output token IDs matched but persistent state differed across cache sizes (five final fields and 35/37 GDN hashes). The 3,000-slot cell passed only 1.47 GiB above the supervisor floor. This adds an actual-prompt/context interaction point, not a capacity limit or performance/quality result.

The [18-GiB pressure probe](../../bench/results/2026-10-12-phase3-q2-actual32k-context64k-18G/README.md) repeated the 3,000-slot/32K-prompt/64K-context cell under the same six-GiB supervisor and was stopped after the prompt trace advanced from chunk offset 0 to 512, at 5.927 GiB effective cgroup headroom. Host availability remained 16.431 GiB and the cgroup recorded no OOM kills. The matched 22-GiB run passed at 7.47 GiB effective headroom. This narrows the pass/abort bracket for this exact workload only; it is not a general RAM requirement or supported-capacity threshold.

A fresh [19-GiB Q2_0 32K-prompt pass](../../bench/results/2026-10-12-phase3-q2-actual32k-context64k-19G/README.md) used the same 3,000-slot cache, 64K context, prompt and binary as the 18-GiB pressure abort and 20-GiB pass. It completed with 6.98 GiB minimum effective scope headroom and 16.42 GiB host availability; leaf cgroup OOM events were zero. The 304/303 owner trace left only the service-lifetime weight arena, and the final fingerprint/all 36 GDN hashes matched the 20-GiB run. This is an additional point for this boot/configuration only; cgroup/page-cache starting state prevents a general capacity threshold.

The [20-GiB 5,000-slot repeat](../../bench/results/2026-10-12-phase3-q2-actual32k-context64k-20G-cache5000/README.md) completed the same exact prompt with 13.87 GiB minimum host availability and 9.38 GiB minimum effective cgroup availability. It generated token ID 32 and matched the 22-GiB/5,000-slot persistent fingerprint and all 36 per-layer GDN hashes. Owner observations were 304 allocations/303 frees, with only the service-lifetime weight arena left live; cgroup OOM counters stayed zero. This confirms state across these two scope caps for this cell, not cap monotonicity, cache-capacity equivalence, or a general memory threshold.

The [prefill-256 repeat](../../bench/results/2026-10-12-phase3-q2-actual32k-context64k-20G-cache5000-prefill256/README.md) then completed the same 32K prompt at the same 64K context, 5,000 slots and 20-GiB cap. It passed at 8.65 GiB minimum effective headroom and 14.00 GiB host availability with no OOM events. Requested device peak was 80.5 MiB lower and prefill-owner peak 80.4 MiB lower than the sequential 512 control, but effective headroom was 0.73 GiB lower due to differing scope/page-cache charges. Both emitted token ID 32 while final state and all 36 GDN hashes differed, consistent with the known chunk-dependent state issue. These single sequential cells neither quantify a chunk performance effect nor determine which state is more accurate.

The matching [18-GiB / prefill-256 repeat](../../bench/results/2026-10-12-phase3-q2-actual32k-context64k-18G-cache5000-prefill256/README.md) also completed and generated token ID 32. It passed at 6.49 GiB minimum effective headroom (0.49 GiB above the guard) and 13.86 GiB host availability, with zero OOM events. All 36 GDN hashes and the final fingerprint match the 20-GiB / prefill-256 run. The earlier 18-GiB/3,000-slot/prefill-512 abort is not a directly matched control; cache, chunk and cgroup charges differ, so this is no general or monotonic capacity threshold.

Three NVMap IOVMM traces during the matching [actual 32K / prefill-512 request](../../bench/results/2026-10-12-phase3-q2-actual32k-graph-nvmap/README.md) each observed four successful verifier graph instantiations and the same 71,983,104-byte process-owner increase from immediately before the first to immediately after the fourth. All three requests passed, generated token ID 32 and matched the final persistent fingerprint and all 36 GDN hashes. The interval includes adjacent synchronous allocations, so it is a repeatable configuration-specific bracket, not graph executable size or total physical memory. Other graph paths and a graph-disabled differential remain open.

A [float32 state-dump comparison](../../bench/results/2026-10-12-phase3-q2-actual32k-state-numeric/README.md) now quantifies the cache-capacity-associated difference for that exact long prompt: 3,000 versus 5,000 slots emitted the same token ID but differed in five final state fields. Their 36-layer GDN dumps differed at 94.32% of values, with 4.687% whole-state relative L2; material drift first appears at GDN layer 3 and grows to 11.80% relative L2 in layer 23. The per-layer profile is diagnostic, not an accuracy oracle or causal proof. Same-configuration GDN hashes matched earlier independent pressure-cap repeats; task-level quality and root cause remain open, and no cache default changed.

The [20-GiB repeat](../../bench/results/2026-10-12-phase3-q2-actual32k-context64k-20G/README.md) completed the same full prompt at 7.930 GiB minimum effective cgroup headroom, generated token ID 32, and matched the 22-GiB run's final fingerprint and all 36 GDN layer fingerprints. It also had no OOM events. The 18-GiB abort, 20-GiB pass and 22-GiB pass are not monotonic in configured cap because per-run cgroup/page-cache charges differed; do not infer a minimum from these points.

The `run_control.py` result now records minimum effective admission headroom separately from host `MemAvailable`, while retaining the detailed ancestor samples. A real 7-GiB cgroup calibration passed and recorded 24.596 GiB minimum host availability separately from 6.991 GiB effective headroom. Focused supervisor tests and full integration Python discovery pass 12/12 and 118/118. Earlier raw results remain reproducible from `memory.jsonl`; new runs retain the additional field in their terminal records.

The prior [MTP cancellation state-parity run](../../bench/results/2026-10-11-phase5-mtp-cancel-state-parity-ignore-eos-rerun/result.json) with a fixed 5,000-slot cache had matching token IDs but state mismatches at accepted lengths 48 and 52. Earlier repeat and numeric-dump runs inherited a config override of `0.5` and are invalid as zero-CPU-prefill controls. A current-harness [fixed-cache follow-up](../../bench/results/2026-10-12-phase5-mtp-cancel-state-parity-fixed-cache/README.md) made the generated engine environment explicit and compared three fresh references at both 3,000 and 5,000 slots. Cancellation, same-process recovery, and every persistent-state fingerprint at L=48 and L=52 matched in all six reference comparisons; minimum host availability was 13.32 and 8.34 GiB. The earlier 5,000-slot mismatch did not reproduce and remains unexplained. This closes only the exercised short integer-list cancellation cell; broader Phase 5 transaction and termination cases remain open, and no Phase 3 performance evidence is implied.

After the Q6_K opt-in kernel change, the same [Q2_0 PLE and ownership regression](../../bench/results/2026-10-11-phase3-current-kernel-ple-regression/README.md) passed again on the current binary: all seven PLE stages for three tokens (worst relative L1 `1.148e-7`), 19/19 selected CTests and 103/103 integration Python tests. Minimum host availability was 27.21 GiB. The new kernel environment variable was unset, confirming the default route retains the established PLE behavior.

The opt-in [Q6_K-to-FP16 warp-layout candidate](../../bench/results/2026-10-11-phase4-q6-warp-layout/README.md) is bit-identical on all five profiled real matrix shapes and cuts weighted isolated conversion time by about 49% in three processes. A three-pair held-out 2,048/128 API screen matched output, draft counts and cache slots, with request-time deltas −4.13%, −6.11% and −6.08%; an eight-token accepted-prefix trace matched all five commit boundaries and full state hashes. The CUDA kernel, full HIP build and full SYCL build pass. This remains a one-workload screen without task-quality or multi-context confirmation; default dispatch is unchanged.

A seven-pair [cross-length 8K-context confirmation](../../bench/results/2026-10-12-phase4-q6-cross-length-context8k/README.md) extended that timing check to exact 512/64 and 2,048/128 prompts. All 28 measured requests passed exact token-count/fresh-prefill checks; each paired output and draft/accept count matched, with 3,903 actual cache slots in every process. Candidate request medians were 6.73% lower (95% paired bootstrap interval −8.05% to −5.26%) for 512/64 and 5.98% lower (−7.93% to −5.35%) for 2,048/128. Prompt deltas were −8.54% and −6.72%; decode was +0.22% and −0.10%, respectively. Minimum host availability was 13.014 GiB. EMC stayed at 3,199 MHz; sampled GPU clocks varied 306–1,300.5 MHz and CPU clocks 729.6–2,201.6 MHz. The timing result is specific to these cells, remains opt-in, and adds no task-quality or state-parity claim; the separate same-context accepted-prefix check is retained as independent correctness evidence.

The [1,024-token vision admission smoke](../../bench/results/2026-10-11-phase3-vision-1024/README.md) completed a 2,048×2,048 image request with 1,049 prompt tokens under the six-GiB supervisor; minimum host availability was 7.005 GiB. A supervised interposed repeat attributed 989.5 MiB peak CUDA runtime requests to the vision process and returned its tracked bytes to zero at exit; the engine peak remains a mixed service/request scope. A fresh [same-fixture 1,024-token repeat](../../bench/results/2026-10-12-phase3-vision-1024/README.md) passed HTTP 200 with 1,049 prompt and 48 completion tokens. The follow-up interposed both processes: vision runtime requests peaked at 1,037,613,696 bytes and returned to zero; the engine runtime-request peak was 18,755,110,608 bytes, while its separate owner ledger retained only the 1,475,120,640-byte service-lifetime weight arena. Whole-board minimum availability was 7,624,368,128 bytes (7.10 GiB), above the six-GiB floor. The interposer and owner ledger have different, potentially overlapping coverage and are not physical totals; wider image-size, image-complexity and memory-envelope qualification remain open.
The model-free [CUDA memory primitive self-test](../../bench/results/2026-10-11-phase3-cuda-memory-selftest/README.md) passed managed sequential ownership, registered-host mapping, 512 CPU/GPU doorbell exchanges and CUDA VMM mapping at the 2-MiB granularity. This validates primitive contracts on Orin, not any production model-buffer transfer mode or its cost.
Its stream-ordered pool follow-up also passed a `cudaMallocAsync`/use/`cudaFreeAsync` lifecycle and returned the default pool to its zero-byte reserved baseline after trimming. This demonstrates runtime support and cleanup only; allocation latency and production-buffer effect remain unmeasured.

The [WeightTable dense-arena owner check](../../bench/results/2026-10-11-phase3-weight-arena-owner/README.md) adds opt-in allocation/free events for the main CUDA arena. A trace-on and trace-off Q2_0 one-token control both passed; the traced ledger balanced 278 allocations/frees, observed a 1,485,606,400-byte arena, and ended with zero live requested bytes. Minimum host availability was 18.45 GiB (trace-on) and 18.49 GiB (trace-off). This prices one previously unlabelled main-route allocation request; graph-pool and other uninstrumented CUDA allocations remain outside the ledger.
The current candidate also passed the selected 19-test Phase 3 owner/graph regression under the six-GiB supervisor (24.41 GiB minimum availability); this validates the listed software contracts, not graph-pool pricing or broad pressure behavior.

The three-startup [Q2_0 32K/spec4 NVMap confirmation](../../bench/results/2026-10-11-phase3-q2-graph-context32k-spec4-confirm3/README.md) repeated the same 48,709,632-byte stable process-owner increase between 20-sample pre-graph and post-graph NVMap plateaus in every run. Each startup completed the 31/24-token request, matched all three graph instantiations to owner events, and stayed above 20.7 GiB `MemAvailable`. This strengthens backing attribution for one graph sequence; adjacent synchronous allocations remain included, and legacy graph paths and non-NVMap allocations remain unpriced. A same-day [32K-versus-64K context graph comparison](../../bench/results/2026-10-12-phase3-q2-graph-context64k-spec4/README.md) then repeated three processes at each context on the same binary. All six matched three runtime graph calls to three owner events and passed with at least 19.36 GiB host availability. Graph-interval NVMap growth was identical at 48,709,632 bytes in all six. The 64K pre-graph baseline rose by 864,747,520 bytes; session-state and verifier-owner requested peaks rose by 864,550,912 and 196,608 bytes, exactly accounting for the measured NVMap delta. This attributes the context-related backing change for this configuration only; no graph timing benefit is claimed.

A randomized three-pair [Q2_0 spec2/spec4 graph-backing screen](../../bench/results/2026-10-11-phase3-q2-graph-spec-interaction3/README.md) held the 4K context, 256-slot cache, 31-token prompt and 24-token output constant. The 20-sample stable-to-stable NVMap deltas repeated at 71,983,104 bytes for spec2 and 48,709,632 bytes for spec4 in all three fresh-process pairs; both arms returned identical text. Minimum host availability was 21.18 GiB and minimum cgroup headroom was 16.76 GiB. This is a repeatable difference for these exact graph-capture sequences, with adjacent synchronous allocations included; it does not price graph executables or support a general per-window memory rule.

The calibrated [public Driver allocation trace](../../bench/results/2026-10-11-phase3-q2-graph-driver-traceall/README.md) observed the same three Q2_0 graph calls but no `cuMemAlloc_v2`, managed allocation or free events through its wrapped public Driver symbols. A separate 2 MiB calibration was visible. This rules out those wrapped calls as an explanation for the 48.71 MB increase, while leaving runtime-private allocation APIs and driver-private graph storage outside scope; no executable size is inferred.

The Q2_0 [cgroup-limited cancellation/recovery check](../../bench/results/2026-10-11-phase3-q2-cgroup-cancel-recovery/README.md) now has three independent service startups combining memory-cap and disconnect handling. All passed under a 16 GiB cap; minimum effective headroom ranged from 7.01 to 13.98 GiB as page-cache charges changed across sequential runs. Each client disconnected during the first 512-token prefill chunk of a 2,048-token request, and each short same-process recovery passed. Allocations were released except for the service-lifetime weight arena. Prefill did not stop until the active chunk completed; the coldest startup had only about 1 GiB of floor margin, so this remains one pressure configuration rather than broad recovery qualification.
The supervisor now supports opt-in read-only CPU/GPU/EMC rate sampling alongside memory samples. A current Q2_0 one-token check captured 21 samples (GPU 306–1,122 MHz; EMC 3,199 MHz) above the six-GiB floor; the integration Python suite passed 98/98. This does not repair missing clocks in earlier reports or provide thermal/energy qualification; see the [clock-observation check](../../bench/results/2026-10-11-phase3-q2-current-clock-observation/README.md).

A same-binary [Q2_0 prefill-chunk × cgroup admission screen](../../bench/results/2026-10-11-phase3-q2-prefill-cgroup-screen/README.md) found that chunk 32 admitted more cache at some lower caps, but the 8/10/12-GiB screen cells reached the six-GiB effective-availability guard; the 12-GiB chunk-512 and both 16-GiB cells passed. A three-pair [12-GiB follow-up](../../bench/results/2026-10-11-phase3-q2-prefill-cgroup-paired3/README.md) then passed 2/3 chunk-32 processes and 3/3 chunk-512 processes, while actual slots varied widely in both arms. These admission-only data do not support a chunk-specific rule or timing claim. The 8-GiB chunk-512 result from the earlier screen remains a separate no-cache/speculation failure, not a successful capacity point.

The current Q2_0 binary also passed one-token configured-context admission checks at 4K/8K/16K/32K/64K with 3,000 actual cache slots. Session requested backing scaled from 235,034,112 to 1,856,067,072 bytes; all five owner ledgers balanced 278/278 and the minimum host availability was 17.12 GiB. See the [context screen](../../bench/results/2026-10-11-phase3-q2-context-admission-current/README.md). These are startup/admission checks only; long-context ingestion, quality, concurrency and graph-pool pricing remain open.

| Phase | State | Evidence / next gate |
| --- | --- | --- |
| 0 — Repository and import | Complete | Pinned source/evidence manifest, source mapping, plan, offline planner checks |
| 1 — Same-day controls | Complete | Four same-day paired API blocks; exact workloads/artifacts; protocol and baseline checks; capability matrix records limits; expanded HIP/SYCL builds compile |
| 2 — Operator/state contracts | Complete | Ownership review, incompatible projection-profile rejection, independent RMS/IQ4_NL/Q6_K oracles, GDN prefix checks, default spec1 regression and post-fix spec1/spec4 token plus nine-field persistent-state parity recorded; native/HIP/SYCL build evidence and eleven selector tests pass; no NInfer execution component promoted |
| 3 — Memory and transfers | In progress | Opt-in trace covers ordinary ExpertCache, CUDA segmented-cache mapped VMM handles, shared CUDA VMM physical-chunk lifetimes and per-range map/unmap transitions, primary SessionState, verifier, prefill, MTP and separate pageable/pinned expert-stage host owners, including an opt-in layer-dump pinned-host buffer whose allocation/free balance was verified on an early-return path; successful dump execution remains unsupported with the native speculative verifier because it requires the token graph that dumping disables; Orin shrink/regrow lifecycle test preserved slot data and matched 41 allocate/free events; injected pinned-registration failures fell back to working pageable copies under the six-GiB supervisor; one injected expert-stage `cudaHostAlloc` refusal produced an observed pageable owner allocation/free, while five sibling pinned buffers also balanced at teardown; the 10 instrumented allocation/free pairs in this request matched, with zero observed live bytes at teardown; the request and forced-pageable control generated one token above the memory floor (targeted test minimum 7.58 GiB); two randomized fixed-cache 4K staging screens matched tokens and nine state fields; the trace-corrected clocked repeat found +0.10% median prompt time and variable decode results with dynamic CPU/GPU clocks; minimum availability was 8.04 GiB; a randomized 2×2 requested-cache/context screen completed all cells above the six-GiB floor, with actual slots 3903/6519; a 2×2 prefill-chunk/borrowed-vs-owned screen observed separate 202/500 MiB workspace holds and remained above 7.47 GiB; owned chunk 1024/2048 follow-up reserved up to 1520 MiB and remained above 7.72 GiB; an exact 2048-token prompt completed against the 2048 owned chunk with 8.02 GiB minimum availability; the Oct 10 focused 10-test Phase 3 CTest set passed with 23.8 GB minimum availability during a separate bounded 4 GiB cgroup allocation; a fresh Oct 10 ten-test PLE/memory rerun passed with 27.80 GiB minimum availability; 12 and 16 GiB cgroup-limited IQ1_M runs reached prefill then were supervisor-aborted at the effective 6 GiB floor (host availability remained 22.2 and 15.6 GiB); the same request passed under 20/24 GiB caps with 9.58/8.84 GiB minimum effective availability and in a fresh uncapped process at 7.62 GiB; simulated expert-cache allocation failure retried at 4,753 slots and completed; late prefill workspace injection and post-warmup CUDA allocation failure each caused a supervised engine restart and successful one-token service recovery; seven randomized fixed-cache mapped/pread pairs matched all tokens and nine persistent-state fields, with mapped median total request time 4.14% lower (bootstrap median interval −5.57% to −4.02%) and at least 8.01 GiB available; a separate seven-pair 3,903-slot mapped/pread run collected temporary systemd-scope `io.stat` counters, matched tokens and state, and observed a −5.08% mapped request delta plus −1.010 GB median scoped read difference; the pread arms consumed zero prefetched blobs and had zero reported decode wait, so this cell did not measure a request-path pread stall; the artifact-aware Q2_0 PLE oracle passes all seven stages for real layer-1 weights and table rows (three-token block, synthetic hidden/history), reassembles the native key byte-identically, and matches the native projection to the independent decoded path; a separate 64-row real-table reader check is bit-identical; captured graph arm completed with state fingerprints and 13.19 GiB minimum availability, but eager comparison is unsupported because `session_token` lacks the CPU expert-pool hook and `--no-pool` fails profile-filled VRAM tier admission; a seven-pair prefetch-fill/stage confirmation matched tokens and state, with staged median request time 3.11% lower (paired bootstrap interval −5.81% to −1.05%), 0.472 GB fewer scoped reads at the median, 205–325 staged blobs consumed, 1.14–3.40 s aggregate decode wait, and up to 167.6 MiB pageable host staging; dynamic clocks and two large outliers limit this single workload/cache cell; a calibrated root-readable NVMap IOVMM client table measured a repeatable 83,427,328-byte process-owner increase across ten graph instantiations in three IQ1_M service startups; this is the capture/instantiate interval for that configuration, while other graph paths and non-NVMap allocations remain unpriced |
A new randomized [Q2_0 model cache × context admission screen](../../bench/results/2026-10-11-phase3-q2-admission/README.md) passed all four 3,000/5,000-slot × 4K/8K cells with one generated token under the six-GiB floor (15.88–18.52 GiB minimum availability). The reported session-state backing grew by 108,068,864 bytes when context doubled; the owner logs balanced 276/276 allocations and frees in each cell. This supplies an actual Q2_0-model admission point, not capacity, quality or performance qualification. The [Q2_0 active-cgroup admission follow-up](../../bench/results/2026-10-11-phase3-q2-cgroup-admission/README.md) passed the 512-token/one-output request under 10/12/20/24 GiB caps, with minimum effective availability 7.85/6.99/12.92/13.73 GiB; host `MemAvailable` stayed at least 18.48 GiB. The same requested 3,000-slot cache admitted 296/805/3,000/3,000 actual slots, respectively. At 8 GiB, no slots were admitted; prefill completed before the native speculative path failed due to the missing device residency table, with 6.74 GiB minimum effective availability. This is one workload/cache/context point; 8 GiB was not a successful request or a general minimum-capacity threshold. A seven-pair [PLE direct/mmap owner-traced diagnostic](../../bench/results/2026-10-11-phase3-q2-ple-mmap-confirm7/README.md) also balanced 276 allocations/frees per process with zero observed live bytes, but its timings are excluded because tracing adds prompt-path events. A separate three-pair [tracing-off timing screen](../../bench/results/2026-10-11-phase3-q2-ple-mmap-untraced3/README.md) had paired deltas from −9.31% to +13.27% and only a 0.49% difference in median prompt time; the PLE counter was 0.3 ms in both arms. This does not establish a transfer benefit and promotes no mode. A same-day seven-pair [current-binary confirmation](../../bench/results/2026-10-12-phase3-q2-ple-mmap-untraced7/README.md) again matched output and 5,000 actual cache slots in every run. Median prefill-stage time differed by −0.77% (mmap faster), but the paired bootstrap 95% interval was −1.83% to +0.76%, and the PLE counter remained 0.3 ms for each arm. This does not demonstrate an end-to-end transfer benefit; default dispatch remains unchanged. A three-pair [direct-versus-RAM-mode screen](../../bench/results/2026-10-12-phase3-q2-ple-direct-ram-screen/README.md) also passed at the same request point, but all three RAM-mode loads failed `mlock` under the launch process's 3,929,184 KiB hard memlock limit and left the table pages reclaimable. Paired prefill changes were −1.53%, +10.76% and +12.76%; this is a page-touch screen, not locked-RAM evidence or a performance confirmation. A subsequent [locked-RAM probe](../../bench/results/2026-10-12-phase3-q2-ple-ram-locked-probe/README.md) set transient per-process memlock limits of 8 and 12 GiB. Both uncapped requests passed but still fell back to reclaimable pages; the 22-GiB-capped 8-GiB attempt was supervisor-aborted at 5.85 GiB effective headroom with no OOM. The locked treatment remains unqualified; larger lock limits were not attempted because their headroom cost is unknown. The latest [current-binary Q2_0 PLE and Phase 3 rerun](../../bench/results/2026-10-11-phase3-current-ple-memory/README.md) passed all seven PLE stages for three tokens (worst relative L1 `1.148e-7`; 24.64 GiB minimum availability), the focused ten-test CTest set (24.54 GiB minimum), and all 20 owner-observation unit tests. These confirm selected contracts; graph-memory attribution, broad cgroup-pressure behavior and remaining transfer/admission gates remain open. A subsequent [15-test accounting and owner regression](../../bench/results/2026-10-11-phase3-accounting-ctest-current/README.md) passed shared-budget arithmetic, conversation/cache reservations, per-layer cache and convolution-state cache tests alongside VMM, PLE, refusal and pinned fallback coverage (24.63 GiB minimum availability). A seven-pair [prefill chunk 32 vs 128 screen](../../bench/results/2026-10-11-phase3-prefill-paired/README.md), with the same 5,000 cache budget and 512-token prompt, reduced median request time by 63.0% and TTFT by 65.1%, while median decode rate fell 6.8%; all outputs matched and the minimum availability was 8.44 GiB. It is a one-prompt screening cell only; no default changed, and held-out quality/confirmation remains required. The follow-up [three-length default-sharing screen](../../bench/results/2026-10-11-phase3-prefill-interaction-screen/README.md) matched output text in 8/9 chunk pairs (172, 557 and 1,069 prompt tokens); the CPU-sharing-disabled rerun matched only 6/9 ([report](../../bench/results/2026-10-11-phase3-prefill-interaction-noshare/README.md)). Both show higher prefill rates at chunk 128, but longer-prompt output drift leaves quality unqualified. No chunk default is promoted.

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

The broader [owner and memory regression rerun](../../bench/results/2026-10-11-phase3-owner-accounting-ctest/README.md) passed all 14 available selected CTests on the current binary, including the Q2_0 artifact-aware PLE oracle and cache/VMM/accounting cases. It ran sequentially under the six-GiB supervisor with 24.60 GiB minimum host availability. This confirms those focused contracts after the graph-owner changes; it does not close the outstanding graph-pool, broad pressure or transfer-measurement gates. A further [19-test owner/graph regression](../../bench/results/2026-10-11-phase3-owner-graph-regression-retry/README.md) passed the same PLE and accounting paths plus platform-memory, captured-graph ownership, convolution-cache and conversation validation/snapshot/file coverage, with 24.53 GiB minimum host availability. It still does not exercise legacy session/token graphs or price model graph-pool allocations.

The new [generic captured-graph runtime test](../../bench/results/2026-10-11-phase3-captured-graph-runtime/README.md) captures and replays a real asynchronous CUDA operation, checks its output and observes exactly one `captured-graph` owner event on Orin. Three calibrated NVMap process-owner repeats found no detectable net backing change (0 bytes at 50 ms sample resolution) for this minimal graph. This qualifies the generic wrapper's trace and bounds one graph's NVMap effect, while allocations outside NVMap, legacy model session graphs and model graph-pool bytes remain unmeasured.

Three Q2_0 64-token requests at a 20 GiB cgroup cap originally produced two complete, token-identical passes and one supervisor abort at 5.48 GiB effective scope headroom during prefill; host availability stayed above 21.65 GiB. One additional repeat also aborted at 5.55 GiB effective scope headroom while host availability stayed at 20.90 GiB; OOM/max events remained zero. The repeat set contains two passes and two safe supervisor aborts, confirming the cap is history-sensitive rather than a supported threshold. The passing repeat's cgroup `memory.stat` showed 8.29 GB file cache and 1.63 GB anonymous use at peak. See the [repeatability run](../../bench/results/2026-10-11-phase3-q2-cgroup20G-cache256-tg64-confirm3/README.md).

| 4 — SM87/ARM kernels | In progress | Pinned and current-candidate request profiles both rank Q6_K→FP16 dequantization first by summed kernel duration; the current profile's grids map to five repeated Q6_K matrix shapes in IQ1_M; six-type real-payload F32/BF16 and dedicated five-shape real-payload H16 checks pass, with 51,200 exact FP16 outputs and preserved packed input; linked SM87 kernel uses 22 registers/thread with zero stack, spills, shared or local memory; an isolated full-matrix CUDA-event baseline covers all five real shapes (median 0.198–4.759 ms); three-process CTA-size screen found no consistent winner and did not promote 128/256/512-thread candidates; Nsight Systems CPU sampling observed frequent ExpertPool worker-loop instruction samples, then a 3-block 1/2/4/8/11-worker screen found a correctness-gate failure (output drift at 11 workers and cross-cell state-fingerprint differences), so timings are retained as exploratory and no default changed; runtime Nsight Compute counters and Compute Sanitizer are unsupported here (profiling privilege warning; GPU debugging features disabled); an opt-in accepted-prefix trace captures published IDs and full state after each verifier commit; default CPU prefill sharing caused repeatable first-commit state divergence, while disabling it yielded identical token IDs, full accepted-prefix state and 36 GDN hashes across five processes; the 3-block 1/2/4/8-worker screen with sharing disabled passed all cells with equal cache capacity, output and accepted-prefix state, and minimum 14.06 GiB host availability; its trace-heavy timings were correctness-only. The follow-up [no-trace 3-block worker screen](../../bench/results/2026-10-11-phase4-pool-workers-512-no-trace/README.md) passed output/cache checks in all 12 cells; 8 workers were fastest in all three paired blocks (median request 17.61 s), with 13.24 GiB minimum host availability. This remains one workload/policy and no-trace state was not compared. Task-level quality remains open; no default changed; the seven-pair held-out 512/64 confirmation at 8K context matched text, draft/accept counts and 3,903 cache slots in every pair, with median request delta −5.901% (paired bootstrap 95% interval −7.004% to −4.953%) and prompt delta −7.226%; decode delta was +0.419%. One baseline prompt outlier (49.296 s) is retained. A traced 512/8 pair matched all four accepted-prefix commits and final state hashes; dynamic CPU rates were 729–2,201 MHz and GPU/EMC clocks and energy were unavailable. The cross-length [512/64 and 2,048/128 confirmation](../../bench/results/2026-10-12-phase4-q6-cross-length-context8k/README.md) added seven paired processes per workload at the same 8K context and observed request deltas −6.73% and −5.98%, driven by prompt reductions; decode was +0.22% and −0.10%. Paired outputs and 3,903 cache slots matched; minimum availability was 13.014 GiB. It remains timing-only evidence, with dynamic GPU/CPU clocks, no task-quality result and no default promotion. |
| 5 — Speculation and graphs | In progress | The [QSA spare-row transaction fix](../../bench/results/2026-10-11-phase5-spare-restore-long-chain/README.md) restores the dead key after accepted-prefix replay. MTP off/2/3/4 now match published IDs, every shared accepted-prefix boundary and final state in 32-token short-prompt screens across FP16/INT8/Q4_0/K8V4; a separate 2,048-token FP16 prompt screen also passes all windows. The current CUDA build and focused QSA tests pass, and changed HIP/SYCL objects compile on maestro1. Randomized three-pair 512/64 and 2,048/128 timing screens passed paired content/configuration checks but measured decode regressions for windows 2/3/4 (5.87/21.67/32.44% short; 11.22/26.41/36.50% long); these results promote no window. Graph/eager interaction, cancellation/recovery transaction-state checks, fallback counters and task-quality qualification remain open; see the [KV state matrix](../../bench/results/2026-10-11-phase5-mtp-kv-matrix/README.md), [short screen](../../bench/results/2026-10-11-phase5-mtp-window-perf-screen/README.md) and [long screen](../../bench/results/2026-10-11-phase5-mtp-window-2048-tg128-enabled/README.md) |
| 6 — Multivariate tuning | In progress | Initial randomized 2×2 worker × transfer screen completed on Q2_0; traced rerun passed state parity, but timing effects are inconclusive and no setting is recommended; held-out confirmation and other interactions remain open. See [screen](../../bench/results/2026-10-12-phase6-q2-worker-transfer-rerun/README.md) |
| 7 — Capacity and service | Not started | Quality, recovery, thermal equilibrium and sustained workload |
| 8 — Release/upstream | Not started | Relevant backend builds, runtime matrix and reviewable changes |

The held-out [1,069-token no-trace worker screen](../../bench/results/2026-10-11-phase4-pool-workers-1069-no-trace/README.md) had identical cache capacity and output across 1/4/8 workers; eight workers were fastest in each of three blocks. A seven-pair [4-vs-8 worker confirmation](../../bench/results/2026-10-11-phase4-pool-workers-1069-confirm7/README.md) on the current binary found a 1.54% lower median request time at eight workers, with the paired 95% median interval supporting a 0.80–1.91% slowdown for four workers; output/cache checks passed in all 14 runs. A separate current-binary trace follow-up matched final state and all accepted-prefix commits in two processes per arm. The small effect is confirmed only for one 1,069-token workload, 3,903 actual cache slots, MTP on and CPU prefill sharing disabled; task quality, GPU/EMC clock effects and general worker settings remain unqualified, so no default changed.

The [held-out 2,048-token/128-output worker confirmation](../../bench/results/2026-10-11-phase4-pool-workers-2048-confirm7/README.md) adds seven randomized pairs under the same 3,903-slot cache and CPU-prefill-sharing-disabled policy. All 14 requests produced identical output digests and admitted equal cache capacity. Eight workers reduced median request time by 2.36% and median decode time by 11.0%; the paired-bootstrap interval for four workers' relative request slowdown was +1.16% to +3.54%. Minimum host availability was 13.22 GiB. This is timing-only evidence under dynamic clocks; task-level quality and accepted-prefix state were not collected in these cells, and no default changed.

A [long-to-short same-process recovery check](../../bench/results/2026-10-11-phase3-long-short-recovery/README.md) ran a 2,048-token prefill and then a distinct 172-token request in one IQ1_M service process. Both completed all eight requested tokens with no prompt-cache reuse; owner events balanced 52 allocations/frees, and host availability stayed above 13.41 GiB. A separate [long-request disconnect check](../../bench/results/2026-10-11-phase3-cancel-long-prefill-recovery/README.md) closed a streamed 2,048-token request after one second, then recovered with a short request in the same process; the engine read the full prompt, generated no tokens, and reported cancellation. Its 52 allocation/free events also balanced, with 13.33 GiB minimum host availability. This confirms cleanup after disconnect, but active prefill did not stop early. Neither check covers cancellation under memory pressure or qualifies long-context quality. Phase 3 remains open for broader graph, pressure and transfer measurements.

The fresh [current-checkout Q2_0 PLE rerun](../../bench/results/2026-10-11-phase3-ple-rerun/README.md) again passed all seven stages for three tokens (worst relative L1 `1.148e-7`; 24.64 GiB minimum host availability). The sequential 15-test Phase 3 accounting/owner CTest selection also passed (24.60 GiB minimum). This confirms the checked operator and ownership contracts on the current candidate; graph-path attribution, broader pressure and transfer/admission measurements remain open.

An attempted [legacy session-graph runtime probe](../../bench/results/2026-10-11-phase3-legacy-session-graphs/README.md) was rejected before model load because the only local pack is native and requires the native execution path. It did not exercise the untested per-layer/session-token graphs; a compatible legacy pack or direct graph fixture is needed.

A fresh three-pair [pageable/pinned expert-stage check](../../bench/results/2026-10-11-phase3-stage-pin-confirm512/README.md) on the current IQ1_M binary matched all generated IDs and nine persistent-state fields, with both staging owner classes observed. Minimum host availability was 13.21 GiB. One pageable decode arm was a large outlier; timing remains descriptive, and no staging mode is promoted.

The [accepted-prefix state trace](../../bench/results/2026-10-11-phase4-accepted-prefix-trace-fixed/README.md) now records per-commit token IDs and the full state fingerprint after waiting for async commit completion. In four short Orin runs, output IDs matched, but GDN, QSA/KV and MTP state differed at the shared first committed boundary and across same-worker repetitions. A separate end-of-request state-hash control passed with the new code and per-commit tracing disabled. Trace hashing is synchronization-heavy and is correctness-only; worker timing remains disqualified pending a root-cause explanation. The native CUDA and maestro1 HIP builds pass for the changed generator; the SYCL build passes against its separate generator tree.

The [full-width GDN localization](../../bench/results/2026-10-11-phase4-gdn-layer-fullhash/README.md) reproduces drift at GDN ordinal 3 after the first QSA layer: with default CPU prefill sharing, two same-worker runs diverged on token seven and their per-GDN hashes first differed at ordinal 3. In a controlled [CPU-share-disabled repeat](../../bench/results/2026-10-11-phase4-gdn-prefill-share-control/README.md), two processes matched all eight tokens, full accepted-prefix state and all 36 GDN hashes. This supports the heterogeneous CPU/GPU prefill expert path as the cause. A follow-up [three-process no-share confirmation](../../bench/results/2026-10-11-phase4-gdn-prefill-share-confirm3/README.md) matched all tokens, full accepted-prefix state and 36 GDN slices in each process, extending the no-share result to five processes across two runs. This remains correctness evidence only; output-quality and CPU-share performance comparisons remain open. No worker timings are qualified and no default changes. A separate [prefill chunk accepted-state trace](../../bench/results/2026-10-11-phase4-prefill-state-trace/README.md) found chunk 32 and 128 repeatable within setting over two runs each, with identical eight token IDs, but different committed state at the first boundary `L=1069`; all 36 GDN layer hashes differ starting at ordinal 0, alongside PLE/QSA/KV/MTP hashes. This persists with CPU sharing disabled and shows a deterministic chunk-dependent state difference; its numerical magnitude and task-level quality remain unmeasured, so no chunk default is promoted. The [numeric GDN follow-up](../../bench/results/2026-10-11-phase4-prefill-state-numeric/README.md) dumped the first accepted `L=1069` state on one additional process per setting, after a shorter warmup. Chunk 32 vs 128 differs in 98.37% of 29.42 million float32 values; relative L2 is 3.138%, with maximum per-layer relative L2 5.33%. The runs pass the six-GiB floor and produce eight tokens, but do not identify a more accurate state or qualify task quality. The dump path is opt-in and no default is promoted.

The new [fixed-share numerical comparison](../../bench/results/2026-10-11-phase4-prefill-share-state-numeric/README.md) captures the measured request (after a distinct-length warmup) and confirms a 3.172% GDN relative-L2 difference at `L=512` between share-off and fixed 0.5, despite matching output through 64 tokens. Both admitted the same 6,519 cache slots and remained above the six-GiB floor; accepted-prefix state hashes diverged. The no-share and fixed-share cache-3000 three-process controls are now documented with their raw summaries. This is a correctness/diagnostic result, not a performance promotion or quality verdict.

A matched [default-auto CPU-share repeatability check](../../bench/results/2026-10-11-phase4-gdn-auto-share-cache3000/README.md) used the same 3,903 admitted cache slots and eight workers as fixed 0.5-share and share-disabled three-process controls. Auto mode emitted identical eight-token outputs and accepted token IDs, but persistent-state hashes diverged at every observed verifier boundary across processes, so its correctness gate failed and timings are excluded. The two fixed policies were each internally repeatable but ended with different committed state, leaving numerical/task-level accuracy unresolved. A later [fixed 0.5-share 5,000-slot screen](../../bench/results/2026-10-11-phase4-gdn-fixed-share-half/README.md) also failed its comparison gate: admitted capacity varied from 6,088 to 6,519 slots and persistent state differed, so no timing deltas were calculated. No prefill-sharing policy is promoted.

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

The new randomized [seven-process ownership-transfer screen](../../bench/results/2026-10-11-phase3-ownership-transfer-randomized7/README.md) compares matched 64 MiB checksum work across persistent pinned-copy, mapped-host, sequential-managed and per-iteration async-pool paths. All checksums passed and each process randomized path order; mapped was 61.76% faster than pinned-copy and 6.99% faster than sequential managed in paired process medians, while async-pool was 9.22% slower than pinned-copy. The six-GiB floor held. This is operator-level evidence only; current product buffers and request-level benefit remain unqualified, so no ownership mode changed.

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

The trace-free seven-pair [2,048-token pinned-stage confirmation](../../bench/results/2026-10-11-phase3-stage-pin-timing2048/README.md) adds a held-out prompt-length cell. Generated IDs and fixed 3,903-slot cache use matched; state hashes were intentionally not collected. Total request delta was −0.18% (paired 95% interval −18.49% to +1.48%), while decode was variable; minimum `MemAvailable` was 13.02 GiB. This does not establish a product benefit or close the broader transfer gate.
The three-pair [512-token pinned-stage clocked screen](../../bench/results/2026-10-11-phase3-stage-pin-clock-screen/README.md) matched IDs and fixed cache use. Prompt and request intervals span zero, decode was highly variable, and sampled GPU rates ranged 306–1,300.5 MHz despite stable sampled EMC at 3,199 MHz. It adds arm-aligned dynamic clock evidence but no state or energy evidence, and does not justify a default change.
A separate traced [2,048-token owner/state pair](../../bench/results/2026-10-11-phase3-stage-pin-state2048/README.md) matched generated IDs and all nine persistent-state fields across pinned/pageable arms. Owner allocation/free events balanced (85/85 pinned; 92/92 pageable); requested stage-host peaks were 154,419,200 and 173,056,000 bytes. Minimum availability was 13.30 GiB. These requested payloads exclude physical-backing reconciliation and graph executable bytes; this is correctness/owner evidence, not timing.

The current-binary Q2_0 [PLE rerun](../../bench/results/2026-10-11-phase3-q2-ple-current-rerun/README.md) passed, and the serial [Phase 3 memory/owner CTest selection](../../bench/results/2026-10-11-phase3-q2-memory-ctest-current/README.md) passed 22/22, including the slower PLE reader self-test. Minimum host availability was 24.55 GiB during the suite. These contract checks do not close the remaining Phase 3 pressure, graph-backing or transfer/admission gates.

The Q2_0 [worker × transfer rerun](../../bench/results/2026-10-12-phase6-q2-worker-transfer-rerun/README.md) revisited the one 4-worker/mapped persistent-state mismatch from the prior screen. A separate randomized traced matrix matched output, cache capacity, accepted-prefix traces and final persistent state in all 12 cells; the mismatch did not reproduce. The trace-free three-repetition screen also completed all 12 cells with identical output and cache use, but paired request-time effects were highly variable and intervals spanned zero. Minimum host availability was 17.47 GiB for correctness and 17.73 GiB for timing. This is inconclusive Phase 6 screening evidence only; no configuration is recommended and no default changed.

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

After rebuilding the current candidate for the accepted-prefix fix, the Q2_0
artifact-aware PLE oracle again passed all seven stages for three tokens
(worst relative L1 `1.148e-7`, 24.63 GiB minimum host availability), followed by
all 19 selected Phase 3 owner, cache, transfer, PLE, platform-memory, graph and
conversation CTests (24.51 GiB minimum). See the
[post-fix Phase 3 rerun](../../bench/results/2026-10-11-phase5-final-phase3-ctest/README.md).
This reconfirms those selected contracts on the modified tree; broader cgroup
pressure, graph-memory attribution and remaining transfer/admission gates keep
Phase 3 in progress.

A fresh [post-fix Q2_0 service and graph-owner run](../../bench/results/2026-10-11-phase3-post-fix-q2-graph/README.md)
passed all seven protocol/recovery scenarios. Three verifier window graphs and
the commit graph were all observed (4/4), and the verifier arena, mapped host
buffers, pageable expert staging, session and expert-cache owners balanced at
teardown. The calibrated NVMap counter rose 72,425,472 bytes from the stable
pre-graph sample through the fourth successful graph call, identical to the
earlier Q2_0 repeats; this interval still includes adjacent synchronous device
allocations. Minimum host availability was 21.15 GiB. This confirms one model
and graph configuration after the new verifier code, not general graph pricing
or pressure qualification.

The [8K-context Q2_0 follow-up](../../bench/results/2026-10-11-phase3-q2-graph-context8k/README.md)
also passed all seven API/cancellation/recovery scenarios, with 21.24 GiB
minimum host availability. Its four verifier/commit graph calls matched owner
events; session, expert cache, verifier arena, mapped host staging and pageable
expert staging allocations balanced at teardown. Stable NVMap growth was again
72,425,472 bytes across capture/instantiation, equal to the 4K run. This adds a
second context point for the same request/configuration, not a universal graph
size or closure of the remaining Phase 3 gates.

The [16K-context Q2_0 graph follow-up](../../bench/results/2026-10-11-phase3-q2-graph-context16k/README.md)
also passed all seven protocol/recovery scenarios with 21.04 GiB minimum host
availability. Session backing increased from 224.1 MiB at 4K to 327.1 MiB at
8K and 533.1 MiB at 16K. The [32K configured-reservation follow-up](../../bench/results/2026-10-11-phase3-q2-graph-context32k/README.md)
also passed all seven protocol/recovery scenarios (20.50 GiB minimum host
availability) and measured 945.1 MiB of session backing. The session increments
were 103, 206 and 412 MiB across successive context doublings. Four graph calls
and balanced owner events repeated at 32K; stable NVMap capture growth remained
72,425,472 bytes. These are configured startup reservations, not requests at
32K actual prompt length or capacity. This describes the tested Q2_0 startup
configurations; broader memory attribution and transfer/admission gates still
keep Phase 3 in progress.

The [Q2_0 cancellation-under-pressure check](../../bench/results/2026-10-11-phase3-q2-cancel-recovery-22G/README.md)
ran a 2,048-token streamed prompt under a 22 GiB cgroup cap. Disconnect stopped
prefill after 512 tokens with no generated output; all 302 observed allocation
pairs balanced, and the same service process then returned `Hello Orin!`.
Minimum host availability was 21.32 GiB. The 18 GiB cell was pressure-aborted
when effective cgroup headroom fell below the six-GiB guard, before recovery;
that failed cell is retained. This adds a bounded cancellation/recovery point,
not a general pressure guarantee or Phase 3 closure.

The fresh [Q2_0 PLE and Phase 3 ownership follow-up](../../bench/results/2026-10-11-phase3-ple-followup-current/README.md)
passed all seven artifact-aware PLE stages (worst relative L1 `1.148e-7`),
then all 15 selected accounting/owner CTests under the six-GiB supervisor.
Integration Python unittest discovery passed 91/91. Minimum host availability
was 24.60 GiB across the supervised checks. This reconfirms selected contracts
on the current checkout; broad cgroup pressure, other graph paths, and held-out
transfer/cache interactions remain open, so Phase 3 stays in progress.

The [Q2_0 layer-dump owner check](../../bench/results/2026-10-11-phase3-layer-dump-owner/README.md)
also exercised the opt-in pinned host buffer on the native speculative path.
The requested configuration is rejected after prefill because dumping
disables the token graph required for the device residency table. The pre-fix
trace showed a 2,007,040-byte pinned allocation without a matching free on that
early return. A function-scope cleanup guard now releases it; the rebuilt
binary emitted matching allocate/free events on the same rejected path. This
closes that cleanup case, while successful layer-dump execution remains
untested. Native CUDA rebuilt; maestro1 is reachable but presently lacks
installed HIP/SYCL compilers, so no fresh remote backend build is claimed.

The [Q2_0 decode-cancellation pressure check](../../bench/results/2026-10-11-phase3-q2-decode-cancel-22G/README.md)
now has three successful independent starts under a 22 GiB cgroup cap. Each
stream disconnected after visible decode and recovered with `Hello Orin!` in
the same live service; the engine committed three tokens before observing
cancellation. Minimum physical availability was 21.37 GiB and minimum cgroup
headroom was 9.50 GiB across the repeats. The 303 request/session allocation
pairs balanced in both new runs, with only the 1,485,606,400-byte service
weight arena remaining until exit; no cgroup OOM events occurred. This still
represents one Q2_0 cache/context configuration. A fresh PLE CTest
passed, the 19 selected Phase 3 accounting/ownership/PLE tests passed, and
integration Python unittest discovery passed 92/92. These checks reconfirm
selected contracts on the rebuilt candidate; Phase 3 remains open for broader
graph-memory attribution and admission/transfer coverage.

The [spec4 graph-owner probe](../../bench/results/2026-10-11-phase3-q2-graph-spec4/README.md)
adds a six-token verifier window at the same Q2_0 4K/256-slot startup. Three
successful graph instantiations (two verifier, one commit) matched owner
events; stable NVMap growth was 48,709,632 bytes over that capture interval,
with 21.43 GiB minimum physical availability. The earlier spec2 run observed
four calls and a 72,425,472-byte interval. Those different call sequences do
not isolate graph executable size or support a per-graph comparison. The
legacy session-token graph route and non-NVMap graph allocations remain
unpriced; no runtime default changed.

The paired [20 GiB cgroup-cap control](../../bench/results/2026-10-11-phase3-q2-decode-cancel-20G/README.md)
also passed cancellation and recovery with balanced owners, but peaked at only
3.70 GiB scope usage (16.30 GiB effective availability), so it is not treated
as pressure evidence.

An exploratory [MTP accepted-prefix cancellation run](../../bench/results/2026-10-11-phase5-mtp-cancel-state-parity-ignore-eos-rerun/result.json)
on the existing IQ1_M/MTP fixture emitted the same five token IDs in the
canceled and exact-length reference requests, and same-process recovery passed.
However, the persistent-state fingerprints differed at both committed
prefixes (`L=48` and `L=52`), so state parity failed and is not claimed. The
Q2_0 fixture has no compatible MTP weights; this result does not describe Q2_0
or close the Phase 5 transaction gate.

The [MTP logits owner check](../../bench/results/2026-10-11-phase3-mtp-logits-owner/README.md)
closes a missing owner event for the draft logits CUDA buffer: the rebuilt
candidate emitted its exact allocate/free pair, and the seven-scenario IQ1_M/MTP
API cancellation/recovery run balanced 53/53 instrumented allocations at zero
live bytes. Minimum physical availability was 9.84 GiB. The independent Q2_0
PLE oracle passed with its real tensor pack and GGUF table shard; ten selected
PLE/memory/owner CTests and all 92 integration Python tests passed. This closes
one MTP ledger gap, not graph-pool pricing or the remaining broad admission and
transfer gates; Phase 3 remains in progress.

A separate trace-free seven-pair [pageable/pinned timing screen](../../bench/results/2026-10-11-phase3-stage-pin-timing512/README.md)
now follows the traced correctness check. All 14 arms emitted 64 tokens with
matching IDs, fixed 3,903 actual cache slots and 13.17 GiB minimum host
availability. Paired prompt-stage delta was +0.48% (bootstrap 95% interval
−3.64% to +10.45%); decode was −2.13% (−46.18% to +134.52%), and the prompt+
decode stage sum was +12.10% (−24.00% to +58.19%). Wide paired uncertainty,
dynamic clocks and one prompt/cache cell leave the candidate unpromoted. The
traced three-pair state check remains separate; this timing run did not collect
state hashes or owner events.

The [Q2_0 32K-configured/spec4 graph check](../../bench/results/2026-10-11-phase3-q2-graph-context32k-spec4/README.md)
adds the missing context/speculation interaction point. A 31-token prompt and
24-token generation passed with 20.96 GiB minimum physical availability; three
successful Driver graph instantiations matched three owner events, and the
302/302 allocation/free pairs balanced. Stable NVMap backing increased by
48,709,632 bytes across capture/instantiate plus adjacent allocations. This is
not a 32K ingestion test or isolated graph executable size. The 32K/spec2 run
had four graph calls and a different 72,425,472-byte interval, so no per-graph
cost is inferred; legacy session graphs and non-NVMap bytes remain open.

The [Q2_0 actual 32K prompt admission](../../bench/results/2026-10-11-phase3-q2-actual32k/README.md)
completed a real 32,768-token prompt plus one output token under both 256- and
3,000-slot caches with a 32,800-token reservation. The four primary requests
and four diagnostic repeats passed above the six-GiB floor.
Within-profile state fingerprints matched exactly, while GDN, KV, tail and
pooled fingerprints differed repeatably across cache sizes (35/36 GDN layer
fingerprints differed) despite identical output IDs; prefill low-16-bit GDN
digests matched (not byte-level evidence). A full state dump showed 2.48%
relative-L2 GDN difference; first-window logits retained token 32 as argmax
with 0.0197 total-variation distance. Strata documents different CPU/GPU
accumulation order for cache hits and misses, which is a plausible but
unverified explanation; no independent whole-model oracle/tolerance was
applied. This remains unresolved cross-profile state parity and quality, not a
promotion result. The owner trace observed the session,
prefill, verifier and staging buffers release; the process-lifetime dense weight
arena remained live at log end, and graph-pool bytes remain outside this ledger.
Two earlier context-boundary validations were rejected before prefill. This is
admission evidence for the tested cells, not broad capacity or performance
evidence. The current candidate's `ple_parity` and `ple_reader_selftest` passed
2/2, and integration Python discovery passed 99/99. Phase 3 remains open.

The [mapped/pread × cache-budget interaction screen](../../bench/results/2026-10-11-phase3-transfer-cache-interaction-screen/README.md)
adds three randomized pairs at each 3,903- and 6,519-slot cache. All pairs
matched tokens and persistent state within cache size; mapped request time was
lower in all six pairs (median paired deltas −4.75% and −3.54%). Minimum host
availability was 13.05 and 8.03 GiB. The cache groups ran sequentially, clocks
were dynamic, and their state differed across cache size, so this is a screen
of transfer effects within each profile, not a cache-size or quality result.
No default changed; Phase 3 remains open.

The same [Phase 3 transfer/cache screen](../../bench/results/2026-10-11-phase3-transfer-cache-interaction-screen/README.md)
reran artifact-aware Q2_0 `ple_parity` and `ple_reader_selftest` on the current
candidate under the six-GiB supervisor; both passed. Integration Python tests
passed 99/99. Minimum host availability for the PLE CTests was 24.64 GiB.

A fresh seven-pair [scoped-I/O transfer confirmation](../../bench/results/2026-10-11-phase3-transfer-cgroupio-current7/README.md)
at 6,519 cache slots matched outputs, all nine persistent-state fields and
cache capacity in every pair. The cgroup counter was calibrated with a 64 MiB
`O_DIRECT` read and reported exact scope-level request bytes. The mapped arm had
a −4.80% median paired request delta and −0.668 GB median paired read delta;
minimum host availability was 8.30 GiB. The nominal pread arm was page-cache
fill (`STRATA_IO_PF_STAGE=0`), with zero prefetched blobs consumed and zero
decode waits, so it does not measure request-path pread service. Dynamic clocks
and this arm limitation remain; no default changed. The reusable calibration
helper's four focused tests and the full 103-test integration suite pass.

A [seven-pair staged-prefetch confirmation](../../bench/results/2026-10-11-phase3-transfer-stage-cgroupio-current7/README.md)
compared active host staging against page-cache fill at 6,519 slots, with
scoped I/O counters calibrated on the same filesystem. All pairs matched
tokens, persistent state and cache capacity; staging served 104–133 blobs per
request and waited 1.48–1.68 seconds during decode. Its median request delta
was −0.53% (95% bootstrap interval −0.89% to +1.66%), with a 91–135 MiB
requested host-stage peak and 8.16 GiB minimum host availability. The scoped
read interval spans zero, as does the timing interval; no path is promoted.

The same-binary [3,903-slot staged-prefetch confirmation](../../bench/results/2026-10-11-phase3-transfer-stage-cgroupio-cache3000-current7/README.md)
adds a lower-cache comparison. All pairs passed output/state/cache checks;
staging served 278–312 blobs and its requested host peak reached 177.7 MiB.
The median paired request delta was −1.27% (95% bootstrap interval −3.48% to
+0.08%), while the paired scoped-read delta was +0.168 GB (interval +0.018 to
+0.477 GB). Minimum availability was 12.85 GiB. Together with the 6,519-slot
confirmation, this confirms staging activity at both capacities, but the cache
strata ran sequentially and no cross-profile interaction or default is
qualified.

A three-pair [Q2_0 pageable/pinned stage screen](../../bench/results/2026-10-11-phase3-q2-stage-pin-screen/README.md)
also matched generated IDs, all nine state fields, cache counters and expected
stage-owner types in every pair. Both modes requested 353,894,400 bytes of
stage buffers. The traced timing screen had one large prompt outlier; its
request interval spans zero, and it supports no performance claim. The guarded
28-GiB-capped campaign stayed above 12.61 GiB effective cgroup headroom. A
separate 22-GiB attempt was safely stopped at 5.97 GiB sampled effective
headroom and is retained as a pressure abort; no OOM occurred. This adds a
Q2_0 transfer-correctness point but leaves the broader Phase 3 transfer gate
open.

A seven-pair [warmup-separated Q2_0 stage-backing timing diagnostic](../../bench/results/2026-10-11-phase3-q2-stage-pin-confirm7-clean/README.md)
reran the pageable/pinned comparison with genuinely trace-free engine processes
after an earlier run was found to retain the graph probe via `LD_PRELOAD`. All
measured token IDs matched. The paired request delta was +0.58% (pinned slower,
95% whole-pair bootstrap interval −2.01% to +10.36%); no end-to-end benefit or
default change is supported. However, warmup completion hashes differed in two
of seven pairs. A three-pair traced [warmup/state follow-up](../../bench/results/2026-10-11-phase3-q2-stage-pin-warmup-state3/README.md)
passed measured token and state parity in the two pairs with matching warmup
outputs; the third had matching measured IDs but differed in five state fields
after its warmup completion diverged. Treat the timing as diagnostic only.
The stage harness now marks warmup-output mismatches as failed pairs. A direct
172-token isolation probe was rejected before startup because the harness
requires at least 512 measured prompt tokens; the existing no-warmup 512/64
screen is the direct-request control. Minimum
`MemAvailable` was 21.18 GiB and minimum
28-GiB cgroup headroom 18.68 GiB, with no OOM events. Two pairs differed in
The earlier probe-enabled timing is retained but excluded from inference.
Focused stage-parity tests passed 8/8 and integration Python discovery passed
106/106 after the warmup-completion validation. Phase 3 remains open.

The current Orin candidate was then rechecked with the artifact-aware Q2_0 PLE
oracle and the selected 19-test Phase 3 CTest set. All seven PLE stages passed
(worst relative L1 `1.148e-7`), and CTest passed 19/19. Minimum host availability
was 24.48 GiB and 24.32 GiB, respectively, under the six-GiB supervisor. The
[rerun report](../../bench/results/2026-10-11-phase3-current-regression-after-harness/README.md)
reconfirms selected contracts but does not resolve the warmup-state finding or
close the broader Phase 3 gates.

The held-out [Q6_K warp-dequant 16K-context confirmation](../../bench/results/2026-10-11-phase4-q6-warp-context16k-confirm7/README.md)
adds seven same-day randomized pairs at a 16,384 context with a new 2,048/128
synthetic incident-log input. All cells passed; warmup and measured output
hashes, token counts, speculative counts and cache-slot counts matched within
pairs. Median request time fell 5.33% (whole-pair bootstrap 95% interval
−7.87% to −2.67%); the prompt median fell 5.63%, while decode interval spans
zero. A separate traced pair matched all three accepted-prefix commits and the
full/GDN state fingerprints. Minimum host availability was 12.88 GiB with no
OOM events. Alongside the 8K confirmation, this supports keeping the candidate
opt-in for further Phase 4 qualification; synthetic prompt construction,
task quality, other workload classes, GPU/EMC clock frequencies and energy
remain limitations. Phase 4 remains open, and Phase 3 ownership/transfer gates
remain active.

A clean [Q2_0 stage-backing warmup/state rerun](../../bench/results/2026-10-11-phase3-q2-stage-pin-warmup-state3-rerun3-nocap/README.md)
adds three trace-enabled pageable/pinned pairs after the earlier 2/3 state
result. All three now matched warmup completion, measured IDs and all nine
persistent-state fields, with the expected owner types and 353,894,400 requested
stage bytes per arm. Minimum effective availability was 21.11 GiB; sampled CPU
and GPU clocks were retained, EMC sampling was unavailable, and no timing claim
is drawn. The earlier mismatch did not recur, but its cause remains unknown.
A separate attempt with an added 28-GiB experiment cgroup was safely aborted at
5.81 GiB cgroup headroom while host availability remained 24.95 GB; it is kept
as a distinct pressure-abort record. Focused stage-parity tests passed 8/8.
Phase 3 remains open for broader pressure, graph-backing and transfer gates.

Two three-startup [Q2_0 cancellation/recovery checks](../../bench/results/2026-10-11-phase3-q2-cancel-prefill128-recovery3/README.md)
extend cleanup coverage with a `--prefill 128` configuration. Closing the
stream after eight seconds cancelled at 256 prompt tokens in all runs; closing
after eighteen seconds cancelled at 768 tokens, after three completed batches,
in all later-point runs. Every same-service `Hello Orin!` recovery passed.
Each trace recorded 304 allocations and 303 frees; only the expected
1,485,606,400-byte process-lifetime weight arena remained. Both supervisors
passed without extra cgroup caps, with at least 21.10 GiB available and no OOM
events. CPU and GPU clocks were sampled dynamically, EMC sampling was denied,
and energy was not measured. This covers two cancellation progress points for
one model/configuration; recovery after allocation failure and broader request
sizes remain open.

The latest [current-candidate regression](../../bench/results/2026-10-11-phase3-q2-followup-regression/README.md)
passed the artifact-aware Q2_0 PLE parity test and 18 additional selected
memory, cache, VMM, graph, and conversation-state CTests (19/19 total), plus
integration Python discovery (106/106). This is software-contract evidence
without a memory supervisor or serving request; the broader Phase 3 physical
backing, pressure, graph-pool, and transfer/admission gates remain open.

The [Q2_0 16K configured-context extension](../../bench/results/2026-10-11-phase3-q2-admission-16k/README.md)
passed one-token requests at 3,000 and 5,000 expert-cache slots, with 18.27 and
15.83 GiB minimum `MemAvailable`, respectively, under the six-GiB floor. Each
instrumented owner trace balanced 278 allocations/frees; requested-live peaks
were 6,592,312,952 and 9,357,112,952 bytes. This extends the 4K/8K admission
screen but is not a long-context request or capacity claim. Graph/driver backing
remains outside the owner trace and Phase 3 remains open.

The [32K configured-context extension](../../bench/results/2026-10-11-phase3-q2-admission-32k/README.md)
also passed at 3,000 and 5,000 slots, with 18.03 and 15.34 GiB minimum
`MemAvailable`. The traces balanced 278 allocation/free events per process;
requested-live peaks were 7,024,653,944 and 9,789,453,944 bytes, and the
session owner requested 991,516,160 bytes. These are configured-reservation
admission points with 512-token requests, not 32K workload evidence. Graph and
driver backing remains outside the owner trace; Phase 3 remains open.

The [64K configured-context extension](../../bench/results/2026-10-11-phase3-q2-admission-64k/README.md)
passed at the same cache sizes, with 17.21 and 14.51 GiB minimum
`MemAvailable`. Each owner trace balanced 278 allocation/free events; requested
live peaks were 7,889,335,928 and 10,654,135,928 bytes, with a
1,856,067,072-byte session allocation request. Together, the 4K/8K, 16K, 32K
and 64K points exercise the planned Q2_0 cache-by-configured-context
admission cells at 3,000/5,000 slots. All generated one token from a 512-token
prompt, so they do not qualify long-context requests or establish capacity
limits. Graph and driver-private backing and broader pressure interactions
remain unmeasured; Phase 3 remains open.

A current-binary [Q2_0 cgroup pressure recheck](../../bench/results/2026-10-11-phase3-q2-cgroup-retest/README.md)
ran the same supervised 512/1 request under 8–16 GiB transient cgroup caps.
The 8/10/12/14-GiB scopes crossed the six-GiB effective-headroom floor and were
pressure-aborted without OOM; the 16-GiB scope passed with 3,000 slots and
output token 32. Host `MemAvailable` stayed at 18.52 GiB or higher in the
14/16-GiB cells. Unlike the older 8-GiB observation, the new 8-GiB attempt
aborted before cache admission, so it does not reproduce the residency-table
error. Earlier successful 10/12-GiB cells remain as distinct state-dependent
observations; current pressure behavior is not a stable capacity boundary.

The [64K/spec4 graph-backing confirmation](../../bench/results/2026-10-11-phase3-q2-graph-context64k-confirm3/README.md)
passed three independent 31/24-token API requests under the six-GiB supervisor.
Each startup matched all three successful graph instantiations to owner events.
Calibrated NVMap plateaus were exactly 6,870,433,792 bytes before and
6,919,143,424 bytes after the graph sequence in every run, a repeatable
48,709,632-byte owner increase. This matches the 32K/spec4 interval for these
two configurations, while adjacent synchronous allocations remain included.
Legacy graph shapes, non-NVMap bytes and isolated executable cost remain open;
Phase 3 continues.

A trace-free Q2_0 [pageable/pinned stage timing screen](../../bench/results/2026-10-11-phase3-q2-stage-pin-timing512/README.md)
added three order-balanced pairs to the earlier three-pair run. All six pairs
matched token IDs; the paired median pinned request-time delta was −6.81%, with
a 95% bootstrap interval of −12.26% to +17.02%. This remains a single 512/64
screen with dynamic clocks and no energy measurement; pageable remains default.

At 2,048/64, a separate [Q2_0 correctness and owner check](../../bench/results/2026-10-11-phase3-q2-stage-pin-2048/README.md)
passed all three pageable/pinned state comparisons and observed the expected
353,894,400-byte stage buffers. Its trace-free three-pair timing follow-up had
a +3.25% pinned request-time delta with a −1.67% to +31.58% interval and one
large prompt-time outlier. It does not show a reliable gain; pageable remains
the default and broader transfer/pressure gates stay open.

A Q2_0 [prefetch-fill versus prefetch-stage screen](../../bench/results/2026-10-11-phase3-q2-prefetch-stage-screen-explicit-disk/README.md)
matched outputs, persistent state, and cache capacity in three pairs. The
paired median stage request-time delta was −1.88% (95% interval −5.08% to
+3.84%); process and cgroup I/O counters were unavailable, while device-wide
block reads included unrelated activity. The native-pack block-counter path
now accepts an explicit GGUF artifact. No mode was promoted.

An exploratory [Q2_0 worker/read-policy correctness screen](../../bench/results/2026-10-11-phase6-q2-worker-transfer-screen/README.md)
completed its 12 mapped/pread × four/eight-worker cells, but one cell had
different accepted-prefix state hashes despite identical output tokens. A
focused three-run repeat passed; the mismatch cause is unknown, so no timing
comparison was made and no policy was promoted.

The [Q2_0 cache-capacity state diagnostic](../../bench/results/2026-10-12-phase3-q2-cache-state-diagnostic/README.md)
reproduced the 3,000/5,000-slot state difference with the same exact 512-token
prompt. Same-capacity process repeats produced bit-identical first verifier
logits and repeatable GDN state; cross-capacity logits differed in every FP32
element and full GDN state differed by 1.11% relative L2. Both configurations
selected token 32, and a shared 511-token prefix also diverged beginning at
layer 3. The diagnostic does not establish whether this numerical difference
is acceptable or identify its cause; expert hit/miss compute is a lead only.
No cache default or quality claim follows. Phase 3 remains open.

The same diagnostic's opt-in CPU-order reduction follow-up reproduced the
default-path accepted-prefix GDN dumps byte-for-byte at both capacities. It
therefore did not explain the cross-capacity difference for this prompt; the
cause remains open and the experimental flag is not promoted.

A randomized [Q2_0 prefill-chunk × cache-capacity screen](../../bench/results/2026-10-12-phase3-q2-cache-state-diagnostic/README.md)
crossed chunks 64/128/256/512 with 3,000/5,000 cache slots, using two fresh
processes per cell on the same 511-token prefix. All 16 runs passed above the
six-GiB floor and selected token 271; repeat GDN dumps matched byte-for-byte
within each cell. Across cells, chunk changes produced 2.19–3.30% GDN relative
L2 differences and cache changes 1.66–2.29%. The numerical cause and task-level
effect remain unqualified; this is a one-prompt, one-token diagnostic, not a
quality result or timing promotion. Keep Phase 3 open.
Owner traces in the same cells balanced 304 allocations against 303 frees,
with the 1,485,606,400-byte weight arena remaining for process lifetime. The
prefill owner request rose from 197.2 to 350.1 MB across chunks 64–512; the
expert-cache owner requested 4.147/6.912 GB at 3,000/5,000 slots. These are
instrumented requested payloads, not physical backing totals; graph and driver
bytes remain outside the trace. Full cell accounting is in the linked report.

A [Q2_0 64-token continuation follow-up](../../bench/results/2026-10-12-phase3-q2-cache-state-diagnostic/README.md)
used two fresh processes per endpoint cell (chunk 64/512 × cache 3,000/5,000).
All eight requests returned the same 64-token sequence, and accepted-prefix
fingerprints repeated exactly within each cell. Fingerprints differed from the
3,000-slot/chunk-512 control at every commit when either factor changed. This
is one prompt with greedy decoding; it does not qualify task quality or resolve
the state difference. Phase 3 remains open.

The randomized [Q2_0 cache × context state screen](../../bench/results/2026-10-12-phase3-q2-cache-context-state/README.md)
crossed 3,000/5,000 cache slots with 8K/64K context reservations in three fresh
processes per cell. All 12 cells selected token 271 and repeated byte-identical
accepted-prefix hashes within each setting. Full GDN state was identical
between contexts at each cache size, but cache size changed GDN/tail/pooled/KV
state at both contexts (first GDN difference at layer 3; global relative L2
1.659%). Minimum host availability was 13.66 GiB; allocation/free events
balanced except for the service-lifetime weight arena. This isolates the
observed state difference to cache capacity for this request, not context
reservation; its cause and task-quality effect remain unresolved. No cache
default changed and Phase 3 remains open.

The Q2_0 [32K prompt continuation trace](../../bench/results/2026-10-12-phase3-q2-cache-continuation/README.md) compared requested cache sizes 3,000 and 5,000 at 64K configured context. Two fresh 20-GiB-capped processes passed the six-GiB effective-headroom floor, completed the exact same 32,768-token prompt, and emitted identical 32-token continuations with matching token IDs at all 32 commit boundaries. Persistent fingerprints already differed at the first commit (`L=32768`) and at all later commits: GDN/tail/pooled/pooled-full/KV differed at all 32, PLE at 16, stale at 3, while dead/MTP/PLE-previous matched. The trace runs took about 466 seconds each because state tracing synchronizes decode; timing is excluded. This confirms the cache-capacity state difference continues through this one greedy continuation, but does not identify cause or task quality. No cache default changed; Phase 3 remains open.

A randomized Q2_0 [32K prompt prefetch-fill versus staging screen](../../bench/results/2026-10-12-phase3-q2-actual32k-prefetch-stage/README.md) completed three pairs at a fixed 3,000-slot cache. All arms emitted matching eight-token IDs and all nine state fingerprints within each pair. Median end-to-end request delta was +16.96% for staging (slower), with a three-pair bootstrap interval from −0.50% to +33.43%; scoped read deltas changed sign and page faults varied. The screen is inconclusive and neither mode changed. A later three-pair campaign safely aborted during the third pair's engine startup at 5.908 GiB effective cgroup headroom (host availability 17.25 GiB, zero OOM events); its first two pairs completed and contribute to the screen alongside the separate pilot. The Q2 pack lacks `experts.bin`, so the harness now accepts an explicit GGUF for whole-device telemetry. Testing also fixed the exact-context boundary by reserving 32 tokens beyond prompt plus decode. Focused transfer tests passed 10/10 and full integration Python discovery passed 119/119. This adds one actual-long-prompt transfer cell, not a held-out confirmation; Phase 3 remains open.

A randomized Q2_0 [32K prompt mapped-versus-pread screen](../../bench/results/2026-10-12-phase3-q2-actual32k-mapped-pread/README.md) completed three pairs at the same 3,000-slot cache and prompt. Token IDs, cache slots and all recorded state fingerprints matched within every pair. Median request delta was effectively zero (−0.001% for pread), with a paired three-pair bootstrap interval from −0.48% to +14.58%. Scoped cgroup reads and major faults favored pread, but the arms shared page-cache history and the first pair had a 14.58% reversal; those counters do not establish a cold-read or product win. The 28-GiB systemd scope preserved 17.16 GiB minimum host availability and 8.34 GiB minimum effective headroom, with no OOM events. No transfer mode changed; Phase 3 remains open.

The traced [16K owner/state follow-up](../../bench/results/2026-10-13-phase3-q2-admit16k-22G-trace/README.md) passed with a distinct exact-length warm-up prompt and zero reuse on the measured request. The target fingerprint was recorded at `L=16384`; its 304/303 owner ledger left only the 1,485,606,400-byte weight arena live. At 22 GiB, minimum effective headroom was 9.997 GiB with no OOM events. A same-prompt warm-up attempt is retained as a failed harness cell because the measured request reused 16,377 prompt tokens; the API response itself was valid. This qualifies observed state/owner cleanup for this request, not task quality or capacity.

A fresh [Q2_0 16K prompt admission run at 19 GiB](../../bench/results/2026-10-13-phase3-q2-admit16k-19G/README.md) completed the exact 16,384-token request twice in one service (one warm-up and one measured), returning one token each time. With 32K configured context and 3,000 requested cache slots, minimum host availability was 17.40 GiB and effective cgroup headroom was 8.686 GiB; OOM counters stayed zero. This extends the actual-prompt ladder between existing 8K and 32K observations. Trace was disabled, so there are no owner/state fingerprints; it is admission evidence only and does not establish a support boundary.

The [Q2_0 19-GiB admission repeat](../../bench/results/2026-10-12-phase3-q2-actual32k-context64k-19G-repeat2/README.md) passed the same exact prompt, cache and context configuration as the earlier 19-GiB run. It reproduced token 32, all prompt-end state fingerprints, and all 36 layer GDN hashes. Minimum effective headroom was 9.11 GiB (the first run reached 6.98 GiB); observed ownership again left only the service-lifetime weight arena. Both runs passed, but differing starting cgroup/page-cache conditions mean this is repeatability evidence, not a capacity boundary. Phase 3 remains open.

The Q2_0 [8K pageable-versus-pinned expert staging screen](../../bench/results/2026-10-12-phase3-q2-stage-pin-8k/README.md) completed three randomized pairs under a 28-GiB cgroup ceiling; all matched output IDs and persistent state. Each stage owner requested 337.5 MiB and balanced 256 allocations/frees per arm. Pinned request-time deltas were −4.80%, +46.16% and +0.83%, with a three-pair bootstrap interval from −4.80% to +46.16%; the result is inconclusive and no mode changed. Minimum host availability was 17.75 GiB and effective headroom 10.60 GiB, with zero OOM events. A separate 24-GiB campaign safely aborted pair 3 at 5.65 GiB after two matching pairs. The harness context-margin fix passed its 9 focused tests and full Python integration discovery passed 120/120.

The standalone CUDA [grouped expert-hit parity check](../../bench/results/2026-10-12-phase3-q2-cache-context-state/README.md)
also passed after a memory-bounded target build. Synthetic Q2_0 host-count,
device-count, mixed-scale, window and alignment cases matched the prior kernels
bitwise and passed the independent double-precision row oracle (worst reported
error `1.10e-7` of sum-of-absolute-terms). This narrows the unresolved cache
capacity effect beyond the isolated grouped hit operator; full-model hit/miss
combination and task-quality explanations remain open.

The current-binary [Q2_0 PLE and memory-contract confirmation](../../bench/results/2026-10-12-phase3-q2-ple-confirmation/README.md)
passed the supervised artifact-aware PLE oracle (worst stage relative L1
`1.148e-7`), the focused memory/VMM/cache/PLE CTest selection (15/15), and
integration Python unittest discovery (113/113). Minimum host availability was
24.47 GiB for both the direct PLE test and CTest. These are contract
checks, not active-pressure, whole-model quality, or ownership closure; Phase 3
remains open.

A fresh [Q2_0 PLE and integration regression rerun](../../bench/results/2026-10-12-phase3-q2-ple-current-rerun/README.md)
again passed all seven PLE stages for three tokens (worst relative L1
`1.148e-7`), the focused 15/15 memory/owner/PLE CTests, and integration Python
discovery (117/117). Minimum host availability was 24.60 GiB for both
supervised GPU runs. This reconfirms software contracts; it does not close
Phase 3's pressure recovery, physical backing, graph accounting or transfer
qualification gates.

A trace-free [seven-pair Q2_0 prefill-chunk timing screen](../../bench/results/2026-10-12-phase3-q2-cache-state-diagnostic/prefill-chunk-timing/README.md)
at fixed 3,000-slot cache/context/reserve found chunk 512 faster than chunk 64
for this 511-token prompt and eight-token continuation: median client elapsed
delta −44.87% (paired bootstrap 95% interval −49.76% to −40.45%), with prompt
time −15.121 s and decode interval spanning zero. All pairs emitted identical
tokens and stayed above 18.01 GiB minimum host availability. Dynamic CPU/GPU
clocks, one synthetic prompt, and unqualified accepted-prefix state differences
limit this to a performance screen; neither chunk setting is promoted.

An attempted Q2_0 64K captured-versus-disabled graph control was unsupported:
`--no-capture` triggers the native-route guard because it would omit routed
CPU-pool experts, and `--no-token-graph` is rejected by the serving layer before
readiness. Both failures occurred above 21 GiB host availability and issued no
request. See the [control compatibility probe](../../bench/results/2026-10-12-phase3-q2-graph-context64k-spec4/graph-control-compatibility/README.md).
The existing supported captured-path NVMap attribution remains scoped to its
tested configuration; Phase 3 graph-backing qualification remains open.

The opt-in [Q6_K warp-dequant 32K-context confirmation](../../bench/results/2026-10-12-phase4-q6-warp-context32k-screen/README.md)
passed seven randomized pairs on a new exact 2,048/128 synthetic incident-log
request. All arms passed above 12.37 GiB minimum availability. Client elapsed
time improved by a median 5.96% (paired bootstrap 95% interval 4.34–7.05%
faster); prompt time improved 6.89% (4.98–7.13% faster), while decode spans
zero. One pair differed by one accepted draft and contains a slow baseline
outlier; all seven matched text, token counts and cache sizes. A separate
traced state pair matched all accepted-prefix commits and final state. This
adds a 32K configured-context cell, not task-quality evidence or default
promotion; Phase 4 remains open.

The Q2_0 [8K-context captured-graph NVMap repeat](../../bench/results/2026-10-13-phase3-q2-graph-context8k/README.md) extended the short-request graph-backing sample to 3,000 cache slots, speculation 2 and context 8,232. Three processes passed with identical output/state and four matched graph-owner events each. The NVMap process-owner interval was exactly 71,983,104 bytes in all three runs, matching the separate 32K/spec2 observation; it still includes adjacent allocations and is not executable size or total physical memory. Minimum host/effective headroom was 17.83 GiB with no OOM. The graph-disabled control remains unsupported, and legacy graph shapes/non-NVMap backing remain open.
