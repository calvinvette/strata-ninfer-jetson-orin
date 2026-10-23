# Integration status

Updated: 2026-10-22. Phases 1 through 4 are complete for their documented tested
Orin scopes (Phase 3 Q2_0; Phase 4 opt-in kernel/CPU candidates). Phase 7 is
complete for its bounded Orin qualification matrix under [its closeout]
(PHASE7_CLOSEOUT.md), and Phase 8 is complete for the bounded Q2_0 release
profile under [its closeout](PHASE8_CLOSEOUT.md). Phases 5 and 6 remain open;
the Phase 8 profile excludes their unresolved adaptive/MTP and broader
parametric/energy scope. This records tested cells, not general product support.

The bounded Phase 8 Q2_0 release profile was rechecked on the current candidate
on 2026-10-22: the 8K-context, 3,000-slot, chunk-128 MTP-off profile passed its
7,498-token retrieval and same-service recovery check, and the current CUDA
CTest suite passed 130 tests with two optional IQ fixtures skipped; Python
integration tests passed 163/163. This is a fresh functional/regression smoke,
not a repeated performance confirmation and does not widen the Phase 8 support
scope. See the [smoke report](../../bench/results/2026-10-22-phase8-current-source-q2-profile-smoke/README.md).

A current-source Coder IQ1_M MTP2 cancellation check also passed: after five
visible deltas, eight tokens had committed across five accepted-prefix states
(lengths 48, 50, 51, 53 and 55). Two fresh exact-length controls matched every
token sequence and recorded persistent-state fingerprint; the canceled service
then returned the expected recovery response. Minimum host/admission
availability was 13.18/12.53 GiB with zero cgroup events. This covers the tested
cancellation boundaries only; Phase 5 remains open. See the
[cancellation report](../../bench/results/2026-10-22-phase5-coder-mtp2-cancel-state/README.md).

A held-out 256-token short–short–short Coder IQ1_M chain now has direct raw
layer-22 committed-state comparisons at accepted positions 515, 530 and 640.
The adaptive recovery state already differs at position 515—before the first
recovery token changes—in 786,405/786,432 recurrent values (relative L2
`2.60e-4`) and 30,719/30,720 convolution values (relative L2 `7.86e-4`). By
position 530 all captured values differ and recovery tokens diverge further.
The delayed-control initial/intermediate/recovery states are bit-identical at
all three positions. All nine raw records per arm were checked against the
service accepted-prefix hash. The adaptive endpoint-767 capture attempt failed
because the 256-token run ended at 766; the three valid positions were retained
and verified separately. This confirms long-chain adaptive state drift for this
workload but does not locate its responsible upstream operation or provide a
general tolerance. Phase 5 remains open. See the
[raw-state report](../../bench/results/2026-10-22-phase5-coder-long-chain-raw-state-pair-pos767/README.md).

A batch-aware `STBNDY2` residual capture and MoE owner trace localized one
target-only delayed-admission difference at position 119 to layer-11 expert
arithmetic. The layer-10 boundary and layer-11 MoE input, routes, weights and
shared-expert output matched serial; three routed expert parts switched from
primary VRAM to CPU in the batch row, and their weighted changes accounted for
the combined-output delta. Slot-0 output still matched all 96 serial tokens.
A same-input native expert oracle then matched each serial part to its CUDA
output and each batch part to its CPU output bit-for-bit, confirming the
owner-specific arithmetic path for all three rows. A paired all-layer capture
at the same committed position found GDN states exact through model layer 10,
then first changed at layer 12 (795,789/817,152 values; relative L2 0.00170369);
all 27 later GDN states differed. Across 36 layers, 21,504,757/29,417,472
floats changed (relative L2 0.00781353). All 96 generated slot-0 tokens still
matched serial.
A 3,000 MiB cache-cap follow-up had already diverged by layer 11. Capturing
layer 10 localized the first selected owner delta: its input, routes, weights
and shared output matched serial, while experts 150 and 2 moved primary
VRAM→CPU. Exact-activation native oracles matched the serial and batch service
parts to CUDA and CPU respectively; both expert outputs use IQ2_S gate/up and
Q2_0 down weights. This diagnoses the changed arithmetic path, not a cache
performance effect. It is a single-prompt correctness diagnostic; Phase 5
remains open.
See the [batch-MTP diagnostic](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

A supervised one-live-after-admission MTP2 trace now shows the same QSA state
boundary after the competing one-token request completes: lengths 70/72/74
match serial, while indexer and K/V hashes differ in all 12 layers at lengths
76 and 78, first at model layer 3. Slot 0 generated 96 tokens and the short
competitor one; both outputs exactly matched serial. Minimum host/admission
availability was 16.77/13.50 GiB with zero cgroup events. This removes the
need for two simultaneously active verifier rows to reproduce persistent QSA
drift, but leaves the solo-to-batch transition versus batch-slot execution
unresolved. Phase 5 remains open. See the [batch-MTP diagnostic](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

An extended one-live-after-admission run generated 96 tokens with exact serial
output parity. Early state samples were unpaired because batch and serial MTP2
recorded different accepted-length parity; at every common captured length
91–163 (41 samples), all 12 QSA indexer and K/V hashes differed. The run kept
16.76 GiB minimum host/admission availability and zero cgroup events. State
divergence therefore persists across this sampled range, but has no numerical
bound here and its effect on quality is unknown.

A direct numeric follow-up captured the one-live-after-admission MTP2 slot at
common committed position 126. Its output matched serial for all 96 tokens, but
all 36 GDN layers differed in 28,576,901/29,417,472 floats (relative L2
0.00972594, maximum absolute difference 0.373845; first changed model layer
1). The run retained 16.69 GiB minimum host/admission availability and zero
cgroup events. This confirms the longer one-slot QSA hash drift also accompanies
numeric recurrent-state movement; the cause and quality bound remain unknown.
A requested position-127 dump had no matching commit and yielded no records;
position 126 was the complete capture. See the [batch-MTP report](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

A matched target-only one-live-after-admission control also produced numeric
GDN drift at committed position 126 while matching all 96 serial output tokens.
All 36 layers changed (28,576,928/29,417,472 values; relative L2 0.00841253,
maximum absolute difference 0.46446; first changed model layer 1). Minimum
host/admission availability was 17.80 GiB with zero cgroup events. Since both
target-only and MTP2 reproduce the movement, MTP2 is not required; the shared
batch-row path versus solo-to-batch transition remains unresolved. This is
not a performance result.

A corrected [delayed-admission MTP2 trace](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md) submitted the second request only after slot 0 had generated 48 solo-path tokens. Both outputs matched serial (96 and one token). QSA hashes matched serial at the first common post-handoff lengths 121/122, then all 12 indexer/KV groups first differed at length 124/model layer 3 and remained different through 163. This places the first captured state change after the solo prefix and handoff, during later batch-slot work; it does not identify an operation. The earlier QSA `one-live` runs submitted both requests concurrently because of a harness name-check error; they show the long request continuing after its one-token peer finished, not a delayed arrival. The separate target-only GDN capture did wait for the first output token. Phase 5 remains open.

A matching all-layer GDN capture at the same delayed-admission boundary was
bit-identical to serial at committed positions 120 and 121. At position 123,
all 36 layers differed (28,228,404/29,417,472 floats; relative L2 0.0142116,
maximum absolute difference 0.518419; first changed model layer 1), aligning
with the first QSA hash divergence at accepted length 124. Slot-0 output stayed
exact for 96 tokens. Minimum host/admission availability was 16.78 GiB over 65
samples with zero cgroup events. A first multi-position attempt allowed the
engine to return to solo mode after the peer exited and captured only position
121; that incomplete attempt is excluded. The corrected harness pins the slot
route. Phase 5 remains open.

A delayed-admission target-only control matched serial GDN state through
committed positions 116–118, then first differed at position 119/model layer
12 (21,504,738/29,417,472 values; relative L2 0.00779578, max absolute
0.380125); at position 120 its first changed layer remained 12. Output matched
for 96 tokens. In MTP2, GDN remained exact at positions 120/121 and first
changed at 123/model layer 1. `STRATA_NO_BATCH_KV_STEP=1` and
`STRATA_DEC_BATCH=0` delayed-admission ablations both preserved the MTP2 QSA
onset at length 124 after exact lengths 121/122; each retained exact 96-token
output. This excludes either batched append or decoder compute as the sole
source in that controlled MTP2 case. MTP is not required for all batch-state
drift, though it changes the sampled onset and first layer. Phase 5 remains open.

The exact 48-token delayed-admission controls were extended through positions
116–120 for target-only decode and through 164 for MTP2. Target-only GDN state
first differed at position 119/model layer 12; MTP2 state first differed at
position 123/model layer 1 after exact positions 120/121. The two MTP2
per-token append/decoder ablations retained the first QSA hash difference at
length 124. All tested 96-token outputs matched serial, but the persistent
state drift remains unexplained and has no quality bound. maestro1 then
completed the one-job HIP build for the synced verifier/generator sources and
the configured `strata --help` check. Its separate SYCL overlay had no pending
build work and passed its configured help check; neither backend was run on an
accelerator. Details and logs are in the [batch-MTP report](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

The latest [MTP2 position-76 committed-state comparison](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md)
paired batch and serial rows by token. Prompt 0's 36-layer GDN state differs
in 26,965,859/29,417,472 floats (relative L2 0.0182307), first at GDN model
layer 4; the first four model layers are exact. Its 64-token output matches
serial. Prompt 1 has no capture at that accepted position. Batch QSA hashes
stop at state length 69 while serial reaches 77, so this does not locate an
earlier QSA difference. It is a state diagnostic only; Phase 5 remains open.

A fresh instrumented MTP2 run now pairs prompt 1's batch and isolated serial QSA
hashes at lengths 70, 72 and 74 (exact), then finds all 12 QSA layers changed
at lengths 76 and 77, beginning at model layer 3. Prompt 0 also differs across
all 12 QSA layers at length 77. Both ten-token outputs still match serial. This
reproduces an earlier QSA-state difference, but does not identify its cause or
prove it causes the output mismatch. The opt-in trace is diagnostic and adds
host-copy overhead. Details and the capture/analyzer scripts are in the linked
batch-MTP report; raw logs and hash streams remain local-only.

A component split of those hashes shows both QSA indexer state and QSA K/V
cache state matching serial through accepted length 74, then differing across
all 12 layers at lengths 76 and 77, beginning at model layer 3. Both ten-token
outputs remain exact. This confirms the divergence reaches both state groups,
but does not tell whether an upstream input difference or separate update
errors produce them. The supervised run retained 16.53 GiB minimum host and
admission availability with zero cgroup events.

Two same-profile negative controls set `STRATA_NO_BATCH_KV_STEP=1` and
`STRATA_DEC_BATCH=0` separately. Both retain the same exact-through-length-74
and first-difference-at-76 QSA indexer/KV pattern, with matching ten-token
outputs. This rules out the batched append path and batched decoder compute as
the sole cause for this repro. Minimum host/admission availability was at least
16.40 GiB in both runs, with zero cgroup events. No performance inference is
drawn from these ablations.

A concurrent duplicate-prompt MTP2 control found both batch slots' hashes equal
across all 12 QSA indexer and K/V groups at length 77, while each
differed from serial across all 12 groups. Their generated ten-token outputs
were exact. This rules against a disagreement between the two live rows for
identical inputs, but confirms batch-versus-serial persistent QSA drift can
occur without different prompt content. The run retained at least 16.37 GiB
host/admission availability and zero cgroup events. Phase 5 remains open.

A separate [MTP2 cancellation test](../../bench/results/2026-10-22-phase5-coder-mtp2-cancel-state/README.md)
passed at five accepted-prefix lengths (48, 50, 51, 53, 55). The canceled
request's token sequences and all state fingerprints matched two fresh
exact-length references; same-service recovery returned `Hello Orin!`.
Minimum host/admission availability was 13.18/12.53 GiB across 98 samples,
with zero cgroup memory events. This adds one bounded cancellation cell, not a
long-chain drift bound or multi-live batch-MTP qualification.

A [batch-MTP state/logit follow-up](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md)
captures full verifier rows and committed GDN arrays/hashes for the two-live
request reproducer. In target-only mode, the row mapped to prompt 0 matches
serial GDN hashes at positions 70 and 71, then differs at position 72 in
ordinals 5–35. The row mapped to prompt 1 matches at position 68, then differs
at 69 in ordinals 4–35. In MTP2 mode, the mapped prompt-1 row matches at
positions 68, 70, 72 and 74, then differs at 76 in ordinals 2–35. The MTP2
peer has no exact shared committed length in this sweep. The prompt-0
target-only request still returns identical 96-token text while its recurrent
state drifts; prompt 1 first differs in output at token 60. At position 127,
serial target-only and two-row target-only logits differ in 248,319/248,320
values (relative L2 0.03960), and their close top-two scores reverse order.
Serial MTP2 and batch-MTP differ in all 248,320 logits (relative L2 0.02568),
also reversing the top-two order. One sequential serial server changed the
second prompt versus a fresh process (first output difference at token 62),
so the per-layer sweep uses an isolated serial control for that prompt and
retains the sequential result as a separate session/cache question. These
captures localize state and verifier-row differences but do not identify the
upstream operation or prove GDN drift is the sole cause. Full state dumps stay
local-only. Current ARM64/CUDA focused tests passed 5/5; the modified shared
sources compiled and linked on maestro1 for HIP and SYCL, with both help
commands exiting 0 and no accelerator execution. This is diagnostic evidence,
not a Phase 5 gate pass or performance result.

A later fresh [maestro1 backend rebuild](../../bench/results/2026-10-22-phase5-maestro1-q8-selector-backend-build/README.md)
used an isolated current-worktree source snapshot. All seven shared files
matched their local SHA256 values. HIP and SYCL Release builds completed with
two jobs, and both binaries returned zero for `strata --help`. This is x86
compile/link and CLI-startup evidence only; no accelerator runtime was tested.

A selected-position raw all-layer committed-state run in the same diagnostic
bundle clarified prompt-to-slot pairing. Two position-67 prompt-boundary
captures were both logged against physical slot 0 before the live requests
settled into slots, invalidating the earlier layer-6-only follow-up's
assumption that a physical slot represented one prompt throughout. At generated
position 71, slot 0 was closer to isolated serial prompt 0 (relative L2 0.00940
versus 0.20284), and slot 1 was closer to prompt 1 (0.02314 versus 0.20366).
At position 72 the same assignments held (0.01079 versus 0.17960 for slot 0;
0.01942 versus 0.18092 for slot 1). Both states differed broadly from their
nearest serial controls even though the six generated tokens matched exactly;
both positions covered all 36 GDN layers. This supports short-output/state
divergence but does not explain the longer concurrent token-60 failure. The raw
capture retained 17.69 GiB minimum available RAM and zero cgroup OOM events.
Full arrays remain local-only; this is not a performance result or Phase 5
closeout.

A cap-1 batch-MTP graph lifecycle stress run then exercised the opt-in
`STRATA_BATCH_MTP_GRAPH_LIMIT` override (the default remains 64). Eight
concurrent requests on two slots completed six tokens each across 16 batch
windows. Logs show four graph-layout patterns, 14 LRU evictions, and 11
recaptures after eviction. The supervised run retained 16.50 GiB minimum
available RAM and zero cgroup memory events. This qualifies the forced cap-1
lifecycle only, not the default cap or speed. The updated ARM64/CUDA candidate
rebuilt with two jobs and focused accepted-window, batch-parity and graph tests
passed 5/5. A later fresh maestro1 scratch-volume build also compiled and
linked the latest shared sources for HIP and SYCL, with both help checks passing.
This remains Phase 5 diagnostic evidence, not a gate pass.

A no-override single-live-request check confirmed the batch-MTP graph limit
remains 64 and its six generated tokens matched serial MTP2 exactly. Minimum
available RAM was 16.97 GiB with zero cgroup OOM events. The full configured
CUDA CTest suite passed 130 tests with two optional IQ-fixture tests skipped
when the external one-layer Q2_0 S2 fixture was supplied. The initial run
without `STRATA_TEST_EXPERTS_BIN` failed only `pool_test` for the missing
fixture; the fixture-backed rerun passed it.

A supervised 80-request default-cap stress run exercised 88 unique batch graph
layouts with batch-MTP enabled. The first LRU eviction occurred after exactly
64 unique layouts, followed by 26 evictions; all 80 requests completed. Across
784 supervisor samples, minimum host/admission availability was 11.12 GiB and
cgroup low/high/max/OOM counters remained zero. This verifies default-cap
lifecycle and memory-headroom behavior only; it makes no serial-state, output
quality or performance claim. The test took 811 seconds. See
[`2026-10-22-phase5-coder-batch-mtp-graph-limit64`](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-limit64/analysis.json).

The current-source ARM64/CUDA candidate then passed 28/28 focused
`native_expert` and `pool_test` cases with the external layer-0 S2 fixture,
including the new opt-in comma-list and reciprocal-SiLU selector contract
checks. The candidate’s CUDA route remains unchanged when the selectors are
unset; these CPU arithmetic hooks are diagnostic and have not fixed the
accepted-state mismatch. Details and reproduction are in the
[regression record](../../bench/results/2026-10-22-phase5-current-source-regression/README.md).

A current-source ARM64/CUDA 12.6 Release rebuild completed with two build jobs. The configured CTest suite passed 130 tests with the external one-layer Q2_0 S2 fixture supplied to the two pack-backed tests; two optional IQ-fixture tests skipped because their external fixtures are absent. Integration Python discovery passed 163/163. The NInfer import manifest verified 1,320 imports at pinned revision `b07248f2`; the matrix validator reported 162 proposed cells / 936 paired entries without executing them. These are current regression and specification checks, not Phase 5 or Phase 6 closeout. The initial missing-pack run is retained in the linked regression report.

A fresh [current-worktree regression rerun](../../bench/results/2026-10-22-phase5-current-source-regression/README.md) rebuilt the ARM64/CUDA candidate with two jobs and passed the focused accepted-window, verifier/GDN/KV, graph, Q8_1 and native-expert selection (29/29), plus Python integration discovery (163/163). The full configured CTest suite completed 132 tests with the external one-layer Q2_0 S2 fixture supplied through `STRATA_TEST_EXPERTS_BIN`: 130 passed and two optional IQ-fixture tests skipped. This includes passing `expert_parity` and `pool_test`; the initial missing-pack issue and fixture/source hashes remain documented. The full 48-layer arena-load test remains unrun. This is regression coverage only; Phase 5 accepted-state drift remains unresolved.

A fresh [accepted-state boundary capture at position 515](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-source-boundary-position515/README.md) completed for the Coder IQ1_M short/long/short sequence. Delayed control reproduced the layer-16 verifier input, routes/weights, expert outputs, combined output, all captured residual/hyperconnection fields, and layer-17 GDN state bitwise. Adaptive recovery emitted the same short-request tokens, but its layer-16 verifier input already differed in all 2,560 values (relative L2 0.01280); expert IDs stayed fixed while weights and all captured expert/combined outputs changed. Its layer-16 boundary also changed, and layer-17 post-GDN state differed in 796,657/817,152 values (relative L2 0.00443) despite an exact pre-GDN state. Initial short-request captures matched across arms. This establishes that drift precedes the captured layer-16 expert computation, but does not locate its origin earlier in the network or qualify accepted-state recovery. Both supervised arms retained at least 14.09 GiB host/admission availability with zero cgroup events. Phase 5 remains open.

An [all-layer verifier-input follow-up at the same position](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-source-all-layer-input-position515/README.md) found the first captured adaptive recovery difference at the input to model layer 12; delayed control and cross-arm initial inputs were exact at all 48 layers. Adaptive remained different through layer 47, with relative L2 0.000632 at layer 12. This moves the observed onset earlier than layer 16, but the origin before layer 12 remains unknown. The all-layer pair passed with 14.22/14.32 GiB minimum host availability and no cgroup events. This remains a one-prompt correctness localization, not Phase 5 exit evidence.

A further [layer-11 boundary and layer-12 GDN pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-source-layer11-boundary-position515/README.md) found adaptive recovery's first changed captured boundary field in layer-11 `bo`: 2,560/2,560 values differ (relative L2 0.000102), while `R` and `inj2` remain exact. The layer-12 read and post-GDN state then differ, although its pre-GDN persistent state is exact. Initial captures matched across arms and delayed recovery stayed bitwise exact. This narrows the observed onset to the layer-11 `bo` boundary for this single sequence; the responsible layer-11 operation remains unknown. Minimum host availability was 14.17/14.28 GiB and cgroup events were zero. Phase 5 remains open.

A [same-input layer-11 owner/output capture and oracle](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-source-layer11-owner-output-position515/README.md) now isolates expert 201 (IQ2_S/IQ4_NL) within that boundary. Adaptive recovery moves experts 201 and 63 CPU-to-GPU with unchanged layer input, IDs and router weights; expert 63's output is bit-identical, while expert 201 changes in all 2,560 values (relative L2 4.415e-4). Its service CPU/GPU outputs match the independent `native_expert_parity` outputs bitwise, whose CPU/GPU delta is 4.395e-4. The combined layer-11 MoE output and `bo` boundary change, followed by the layer-12 GDN delta. This links one migrated expert's numerical difference to the observed boundary for the captured token; longer accepted-state drift remains unresolved, so Phase 5 stays open.

A [raw accepted-state follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-state-bound-64pos/README.md) repeated the randomized 64-token short/long/short pair and captured layer-32 committed GDN arrays. Adaptive recovery's recurrent relative-L2 delta from its initial short request grew from 0.00166 at endpoint 515 to 0.02559 at endpoint 534; convolution-state relative L2 grew from 0.00735 to 0.02523. A separate adaptive-only rerun then captured the final endpoint 574: recurrent relative L2 was 0.5243 and convolution relative L2 0.9158, with all values changed and final token IDs 264/1785. All raw captures matched service hashes. The first token mismatch was at output index 23; delayed control retained exact state and tokens. This demonstrates substantial growth in this tested chain, not a general bound. Both paired runs and the endpoint rerun passed supervision with at least 13.93 GiB host/admission availability and zero sampled cgroup events. Phase 5 remains open.

Stage isolation for expert 201 found independent IQ2_S/Q8_1 gate/up dots bit-identical to CUDA gate/up (`0/1,920` differences); CPU hidden F32 was also unchanged when fed the exact GPU activation. After SwiGLU, only 3/60 hidden Q8_1 blocks differed, each by one code byte (32 vs 33) with equal scales and sums. CPU IQ4_NL down on the captured GPU hidden Q8_1 rows matched grouped CUDA output in all 7,680 values. A host replay from captured CUDA gate/up values found that CPU's multiply-by-sigmoid expression reproduces CPU hidden codes, while CUDA's direct-division expression reproduces all GPU hidden codes under both tested code quantizers. Both replays use the same host `std::exp`, so this isolates operation order for this row without establishing CUDA `__expf` equivalence or qualifying an accepted-state fix. A separate activation-quantizer check found stored-sum differences in 78/80 Q8_1 input blocks, but the exact gate/up and down-stage matches indicate that observation did not contribute to this row's output delta. See the raw stage dumps, host replay and supervisor records in the linked oracle directory.

The [layer-11 expert-201 replay record](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/operator-checks/layer11-position515/expert201/README.md) contains the captured input/output hashes and direct reproduction helper. The result narrows this single-row CPU/GPU operator delta to the SwiGLU expression order; it does not qualify broad CPU/GPU arithmetic parity or accepted-prefix recovery. No runtime code changed for this diagnostic.

At the layer-16 expert-118 SwiGLU seam, an [Orin NEON reciprocal replay](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer17-position515/division-formula-trial/neon-reciprocal/README.md) tested zero through three Newton refinements against the captured CUDA Q8_1 hidden blocks. One refinement matched all 60 `d` scales but moved the three one-half-step mismatches to FP16 `s` at blocks 8/28/48; two or three refinements matched `s` but retained three `d` mismatches at blocks 10/30/50. Codes matched in those refined variants, but none reproduced all packed bytes. This rejects a simple NEON reciprocal as the CUDA divide mirror for this row; it does not resolve the accepted-state divergence or establish a general arithmetic bound. A separate [current-source layer-31 expert-22 parity rerun](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer17-position515/division-formula-trial/current-source-recheck/README.md) passed the exact Q8_1 stage and expert-output oracle on the rebuilt binary, while the known layer-32 state divergence remained outside that operator check. Phase 5 remains open.

Phase 8 now has a consolidated [bounded Orin integration profile]
(RELEASE_PROFILE.md), including the current-source Q2_0 profile, reproduction
command, default regression and pinned-control API rollback evidence, and
explicit exclusions. This is an experimental profile for the measured Orin
cell, not a general support claim. Phase 8 remains open pending broader release
gates and the remaining Phase 5/6 work.

A [layer-31 expert-155 follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer11-27-31-mirror-layer32-state-pair/README.md)
with the existing layer-11 and layer-27 Q8_1 mirrors found an identical-input
CPU-to-GPU owner change at layer 31. The IQ3_XXS/IQ4_NL service rows match the
independent oracle; their default CPU/GPU delta is 1.331% relative L2, and the
layer-31 Q8_1 selector makes both outputs bit-identical. In a fresh paired run,
that selector also makes the sampled layer-31 combine and layer-32 raw GDN
state exact across initial/intermediate/recovery requests. Delayed control
remained exact, but adaptive accepted-state fingerprints still differ at all
12 prefixes and the first captured activation difference moves to layer 33.
This is another narrow operator boundary, not an adaptive migration fix or
performance result; Phase 5 remains open.

The adaptive-migration localization has advanced through two further
same-service, randomized short/long/recovery pairs. With layer-1 and layer-3
Q8_1 mirrors, a [layer-4 trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-combined-mirror-layer4-prompt-tail505-511-pair/README.md)
found expert 153 moving CPU-to-GPU at positions 505, 508, and 509; an
independent same-input oracle matched the two service owner rows and the
layer-4 Q8_1 mirror made CPU/GPU outputs bit-identical at the captured input.
Adding that layer-4 rule made the captured layer-5 MoE, GDN intermediates, and
committed state exact across adaptive initial/recovery. A [layer-6 follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-combined-mirror-layer6-prompt-tail505-511-pair/README.md)
then found experts 110 and 162 moving CPU-to-GPU at positions 506–511 with
matching inputs, routes, and weights. Independent native expert oracles match
the service rows; the layer-6 Q8_1 mirror makes both CPU/GPU rows bit-identical
at position 511. The first changed dispatch activation remains at layer 7 for
positions 506–511 and layer 10 for position 505. Both delayed controls stayed
exact and all four supervised arms retained at least 14.17 GiB host/admission
availability with zero cgroup memory events. These are narrow correctness
localizations; adaptive accepted-prefix divergence remains and Phase 5 stays
open. The [layer-7 QSA/MoE capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-combined-mirror-layer7-prompt-tail505-511-moe-only-pair/README.md)
was exact at all seven selected positions; its unsupported GDN hooks are
documented separately because layer 7 is QSA. A [layer-8 trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-combined-mirror-layer8-prompt-tail505-511-pair/README.md)
found expert 196 moving CPU-to-GPU for IQ2_S/Q2_0; its same-input oracle
matched service output and the exact layer-8 Q8_1 mirror made CPU/GPU rows
bit-identical. A [layer-9 trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-combined-mirror-layer9-prompt-tail505-511-pair/README.md)
then localized the next row to expert 235 at position 505; its IQ2_S/IQ4_NL
oracle and layer-9 mirror also match bitwise. Recovery tokens now match for
this 12-token request while terminal persistent fingerprints still differ.
The [layer-10 trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-combined-mirror-layer10-prompt-tail505-511-pair/README.md)
then found IQ2_S/Q2_0 experts 113 and 232 moving CPU-to-GPU; both same-input
oracles match service rows, and the layer-10 mirror makes their CPU/GPU outputs
bit-identical. The following [layer-11/12 capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-combined-mirror-layer11-12-prompt-tail505-511-pair/README.md)
found QSA experts 179 and 201 changing owners; their valid same-input oracles
and layer-11 mirrors also match bitwise. However, the 12-token recovery has no
shared token prefix and layer-12 GDN state differs. Follow-up paired runs found
owner changes at layer 12 for IQ3_XXS/Q2_0 experts 73 and 141; same-input CPU/GPU
oracles join the changed service rows. Adding the exact layer-12 mirror makes
captured layer-12 GDN intermediates and raw state exact, while layer-13 expert
147 (IQ2_S/Q2_0) then changes owners at all seven captured positions. Its
single-row oracles also join the service rows. A layer-13 mirror makes the
selected layer-14 MoE, GDN intermediates, raw state and accepted commit exact,
but the 12-token adaptive recovery IDs then differ at all positions. The
dispatch trace shows IQ2_S/IQ4_NL expert 250 changing CPU-to-GPU at layer 15,
position 505; its single-row CPU/GPU oracle matches the service owner rows.
The layer-15 mirror pair then identified 21 IQ3_XXS/IQ4_NL owner rows at layer
16 across experts 118, 220, 39, and 30; all single-row oracles join to service
outputs. Layer-16 raw recurrent state at accepted position 511 is exact across
recovery although `ffn_y` differs. Adding the layer-16 rule makes selected
layer-16 state and layer-17 MoE outputs exact, and recovery tokens match all 12
positions. All accepted-prefix state records still differ; the first captured
activation difference moves to layer 20, where expert 221 changes owner at
layer 19. Four exact-input oracle rows match service; adding the layer-19 rule
makes sampled layer-20 GDN state/intermediates and layer-21 MoE outputs exact.
Accepted-prefix state still differs, and the first prompt-tail activation
differences now move to layers 25–28. The dispatch trace identifies expert 173
at layer 24, expert 213 at layer 26, and expert 36 at layer 28. The current
paired capture checks layer 24's MoE/GDN boundary. Reports and raw evidence are
linked from the current [Phase 5 trace
bundle](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/).
The hash comparator records no-common-prefix cases without inventing
post-mismatch comparisons.

A same-position [Coder adaptive-migration trace and IQ3_XXS/Q2_0 CPU mirror
check](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/README.md)
found a layer-12 CPU-to-GPU owner change for a native format pair missing from
the earlier Q8_1 diagnostic selector. Extending the opt-in route matched that
real expert's CUDA output bit-for-bit for widths 1–8 and moved the first
captured activation divergence from layer 13 to layer 26 in one randomized
short/long/short comparison. The delayed control had no captured activation
divergence. Adaptive recovery tokens matched the initial short request and the
delayed control, but all 16 accepted-prefix state records still differed from
the adaptive initial short state; the remaining divergence is unresolved. The
Ten focused Orin CTests covering accepted windows, verifier/state parity, CPU
Q8_1 mirrors and the selector contract passed; the full integration Python
suite passed 163/163. A fresh GDN dump comparison reproduced the report's
numeric delta while validating both dumps against their logged per-layer
hashes. This is
correctness localization, not a migration fix or performance result. Phase 5
remains open. Current-source maestro1 HIP and SYCL compile/link plus `strata
--help` checks passed with two jobs; the fresh SYCL build completed 123/123
steps using its migrated `generate.cpp` overlay. This is x86_64 build evidence
only, with no accelerator runtime claim. See the backend report in the linked
result bundle.

A subsequent 64-token accepted-prefix pair extended the same Coder IQ1_M
workload. Token IDs still matched between initial short and recovery requests,
but adaptive state first differed at zero-based accepted prefix 8 and remained
different through prefix 63; delayed-control state and per-layer GDN hashes
matched at all 64 prefixes. The first adaptive GDN hash differences were
ordinals 24–35. Both supervised arms passed with 14.14 and 14.32 GiB minimum
host/admission availability and zero cgroup events. This shows the earlier
16-token recovery parity did not qualify longer accepted chains, without
identifying the first divergent operation. See the
[64-token trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/reproduction-q8-cuda-input-quantizer-long64/README.md).

A same-day [multi-position follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-state-prefix8-capture/README.md)
captured positions 511–520 across all layers. The first adaptive accepted-state
mismatch remains prefix 8 at verifier position 519, with GDN ordinals 24–35
(model layers beginning at 32) changed. At that position, the first changed
captured MoE input is layer 32 (relative L2 `1.4294e-5`, maximum absolute delta
`5.2571e-5`); expert IDs match there but owner placement differs. Delayed
control remained exact at all captured positions. Earlier adaptive activation
differences did not yet change committed-state hashes. This narrows the
boundary without proving a causal operation; Phase 5 remains open.

A verifier-level [layer-31/layer-32 follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-state-prefix8-verifier-capture/README.md)
strengthened the localization. At position 519, layer-31 IDs and router
weights matched; adaptive migration moved expert 22 from CPU to GPU, and its
service verifier contribution changed in 2,559/2,560 values. The weighted
layer-31 combine then differed in 2,555/2,560 values (relative L2
`3.38419e-5`), followed by changed layer-32 GDN input `x`; delayed control was
bit-identical. The same-input oracle found expert 76 bit-exact and expert 22
different across CPU/GPU. This strongly implicates layer-31 expert-22 arithmetic
as the immediate source of the observed layer-32 input change. A subsequent
[raw committed-state capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-state-prefix8-committed-raw/README.md)
confirmed that the serving layer-32 recurrent matrix first differs at accepted
position 519 (564,534/786,432 values; relative L2 `1.28332e-7`), while its
convolution history remains exact. The raw per-layer hash matches the service
fingerprint; delayed control is bit-identical at positions 518–520. This
confirms the committed-state boundary but does not establish an accuracy
winner. Both supervisors passed with at least 14.22 GiB minimum
host/admission availability and zero cgroup events. Phase 5 remains open.

A same-input [expert-22 Q8_1 stage check](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/operator-checks/layer31-position519/README.md)
compared the actual captured layer-31 activation with the independent native
expert harness. CPU and CUDA input Q8_1 blocks and all 1,920 gate plus 1,920 up
dot values matched bitwise under mode 0. After SwiGLU, 3/60 hidden Q8_1 blocks
differed only in the FP16 `d` scale by one representable step; their sums and
integer codes matched. The default Orin mode produced the same CUDA hidden Q8_1
bytes as explicit mode 0. Replaying down projection on those CUDA-produced
hidden blocks yielded bit-identical CPU IQ4_NL and grouped CUDA outputs
(0/7,680 words different). This localizes the numeric seam to SwiGLU output or
its hidden quantization scale; the exact operation is not isolated. Phase 5
remains open.

The explicit reciprocal-sigmoid CPU operation order made the captured
layer-31 expert-22 CPU/CUDA outputs and hidden Q8_1 blocks bit-identical.
However, the [broad operation-order pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-state-prefix8-reciprocal-silu-check/README.md)
changed 40/64 adaptive recovery tokens. Restricting it to layer 31 kept output
tokens equal but did not restore transaction state: the [targeted pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-prefix8-layer31-silu-check/README.md)
found the layer-32 committed state already differed at position 518. Delayed
controls were exact in both pairs, and raw state captures matched their service
hashes. This is operator-level parity evidence, not a state-migration fix; the
arithmetic remains opt-in and Phase 5 stays open.

The [current worktree cross-backend rebuild](../../bench/results/2026-10-20-phase5-maestro1-current-worktree-rebuild/README.md)
refreshed maestro1's isolated source copy with the exact current C++/header
hashes, including the committed layer-aware native-expert declaration. HIP and
SYCL compiled and linked, and both binaries passed `--help`; the first HIP
attempt used a stale header in that remote copy and failed before the source
refresh. The Orin Release CUDA/SM87 targets then rebuilt from this worktree. A
focused accepted-prefix, verifier, GDN, KV, graph lifecycle, native expert and
selector selection passed 13/13; integration Python discovery passed 163/163.
The current build and test logs are retained in the [Orin current-source check
record](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/checks/orin-current-source/README.md).
This confirms build and selected contract coverage only; it provides no
HIP/SYCL runtime or performance result and does not resolve adaptive state
divergence. Phases 5 and 8 remain open.

A shorter [position-518 route trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position518-layer31-only-trace/README.md)
with the mirror limited to layer 31 found the first changed MoE input at layer
2, expert IDs first changed at layer 3, and adaptive owner placement first
changed at layer 6. Layer-32 committed state already differed at position 518,
although the 12 initial/recovery output token IDs matched. Delayed control was
exact across routes, outputs and captured state. This demonstrates earlier
owner-dependent work remains to be localized; it does not attribute the
position-518 delta to a particular operator. Phase 5 remains open.

A [layer-1 verifier follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position518-layer1-verifier/README.md)
at the same accepted position found identical initial/recovery router routes,
all ten expert contributions, shared-expert output and combined MoE output at
layer 1. The first changed dispatch input remained at layer 2 (all 2,560
values), so the captured layer-1 MoE path is excluded; the post-combine
residual/hyper-connection and layer-2 GDN transition remain unseparated.
Delayed control was exact, while adaptive output tokens matched but terminal
state fingerprints changed. Phase 5 remains open.

A same-input [layer-25 owner trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-owner-position505-506/README.md)
directly ties the position-505 adaptive divergence to expert 183 changing from
CPU to GPU at layer 25. Its input, route IDs and weights match bitwise; the
captured CPU and GPU outputs each match the corresponding same-input
`native_expert_parity` result exactly, but differ from one another by 1.2575%
relative L2. The combined layer-25 MoE output differs at position 505 and is
exact at position 506. Delayed control is exact at both positions. This
narrows the first observed boundary to owner-dependent IQ3_S/IQ4_NL expert
arithmetic, but does not yet qualify long-chain state drift or answer quality.
Both supervised arms passed at 14.17 and 14.31 GiB minimum host/admission
availability with zero sampled cgroup events. Phase 5 remains open; this is a
diagnostic result, not a migration fix or performance claim.

An opt-in CUDA-order CPU Q8_1 mirror for IQ3_S/IQ4_NL now makes expert 183's
captured layer-25 CPU and GPU outputs bit-identical. In a repeated same-service
pair with that mirror active, initial/recovery activations and combined layer-25
MoE output match at positions 505 and 506, but adaptive accepted-state
fingerprints still differ. A [position-520 trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-generated-position520/README.md)
found the first route-owner changes at layers 2 and 3 and the first activation
difference at layer 4. Layer-26 GDN input `x` was already different; the
delayed control remained bit-identical through the same captures. The adaptive
state mismatch therefore persists beyond the fixed-row operator difference,
and its first cause remains unresolved. Both arms passed supervision, retaining
14.25/14.36 GiB minimum host/admission availability and zero sampled cgroup
events. Phase 5 remains open.

A [generated-position-520 operator trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer3-generated-position520/README.md)
then captured the earlier layer-3 boundary. Expert 182 (`IQ2_S`/`IQ4_NL`)
changes from CPU to GPU on identical input, IDs and router weights. The two
service expert outputs match independent same-input CPU/GPU parity outputs
exactly, but differ from each other by 0.2819% relative L2. It is the only
changed routed expert row at that layer; the combined MoE output changes and
layer 4 is the first changed activation. The opt-in Q8_1 CPU mirror reduces
this row difference from 1.82% to 0.2819%, but does not remove it. The CPU
down projection on the GPU-produced hidden activation matches grouped CUDA
exactly, while the post-SwiGLU hidden Q8_1 blocks differ. The remaining
owner-dependent arithmetic boundary is before the down projection; the first
persistent-state write and complete recovery parity remain unresolved. A
separate opt-in hidden-stage capture with the existing unfused GPU path found
the CPU/GPU pre-quantized SwiGLU floats differ in all 1,920 values (relative
L2 0.00100083, maximum absolute difference 0.00019974); its GPU Q8_1 output is
bit-identical to the default fused path. This confirms the discrepancy is
present before hidden quantization, while gate/up and SwiGLU arithmetic remain
unseparated. Both
arms passed supervision with 14.22/14.37 GiB minimum host/admission
availability and zero cgroup memory events. The first optional input-quantizer
check exposed a host-oracle rounding mismatch and remains retained as a failed
checker cell. A corrected independent check now passes CPU code and both
stored-sum formulas; CUDA codes are exact or within one step (one block).
CPU/GPU stored sums differ by their documented GGML versus CUDA encodings.
This does not change the routed-row or state findings. Phase 5 remains open.

A follow-up corrected the Q8_1 input producer used by the opt-in CPU mirror to
match the grouped CUDA reduction and rounding contract. In a fresh same-service
adaptive/delayed pair, adaptive ownership still flipped at 14 layers, but the
captured dispatch activations and expert IDs matched across all 48 layers at
position 520. The layer-3 expert-hit rows (25,600 values), shared output,
combined MoE output and layer-26 GDN verifier fields were bit-identical. The
adaptive recovery also matched its initial short request's 16 token IDs and
nine accepted-state fingerprints. Two further same-service pair campaigns,
with the third reversing arm order, also matched all 16 recovery token IDs and
all nine accepted-state fingerprints in both arms. All six supervised runs
passed; minimum host/admission availability across them ranged from 14.03 to
14.32 GiB with no cgroup memory events. This is correctness evidence for one
model and workload, not broad migration qualification or a performance result;
the selector remains opt-in. All 11 Q8_1 selector/window CTest cases and the
163-test integration Python suite passed on this source. maestro1 rebuilt HIP
`strata` and `native_expert_parity`, passed the Strata help and GPU-free
selector-contract checks, and rebuilt the SYCL `strata` target with a
successful help check; the report distinguishes these x86_64 checks from
accelerator execution. Phase 5 remains open. See the
[quantizer follow-up report](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer3-generated-position520/README.md#cuda-order-q8_1-activation-quantizer-follow-up)
and [backend report](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/backend/maestro1-current-q8quant-2026-10-19/README.md), plus the retained raw pairs.

An earlier [layer-25 CPU-row capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/README.md#layer-25-cpu-row-follow-up)
joined the initial and recovery prompt at position 511. The route input, IDs
and owners matched, and the three CPU-owned expert rows matched bitwise across
7,680 values. This ruled out those rows for that position; later verifier
captures extended the comparison to GPU rows, router weights, shared output,
and the combined MoE vector.

A same-service [layer-25 verifier capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-verifier-parts/README.md)
then compared the router and all ten expert rows at position 511. Initial and
recovery token IDs, expert IDs, and router weights matched; all 25,600 FP32
values after expert-hit accumulation were bit-identical. This excludes the
captured routed-expert path for this row. A paired follow-up found the shared-
expert output and combined MoE vector bit-identical too; the remaining boundary
is after combine, at residual/hyper-connection application or the next recurrent
state transition. A same-service layer-26 GDN trace found identical per-token
inputs through `z` but a first difference in recurrent output `y` (5,152/6,144
values). A paired verifier-state snapshot found a pre-existing difference in
the incoming recurrent matrix (688,243/786,432 values) while convolution history
matched exactly. This narrows the immediate boundary but does not identify which
earlier token or operation caused it; the snapshot is verifier-owned, not the
serving session's accepted-prefix state. The
initial expert-parts capture passed with 14.31 GiB minimum host/admission
availability, 10.85 GiB maximum scope use, and zero cgroup events. The
shared/combined output capture passed with 14.37 GiB minimum availability,
10.92 GiB maximum scope use, and zero events. The layer-26 GDN trace passed
with 14.36 GiB minimum availability, 10.77 GiB maximum scope use, and zero
events. The verifier-state snapshot passed with 14.35 GiB minimum availability,
10.37 GiB maximum scope use, and zero events; see the linked report for raw-file
identity and state deltas in [the experiment bundle](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-state-pair/README.md).
maestro1 HIP recompiled the verifier for each diagnostic increment and for the
state capture, and passed `strata --help`; the SYCL overlay reported no work
and passed help. These are x86 compile/CLI checks only. Phase 5 remains open.

The follow-up [prefill-boundary capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prefill-state-comparison/README.md)
found bit-identical layer-26 state at all eight captured ends of the initial and
recovery short-request prefill chunks, including exact raw-state equality at
boundary 505. The verifier pre-state at position 511 still differed in the
recurrent matrix while its convolution history matched. This places the observed
change after the captured prefill and before verifier capture, without naming a
specific transition because the samples are at different boundaries. The
28-GiB run passed with 14.33 GiB minimum availability and zero cgroup events.
Current-source maestro1 HIP rebuilt and linked; SYCL had no source work. Both
CLI help checks passed. This remains a diagnostic, not a correction or
performance result; Phase 5 remains open.

The subsequent [accepted-commit state trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-commit-state-trace/README.md)
narrowed the first captured divergence to layer-26 GDN state after the commit
ending at position 506. Initial and recovery token IDs matched. Recurrent state
and part of convolution history differed at 506; convolution history was exact
again at 508 while the recurrent matrix remained different. Position-510
committed state matched the earlier position-511 verifier pre-state byte-for-
byte in both requests. This identifies the first changed accepted-window
boundary after the bit-identical prefill snapshot, but it does not separate the
individual token computations inside that window or establish cause. The Orin
run passed at `MemoryMax=28G`, with 14.31 GiB minimum availability, 10.90 GiB
peak scope use and zero cgroup events. Phase 5 remains open.

An attempted `--spec 1` ablation could not split that two-token window: native
Coder packs reject `--spec < 2` before model loading. No runtime data was
collected, and the unsupported cell is retained with the trace. The current
evidence locates the first difference to endpoint 506; token-level separation
inside that supported window remains open.

The trace's per-layer accepted-prefix hashes now localize the adaptive state's
first mismatch: at the first recovery token, GDN ordinals 20–35 differed from
the initial short request, while ordinals 0–19 matched. Ordinal 20 maps to
model layer 26 with QSA interval 4, matching the first changed dispatch input;
delayed recovery matched all GDN hashes. The switched layer-24 expert 173 also
passed a captured-activation CPU/CUDA output oracle, so that isolated operator
does not explain the later state boundary. See the report's updated analysis
and `operator-checks/`. This narrows the follow-up target but does not identify
or fix the migration cause.

Two raw GDN state dumps at the same `L=512` accepted prefix now quantify this
boundary. Initial-state hashes were identical across the separate supervised
runs, and the recovery dump matched all per-layer hashes in its accepted-prefix
log. GDN ordinals 0–19 remained bit-identical; ordinals 20–35 differed in
12.92 million of 13.07 million float values. Overall relative L2 was 1.686%
with a 1.403 maximum absolute difference. Raw dumps remain outside Git under
`~/models/strata-orin-validation/experiments/phase5-gdn-state/`; the exact
comparison and supervisor records are linked in the report. This is a state
delta measurement, not an accuracy oracle or a cause/fix claim.

A corrected [layer-2 grouped IQ4_NL Q8_1 mapping](../../bench/results/2026-10-19-phase5-coder-layer2-hidden-q8_1/README.md)
now mirrors the grouped CUDA service reduction schedule. Three randomized,
fixed-residency owner pairs on the Coder IQ1_M artifact matched all 16 accepted-
prefix state fingerprints, completion IDs, prompt-end GDN hashes and captured
device route records. A raw GDN capture at the first accepted prefix also
matched byte-for-byte. The earlier layer-2 owner-placement counterexample and
operator residual were caused by comparing the CPU's standalone four-warp
mapping with the CUDA grouped lane-strided mapping; those pre-fix results remain
in their reports and are superseded for this selector. The CPU route remains
opt-in, and this one model/prompt/operator check has no performance or default-
selection claim. Phase 5 remains open for other formats, state transactions,
speculation, cancellation and broader workloads.

A pre-fix [layer-2 Coder expert oracle check](../../bench/results/2026-10-19-phase5-coder-layer2-operator-oracle/README.md)
reused the same captured position-511 activation for all seven CPU-owned
experts. Each uses IQ2_S gate/up and IQ4_NL down weights. CPU and CUDA expert
outputs differed in all 7,680 F32 values per expert, with relative-L1 deltas
of 1.38%–1.67%; both routes were compared against an FP64 accumulation using
GGML-decoded weights. This confirms a second same-input operator mismatch
downstream of layer 1, but it is not a router-weighted layer reconstruction or
service-level state-causality result. The 28-GiB scopes retained 24.51 GiB
minimum host/admission availability and zero cgroup events. Adaptive migration
and Phase 5 remain unqualified.

An earlier opt-in [layer-2 IQ4_NL CPU Q8_1 arithmetic mirror check](../../bench/results/2026-10-19-phase5-coder-layer2-q8_1-mirror/README.md)
matched standalone CUDA MMVQ, but not the grouped service kernel's lane-strided
reduction schedule. Its reported full-expert residual and paired service state
differences were measured before the correction linked above. The corrected
grouped mapping removed those differences in the fixed-residency pair sample;
it remains opt-in and adaptive migration is still unqualified. Current-source maestro1
HIP/SYCL compile/link and CLI-help checks passed, with no accelerator runtime
claim; see the [backend report](../../bench/results/2026-10-19-phase5-coder-layer2-q8_1-mirror/backend/maestro1/README.md).
Phase 5 remains open.

An opt-in [IQ3_XXS/IQ4_NL Q8_1 CPU mirror diagnostic](../../bench/results/2026-10-19-phase5-coder-layer0-iq3xxs-q8_1-mirror/README.md)
extended the CUDA-lane-order CPU dot to a captured layer-0 Coder expert. On the
two-row service activation, CPU-vs-CUDA expert relative L1 fell from 1.52% on
the default CPU path to `2.46e-8`; the IQ4_NL down projection matched exactly.
All six Q8_1 operator CTests passed. A same-binary fixed/adaptive service pair
enabled all supported Q8_1 CPU pairs, so it did not isolate IQ3_XXS. Its
persistent-state hashes differed on every request; output IDs differed by
10/16 on adaptive short/recovery and 3/16 on the fixed long request. The
format-specific [IQ3_XXS/IQ4_NL-only service diagnostic](../../bench/results/2026-10-19-phase5-coder-layer0-iq3xxs-only-service/README.md)
then enabled only that expert pair. With no accepted speculative drafts, it
still changed 6–7 of 9 persistent-state fields on every request, and changed
token IDs by 10/16 and 3/16 in the adaptive short/long requests and by 10/16 in
the fixed short, recovery and continuation requests. This does not isolate one
layer or qualify migration/state parity. The selector remains opt-in and
Phase 5 remains open.

The [layer-0 IQ3_XXS/IQ4_NL follow-up](../../bench/results/2026-10-19-phase5-coder-layer2-hidden-q8_1/iq3xxs-layer0-service-followup/README.md)
corrected a parity-harness omission: `native_expert_parity` had not passed the
requested layer into `native_fmt`, so its layer-scoped selector was not active
in those replays. With that fixed, seven CPU-owned experts from a live layer-0
service dispatch matched the service CPU outputs and grouped CUDA outputs
bit-for-bit on the captured activation. A paired layer-0 capture also found
identical verifier input, IDs, weights and owners at position 511; the seven
weighted CPU expert-output deltas reconstructed the combined `ffn_y` delta
with `1.116e-5` relative-L1 residual. Later completion IDs differed at 10/16
positions and all 16 accepted-prefix fingerprints differed, so the selector's
state and output effect remains real. This localizes the first combined layer
change to the opt-in activation-format arithmetic for that row; it does not
qualify the route as a default or establish broad quality. Phase 5 remains open.

The current-source [maestro1 HIP/SYCL rebuilds](../../bench/results/2026-10-19-phase5-coder-layer2-hidden-q8_1/backend/maestro1/README.md)
passed compile/link with two jobs. HIP `strata --help` exited 0. SYCL
`strata --help` could not run because maestro1 had no SYCL device available;
that is recorded separately from the successful build. These are x86_64 build
checks only, not accelerator execution or Orin performance.

A new supervised [Q2_0 short→long→short check](../../bench/results/2026-10-18-phase5-q2-short-long-short/README.md)
on the selected MTP-off, fixed-residency profile returned the same exact
512-token retrieval-and-sum answer before and after an uncached 7,498-token
retrieval. All three long-prompt markers appeared once and in order. Independent
review passed; minimum host/admission availability was 17.89/11.75 GiB across
343 samples, with zero observed cgroup events. This adds one same-service
functional state-recovery sequence; it does not prove persistent-state identity
or resolve the separate IQ1_M adaptive-migration divergence. Phase 5 remains
open.

A seven-block current-source [Q2_0 prefill-chunk confirmation](../../bench/results/2026-10-18-phase6-q2-current-source-prefill-confirm7/README.md)
repeated the selected 512-token retrieval-plus-arithmetic comparison on the
current candidate binary. All 14 fresh-service answers matched the exact
47-token oracle. Chunk 128 reduced paired median request time 40.75% (95%
interval −40.86% to −37.56%) and prompt time 48.21% (−48.50% to −46.49%);
decode change included zero. Paired request-window `VIN_SYS_5V0` energy per
output token fell 40.04% (−40.53% to −37.74%), but this rail includes board
idle/background activity and is not process energy. Minimum host/admission
availability was 18.06/14.70 GiB over 1,209 samples, with zero cgroup events.
This repeats an existing task at current source and supports the bounded
chunk-128 test profile only; no default changed and Phase 6 remains open.

Phase 6 has selected one bounded Q2_0 test profile for Phase 7 qualification:
FP16 KV, 8K context, MTP off, 3,000 expert slots, prefill chunk 128, eight
workers and prompt cache/adaptive swaps disabled. This is not a default or
general support claim. A supervised 30-minute 512-token retrieval-plus-sum
soak on that exact profile passed 101/101 exact-answer checks, with 17.73 GiB
minimum host and 8.51 GiB minimum admission availability. A separate selected-
profile 7,498-token 8K recall and same-service recovery check also passed, with
17.96 / 11.75 GiB minimum host/admission availability. The retained [soak
report](../../bench/results/2026-10-17-phase7-q2-prefill128/sustained-512/README.md)
and [recall report](../../bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/README.md)
include independent review and raw telemetry. The selected-profile seven-case
API suite passed, and separate checks confirmed decode cancellation and active
prefill cancellation at 256 of 7,498 tokens, each followed by same-service
recovery. See the [protocol report](../../bench/results/2026-10-17-phase7-q2-prefill128/api-cancel-recovery/README.md)
and [active-prefill report](../../bench/results/2026-10-17-phase7-q2-prefill128/api-prefill-cancel/README.md).
The selected profile also passed three sequential fresh-service teardown
cycles with independent response and process-exit review; see the
[teardown report](../../bench/results/2026-10-17-phase7-q2-prefill128/teardown-3cycle/README.md).
The bounded Phase 7 matrix is now complete. Process-energy attribution and
broader Phase 6 interactions remain open.

The selected Q2_0 MTP-off profile also passed [16K](../../bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/README.md),
[32K](../../bench/results/2026-10-17-phase7-q2-prefill128-32k-selected-profile/README.md),
[64K](../../bench/results/2026-10-17-phase7-q2-prefill128-64k-selected-profile/README.md),
and [128K](../../bench/results/2026-10-17-phase7-q2-prefill128-128k-selected-profile/README.md)
near-limit retrieval and same-service recovery cells. The 15,003-, 30,032-,
60,071- and 120,149-token prompts each returned all three planted markers once
and in order, followed by `RECOVERED`. Minimum host/admission availability was
17.72/10.15 GiB at 16K, 17.52/11.89 GiB at 32K, 16.68/11.32 GiB at 64K and
15.02/11.73 GiB at 128K across 611, 1,106, 2,186 and 5,092 supervised samples;
all runs had zero cgroup memory events. This extends the exact selected profile
from 8K through one 128K capacity point. The 64K prompt took 2,251.7 seconds
at 26.7 tokens/s and the 128K prompt took 5,302.2 seconds at 22.7 tokens/s for
prefill. The 128K client request took 5,311.3 seconds. The selected profile also passed a
held-out [32K retrieval-plus-arithmetic task](../../bench/results/2026-10-17-phase7-q2-prefill128-32k-quality-mtp-off/README.md):
all three markers appeared once and in order, the independent suffix oracle
returned `1971`, and same-service recovery passed. That run retained 17.42/11.48
GiB minimum host/admission availability over 1,081 samples with zero cgroup
events. The separately tested contexts and quality cells are not a general
support claim; see the Phase 7 closeout for boundaries and exclusions.

The selected Q2_0 MTP-off profile also passed one [256K retrieval and recovery
cell](../../bench/results/2026-10-17-phase7-q2-prefill128-256k-selected-profile/README.md):
all three markers were returned once and in order from a 240,286-token uncached
prompt, followed by same-service `RECOVERED`. Independent review passed. Across
31,442 samples, minimum host/admission availability was 11.64/11.64 GiB and
cgroup memory events remained zero. Engine prefill took 32,851.9 seconds
(7.3 tokens/s). This is one functional capacity point with no energy
attribution, not repeated quality or sustained 256K evidence; Phase 7 remains
closed for the bounded matrix.

The selected profile also passed one [128K held-out retrieval, arithmetic and
recovery task](../../bench/results/2026-10-18-phase7-q2-prefill128-128k-heldout-quality/README.md).
The independent input review confirmed a 120,141-token uncached prompt with new
markers near 10/50/90%; the service returned all three in order and the
independent suffix oracle verified `417 + 638 + 925 = 1980`. Same-service
recovery returned `RECOVERED`. Across 5,528 samples, minimum host/admission
availability was 14.64/11.41 GiB with zero cgroup events. Prefill took 5,751.5
seconds at 20.9 tokens/s. This is one synthetic quality cell, not a broad score
or performance comparison; see the Phase 7 closeout for scope.

The selected Q2_0 MTP-off profile also passed one [64K retrieval-plus-arithmetic
replication](../../bench/results/2026-10-17-phase7-q2-prefill128-64k-quality-mtp-off/README.md)
of the task previously run under MTP4. The 60,079-token uncached prompt returned
the three codes in order and the independently checked suffix sum `1971`, then
the same service returned `RECOVERED`. Minimum host/admission availability was
16.71/10.74 GiB across 2,224 samples, with zero cgroup events. This is one
profile-specific replication, not a new held-out prompt or broad quality score;
broader quality is outside the bounded Phase 7 closeout.

The selected profile also passed one [two-slot streamed API overlap
check](../../bench/results/2026-10-17-phase7-q2-prefill128-concurrency2-selected-profile/README.md)
with distinct 7,498- and 15,003-token retrievals. Serial and candidate answers
passed exact prompt-count and marker checks; metrics observed two requests in
two active slots. Minimum host/admission availability was 16.86/8.32 GiB over
1,927 samples, with zero cgroup events. The two-slot requests took longer than
the serial controls in this single sequence, so it provides functional overlap
evidence and no latency benefit. Repeated concurrency and broader quality are
not claimed; see the Phase 7 closeout for exclusions.

A same-day [Coder GGUF quantization comparison](../../bench/results/2026-10-17-phase6-coder-quant-comparison/README.md)
then compared Q2_0 and IQ1_M from the same pinned Hugging Face repository
revision. After correcting an exploratory screen's cache-size mismatch, a
randomized three-pair cache-matched screen and seven-pair held-out confirmation
used 3,955 MiB of actual expert cache in every arm. All 14 held-out arms returned
the three planted retrieval markers exactly once and in order. IQ1_M median
prompt time was 30.83% lower (paired-block bootstrap 95% interval −31.12% to
−30.43%); client total time was 31.55% lower (−31.81% to −31.15%). Short
36-token completions make decode throughput less informative. This qualifies
only the tested prompts and Orin configuration; it is not broad answer-quality
evidence or a profile promotion. Phase 6 remains open.

An exploratory Phase 5 [Coder CPU-order recovery attempt](../../bench/results/2026-10-16-phase5-cpu-order-adaptive-recovery/README.md)
is excluded from numerical and quality conclusions. The flag dispatches to a
kernel for the packed Q2_0 expert layout, while this Coder pack stores native,
per-layer GGUF expert formats (including IQ3_XXS/IQ4_NL). The command accepted
that incompatible combination, so its output and state results are not valid
evidence about CPU-order arithmetic. A startup guard now rejects the option for
native packs. The guard built on Orin CUDA and in a targeted maestro1 HIP
service rebuild; the matching Coder config exited with status 2 before serving.
maestro1's HIP result is compile/CLI evidence only. Phase 5 remains open.

A randomized three-block [Coder IQ1_M swap-budget recovery screen](../../bench/results/2026-10-16-phase5-coder-swap-budget-screen/README.md)
completed all 12 arms. The active caps were 1, 8 and 96 swaps per adaptation;
each used the same short/long/short sequence, MTP off, accepted-prefix state
hashes and layer-0 route capture. Cap 8 exactly matched delayed-control recovery
tokens in all three blocks, but five persistent-state fingerprints still differed
from the control each time. Caps 1 and 96 differed at all 16 recovery-token
positions versus control in all three blocks, with seven changed fingerprints.
Every adaptive byte and residency verification passed. A three-block
continuation follow-up then found the same cap-8 pattern each time: the 2,048-
token response differed at 3/16 positions, the immediate recovery response
matched, and the next identical short response differed at 16/16 positions;
seven state fingerprints differed. Thus the apparent recovery match conceals a
state divergence that affects continuation. Minimum host/admission availability
was 14.33 GiB across 1,196 continuation samples; cgroup memory-event counters
were zero. Phase 5 remains open.

A seven-block [fixed-residency Coder IQ1_M confirmation](../../bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7/README.md)
reproduced that continuation failure in all seven randomized pairs on the exact
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M snapshot. Cap-8
matched the immediate recovery tokens but differed in five persistent-state
fingerprints each time; the next identical short request differed at all 16
token positions in every block. The delayed-adaptation control restored both
the initial output and state fingerprints. All 14 services passed supervision,
with no cgroup memory events and at least 14.07 GiB host availability. This is
correctness/state evidence, not a performance comparison or a result for other
Coder quantizations. Adaptive migration remains unqualified and Phase 5 remains
open.

A three-block [all-layer Coder trace and CPU/GPU operator oracle](../../bench/results/2026-10-16-phase5-coder-swap-budget-screen/README.md#all-layer-route-trace-and-operator-oracle--2026-10-16)
reproduced the first cap-8 route changes at layer 1 on identical activations and
expert IDs. Short request changes at row 10 preceded layer-2 activation drift;
the long request showed four CPU-to-VRAM changes at layer 1, row 0. Independent
Q8_K/Q8_0 versus Q8_1/Q8_1 reconstruction closely matched all six observed
CPU/GPU expert deltas (0.85%–6.03% residual). This strengthens the arithmetic
mechanism hypothesis but does not prove full service-level causality or clear
the state/continuation failure. The six traces passed supervision with a
13.85-GiB minimum availability; Phase 5 remains open.

A [Q8_1 block comparison](../../bench/results/2026-10-16-phase5-coder-q8_1-quantizer-check/README.md)
compared the actual GGML CPU and CUDA activation producers on captured layer-1
Coder inputs. Across 80 blocks per input, both had identical FP16 scales and
int8 codes, with zero failures against an independent scalar block oracle.
Their stored sum fields differed in 76 and 78 blocks by design: GGML stores
`d*sum(q)`, while CUDA stores the original-input sum. The sampled symmetric
IQ2_S/Q2_0 CUDA dots do not consume that sum; other formats may. This makes a
host Q8_1 dot for these native formats a viable experiment, not an established
operator or service fix. The updated diagnostic target built with CUDA on Orin
and compiled/linked with HIP on maestro1; the latter is compile/usage evidence
only. Phase 5 remains open.

A follow-up [scalar CPU Q8_1 dot diagnostic](../../bench/results/2026-10-16-phase5-coder-q8_1-dot-check/README.md)
ran the actual IQ2_S/Q2_0 layer-1 expert on two captured activations. Its
dequantized-weight CPU oracle differed from CUDA by 9.33e-4 and 6.36e-4 relative
L1; every word differed bitwise on the short row, and 7,677/7,680 differed on
the long row. This supports the operator arithmetic contract but is not an
optimized CPU implementation, speed measurement, accepted-prefix check or
service parity result. All 15 Orin CUDA native-expert parity CTests pass. A
fresh maestro1 HIP rebuild first had a device-link bus error; the single-job
retry with `/mnt/sda2` temporaries linked and passed the usage check (compile/CLI
evidence only). Phase 5 remains open.

The [CPU Q8_1 CUDA-row mirror diagnostic](../../bench/results/2026-10-16-phase5-coder-q8_1-cuda-mirror-followup/README.md)
now implements CUDA's integer IQ2_S/Q2_0 row arithmetic behind an opt-in
environment flag. Synthetic parity and a captured Coder layer-1 expert row
matched CUDA bitwise; all 16 Orin native-expert parity CTests passed. A
randomized three-block active-swap screen then found a repeatable service-level
regression: after matching the initial and recovery answers, the identical
continuation differed at 13/16 token positions in all three mirror arms, while
all three default arms matched at 16/16. Both routes changed the same five
initial-to-recovery state fingerprints. All six arms passed 15/15 swap-byte
and 15/15 residency checks; minimum host availability was 14.22 GiB and
minimum admission availability was 9.35 GiB across 1,264 samples, with zero
cgroup memory events. The mirror is not promoted as a
recovery fix and no speed claim follows. Current-source HIP and SYCL service
builds and CLI checks passed on maestro1; these are compile/link checks only.
The follow-on method for a future Splash integration is recorded in
[PORTING_NOTES.md](PORTING_NOTES.md). Phase 5 remains open.

An opt-in [CPU Q8_1 route screen](../../bench/results/2026-10-16-phase5-coder-q8_1-cpu-route-check/README.md)
then ran one supervised default/candidate pair on the same Coder IQ1_M GGUF
revision. The route was exercised for 549 of 863 shared layer-1 expert calls;
owner choices matched. Recovery tokens and state matched within each service,
but the long answer differed at 3/16 token positions across arms and persistent
state fingerprints diverged across arms. The scalar CPU route is still an
exploratory candidate: one pair gives neither quality qualification nor a speed
claim, and the default remains unchanged. All 16 CUDA native-expert parity tests
passed; maestro1 HIP/SYCL results are host compile/link evidence only. Phase 5
remains open.

A randomized one-block [CPU arithmetic × swap-cadence screen](../../bench/results/2026-10-16-phase5-coder-q8_1-adaptive-swap-screen/README.md)
then exercised actual cadence-4 accepted-only swaps with and without the scalar
Q8_1 route, alongside delayed-swap controls. All 15 swap byte/residency checks
passed in both active arms. Delayed controls matched initial/recovery tokens and
state exactly. Both active routes differed from recovery on all 16 continuation
tokens; the default route changed five recovery-state fields, and the Q8_1 route
changed seven fields and six token positions versus its own initial short
request. This one block does not show that Q8_1 resolves swap-dependent state
drift; no quality or speed claim follows. Phase 5 remains open.

A four-pair [first-divergence trace and captured-input operator check](../../bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/README.md)
then localized an early route-dependent difference on the same Coder IQ1_M
snapshot, with the final pair running the mirror first. Every pair first
differed at dispatch 1394, layer 2, while expert IDs and owners still matched.
On the bitwise-identical preceding layer-1 activation, all four CPU-owned
IQ2_S/Q2_0 expert rows differed from CUDA under the default CPU route (all
7,680 words per row; relative L1 1.23e-2–1.57e-2); the CUDA-row mirror matched
CUDA bitwise for all four. Layer-2 relative L1 was 0.00381 in every pair. The
service differed at 3/16 long-response and 13/16 continuation token positions
in all four pairs, so this identifies a repeatable arithmetic contribution
without establishing a full-service fix. All eight arms passed with at least
14.35 GiB availability and no cgroup memory events. This is diagnostic only;
it makes no performance or quality claim. Phase 5 remains open.

A fifth [service CPU-row capture](../../bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/README.md#actual-service-cpu-row-capture)
at dispatch 1393/layer 1 confirmed that the arithmetic change is present in
the actual service output buffer before weighted combine. For identical input
activations, the default and mirror rows differed in all 2,560 values for each
CPU-owned expert; their relative L1 deltas (0.012306–0.015658) match the
standalone CPU/CUDA diagnostic. This localizes the first tested route change
to the CPU expert outputs.

A randomized [weighted-combine capture](../../bench/results/2026-10-16-phase5-coder-q8_1-combined-moe-capture/README.md)
then recorded the layer-1 verifier's `ffn_y` after expert weighting and shared
expert addition. Among 50 rows with matching positions and input tokens, no
combined output matched bitwise; the first shared row (position 511/token 271)
differed in all 2,560 values, with relative L1 0.004017. In the same pair,
dispatch 1393/layer 1 had matching input activations, expert IDs and owners,
while all four CPU-owned rows differed in all 2,560 values. The route and
combined-output captures were initially retained as separate observations.
A later [alignment audit](../../bench/results/2026-10-18-phase5-coder-dispatch-combine-audit/README.md)
found that the route trace begins after 1,392 skipped rows and has no absolute
position or token ID, while the combined capture starts at position 511/token
271. It therefore cannot join dispatch 1393 to the first combined row; the
previous contrary assertion was withdrawn. The CPU-output rows match the
dispatch's own expert IDs and CPU owners, and the paired services separately
show both CPU-route and post-combine differences, but their direct link remains
unproven. Default and mirror answers matched on the
initial short and immediate recovery requests, then differed at 3/16 long and
13/16 continuation token positions; persistent-state fingerprints differed
across arms. Both services passed above the six-GiB floor with no cgroup memory
events. This is correctness evidence only, not a quality fix or performance
claim; Phase 5 remains open.

A follow-up [no-swap CPU-route pair](../../bench/results/2026-10-16-phase5-coder-q8_1-fixed-owner-no-swaps/README.md)
disabled adaptation in both arms (`--adapt-every 0 --adapt-swaps 0`) while
retaining the same cache profile. It reproduced the first activation difference
at dispatch 1394/layer 2 with expert IDs and owners still equal; expert-ID and
owner differences appeared later at dispatch 1400/layer 8. Layer-1 combined
outputs differed across all 62 shared position/token rows, although the
separate captures still do not join a particular CPU dispatch directly to an
`ffn_y` row. The long answer differed at 3/16 positions, while initial,
recovery and continuation token IDs matched; cross-route persistent-state
fingerprints still differed. This demonstrates a route-dependent numeric/state
effect without adaptive swaps, but later router choices do change owner
selection against the static cache. Both supervised arms remained above 14.45
GiB availability with no cgroup memory events. It is diagnostic only; the
mirror is not promoted and Phase 5 remains open.

A randomized [current-source adaptive-state retest](../../bench/results/2026-10-16-phase5-coder-current-source-adaptive-retest/README.md) reran one short/long/short/continuation pair on the exact Coder IQ1_M artifact and current binary. Delayed control and cap-8 adaptive arms matched the initial and immediate recovery outputs; the long answer differed at 3/16 positions, and the next short continuation differed at all 16. Cap-8 changed five recovery state fingerprints despite matching recovery text, then diverged on the continuation. All 15 adaptive byte and residency checks passed, with minimum host/admission availability 14.15 GiB and zero cgroup memory events. This corroborates the prior seven-pair state finding on the current binary but does not prove a complete causal path or fix; adaptive migration remains unqualified and Phase 5 remains open.

The [all-layer follow-up](../../bench/results/2026-10-16-phase5-coder-current-source-adaptive-retest/README.md#current-binary-all-layer-follow-up) repeated the randomized delayed-control/cap-8 sequence on the current binary and captured all 48 layers. For the initial short, long and recovery requests, the first route-owner differences occurred at layer 1 on identical activations and expert IDs; the next layer's activation then differed. Within cap-8, initial and recovery outputs matched but layer-1 ownership and layer-2 activations did not; delayed control matched across the same requests. All 15 refill-byte and residency checks passed. This strengthens the route/state mechanism evidence without proving exclusive causality or a fix; the capture is capped at 4,096 rows and only covers the first 19–20 continuation rows per layer.

A supervised [Coder IQ1_M accepted-prefix comparison](../../bench/results/2026-10-16-phase5-coder-accepted-prefix-adaptive/README.md) then compared MTP off and MTP4 while retaining cadence-4 accepted-only adaptive updates on 512- and 2,048-token prompts. Both arms produced the same 32 tokens and matched final persistent-state fields on both prompts, including all 17 and 15 shared commit boundaries. MTP4 offered/accepted 27/15 and 30/17 drafts. The 28-GiB supervisors retained 13.15 and 13.35 GiB minimum host/admission availability, respectively, with zero cgroup memory events. This supports the accepted-prefix transaction for these two prompts/configuration only; it does not qualify task quality, performance, the experimental CPU Q8_1 route or adaptive updates generally. Phase 5 remains open.

A separate [Coder IQ1_M INT8-KV accepted-prefix comparison](../../bench/results/2026-10-16-phase5-coder-accepted-prefix-int8/README.md) repeated the MTP-off/MTP4 check at 512- and 2,048-token prompt lengths with the same binary and cadence-4 accepted-only adaptive policy. Both arms matched output IDs and final persistent-state fields at all 17 and 16 shared commit boundaries. MTP4 offered/accepted 27/15 and 31/16 drafts. Minimum host/admission availability was 13.48 and 13.35 GiB under the 28-GiB supervisors, with zero cgroup memory events. This adds INT8-KV correctness coverage at both prompt lengths; task quality, performance, other formats and adaptive migration remain open.

A new [Coder IQ1_M accepted-prefix MTP2/3/4 matrix](../../bench/results/2026-10-18-phase5-coder-accepted-prefix-mtp234/README.md) compared MTP off/2/3/4 with cadence-4 accepted-only adaptation at exact 512- and 2,048-token prompts. Each arm generated 16 tokens; all MTP arms matched output IDs and persistent state at every shared commit boundary and at completion. Draft acceptance was 6/7, 7/8 and 8/11 at 512 tokens, and 5/7, 7/10 and 8/13 at 2,048 tokens. Minimum host/admission availability was 13.20/9.93 GiB across the two blocks, above the six-GiB floor, with zero cgroup memory events. This strengthens state correctness coverage across the planned windows and two prompt lengths, without task-quality or performance claims; active CPU/GPU migration state divergence remains unresolved and Phase 5 remains open.

A [current-source Coder IQ1_M accepted-prefix rerun](../../bench/results/2026-10-19-phase5-coder-current-source-mtp-prefix/README.md) used the exact current service binary on a 2,048-token prompt. MTP windows 2/3/4 matched the MTP-off token IDs and persistent state at every shared commit boundary and at completion; accepted/offered drafts were 5/7, 7/10 and 8/13. The 28-GiB run retained 13.16 GiB minimum host and 11.36 GiB minimum admission availability, with zero cgroup events. This verifies no MTP transaction regression in the current build for that prompt and policy; it does not resolve adaptive CPU/GPU migration divergence or qualify performance. Phase 5 remains open.

The [current-source MTP round-cost diagnostic](../../bench/results/2026-10-19-phase5-coder-current-source-mtp-metrics/README.md) repeated the same 2,048-token off/2/3/4 accepted-prefix matrix with `STRATA_DECODE_TIMING=1`. Every MTP arm again matched output IDs and persistent state. Windows 2/3/4 accepted 5/7, 7/10 and 8/13 drafts and emitted 1.45, 1.78 and 2.00 tokens per round on average. Draft cost was 9.78/19.04/28.36 ms per round and verify cost was 157.19/162.83/183.05 ms per round; the stage breakdown, rejected proposals and target-produced correction/bonus tokens are retained in the analyzer output. This is instrumented correctness telemetry from 16 output tokens, not a speed comparison. Adaptive migration remains the open Phase 5 state issue.

A supervised [Coder layer-1 CPU/GPU route isolation attempt](../../bench/results/2026-10-18-phase5-coder-layer1-route-isolation/README.md) moved seven observed CPU-owned layer-1 experts into the existing GPU profile capacity. The default and CPU-mirror arms retained seven CPU misses; the profile arm routed all ten captured layer-1 experts to GPU. All arms returned the same 16 token IDs, but accepted-prefix state differed. The first unkeyed captures could not join route to combined output, so the diagnostic format now carries absolute position and token ID. A randomized current-source rerun joins dispatch 1/layer 1 to combined position 511/token 271 and confirms that CPU default versus CPU mirror changes all 2,560 combined values on bitwise-matching input activation and route (maximum absolute difference `0.00021168`, relative L1 `0.00402`); each of seven CPU expert vectors differs at all 2,560 elements (per-expert relative L1 `0.00804`–`0.01757`). The captured-expert oracle confirms the default and mirror service outputs match their corresponding parity CPU outputs exactly, and all seven Q8_1 mirror vectors match CUDA bitwise with lower GGML float-reference error. The GPU-profile arm's host JSONL activation was stale for all-GPU rows; the follow-up device-side graph capture shows the actual position-511 input matches CPU mirror and the combined output matches exactly. The remaining row differences are analyzed in the follow-up below. This is one-row operator correctness evidence only; task quality, state parity and performance remain open, and Phase 5 remains open.

A supervised [Coder IQ1_M MTP cancellation check](../../bench/results/2026-10-16-phase5-coder-mtp-cancel-parity-current/README.md)
canceled after eight streamed deltas and 12 committed tokens. Same-service
recovery returned `Hello Orin!`; three fresh exact-length references matched
all 11 persistent-state fields at each shared accepted prefix `L=48, 51, 55,
59`. This used the Coder GGUF with the separately sourced base
`Qwen/Qwen3.8-Flash-Next` MTP revision `de4b8e4d43b917e7706784d8bb445c9af86a3540`;
it is evidence for that exact pairing and one cancellation point, not a
Coder-specific MTP artifact or broad cancellation qualification. Phase 5
remains open.

A supervised [Coder IQ1_M long-prefill cancellation check](../../bench/results/2026-10-16-phase5-coder-prefill-cancel-recovery/README.md)
repeated stream cancellation during the 7,501-token, 8K-context retrieval
prefill at four client delays. The engine had read 64, 64, 512 and 576 tokens,
and generated none; each same-service recovery returned `Hello Orin!`, and all
11 final persistent-state fields matched a fresh-service reference at `L=24`.
Across the four 28-GiB-supervised runs, minimum host/admission availability
ranged from 13.15 to 13.41 GiB and cgroup pressure/OOM counters remained zero.
This covers early and mid-prefill cancellation points, not every prefill
boundary; Phase 5 remains open.

A randomized three-block [Coder IQ1_M short-task MTP screen](../../bench/results/2026-10-16-phase5-coder-mtp-window-screen/screen-short/README.md)
and [near-limit MTP screen](../../bench/results/2026-10-16-phase5-coder-mtp-window-screen/screen-near-limit/README.md)
completed both a 512-token and a 7,501-token retrieval task at 8K context, with
MTP off/2/3/4, FP16 KV and static expert residency. All 24 measured responses
matched their independent retrieval oracle. In the short-task screen, decode
throughput rose 7.40%, 11.84% and 13.61% for MTP2/3/4; at near-limit length,
MTP3 was 1.62% slower and MTP4 7.65% faster by median paired decode rate.
MTP4's median client request-time change was +0.19%, so the decode gain did not
produce an end-to-end request win on the prompt-dominated workload. One near-
limit MTP2 pair initially loaded 121 fewer expert slots than its control and
was excluded from timing analysis. A separate [three-block fixed-cache
recheck](../../bench/results/2026-10-16-phase5-coder-mtp-window-screen/screen-near-limit-mtp2-fixed-cache/README.md)
matched 3,378 resident slots in all pairs, but one MTP2 request had a 9.92-second
stream gap; its paired decode-rate interval remained very wide (−76.66% to
+0.35%). This leaves MTP2 near-limit timing inconclusive. Both reports retain
model/runtime identities, raw paired measurements and memory telemetry. These
are screens for one Coder IQ1_M task and FP16 KV, not confirmation or a profile
recommendation. Phases 5–7 remain open.

A seven-block [held-out Coder IQ1_M MTP4 confirmation](../../bench/results/2026-10-16-phase6-coder-mtp4-heldout-confirm7/README.md) compared MTP off and MTP4 on a distinct 512-token retrieval-plus-arithmetic prompt. All 14 arms matched the independent exact answer and each pair matched actual expert residency and FP16 KV. MTP4 drafted/accepted 42/33 tokens per request; median paired decode throughput rose 3.65% (paired-block bootstrap 95% interval 2.25%–4.85%). Median client request time increased 1.27%, with an interval spanning zero (−0.59% to +1.67%); prompt throughput was 1.95% lower with an interval reaching zero. Minimum host/admission availability was 13.31/9.21 GiB across 1,108 memory samples, with zero cgroup memory events. This confirms the decode effect and exact task output for this one held-out Coder IQ1_M/FP16-KV cell; it does not establish an end-to-end win, compare against Q2_0 or promote a profile. Phases 5–7 remain open.

Phase 6's same-binary Q2_0 int8-KV [MTP × prompt-length study](../../bench/results/2026-10-16-phase6-q2-int8-mtp3-workload-interaction/README.md) completed its 12-arm screen and corrected 28-arm held-out confirmation. The confirmation passed all 14 paired blocks with no rejected cells, including the independent short-task suffix-sum oracle. MTP3 reduced median prompt throughput 13.65% at 512 tokens and 8.56% at 7,501 tokens; client total time increased 7.60% and 8.63%. The prompt-throughput interaction estimate was +5.89% (paired-process bootstrap 95% interval 1.0009–1.0680), while decode-TPS and client-total interaction intervals included no effect. This supports only a borderline difference in the penalty between these prompts; it does not promote MTP3 or close Phase 6's other interactions.

A new seven-block Q2_0 [task-qualified graph × MTP confirmation](../../bench/results/2026-10-16-phase6-q2-graph-mtp-quality-confirm7/README.md) reran all 28 captured/eager × MTP-off/window-2 cells on the validated 2,094-token processor task. Every arm naturally stopped at 293 tokens, passed the task rubric, and produced byte-identical output. Graph/eager effects and graph × MTP interaction intervals included no change. MTP2 increased request time 4.12% captured and 3.86% eager, and reduced decode throughput 6.10% and 4.94%; those request/decode intervals exclude zero. MTP2 offered/accepted 153/97 drafts each run. Minimum host/admission availability was 16.925/11.630 GiB and all cgroup event counters remained zero. This closes the quality gap for this graph × MTP cell only; no profile is promoted and Phase 6 remains open.

A current-source seven-block [Q2_0 graph × MTP2 confirmation](../../bench/results/2026-10-19-phase6-q2-graph-mtp-current-source-confirm7/README.md) repeated the randomized captured/eager × MTP-off/window-2 matrix on the validated 2,094-token processor task with binary `b09ed0b5`. All 28 fresh-service cells passed, outputs were byte-identical across conditions, and every arm offered/accepted 0/0 or 153/97 drafts as expected. Client request-time intervals included no change for capture, MTP2 and their interaction. MTP2 reduced decode throughput 5.00% captured (95% interval −8.54% to +2.63%) and 5.06% eager (−7.32% to −3.70%); the captured interval includes no change. Minimum host/admission availability was 16.86/9.22 GiB with zero cgroup events. No profile is promoted; this adds current-source evidence for this one task, while Phase 5 state/migration and Phase 6 other interactions remain open.

The current-source Coder IQ1_M [256K retrieval/recovery check](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m-256k/README.md) passed: all three planted markers were returned once and in order from a 240,286-token uncached prompt, and the same service returned `RECOVERED`. Engine timing was 8.5 prompt tokens/s; minimum host/admission availability was 7.44 GiB across 27,042 one-second samples, above the six-GiB floor, with zero cgroup pressure/OOM events. This adds one functional capacity cell for the already-tested Coder IQ1_M artifact, not a quantization or engine comparison or a broad support claim. Phase 7 remains open.
A Q2_0 [256K near-limit retrieval and recovery check](../../bench/results/2026-10-15-phase7-q2-recall-256k/README.md) passed on Orin: 240,286 prompt tokens, all three planted markers exactly once and in order, and a same-service recovery response. Across 11,096 one-second samples, minimum host/admission availability was 7.31 GiB; sampled cgroup pressure/OOM counters were zero. The engine reported 20.8 prompt tokens/s, with 11,557.8 s prompt time. This is a single functional capacity check, not a performance or broad 256K support claim. Phase 7 remains open.

A held-out Q2_0 [64K retrieval-plus-arithmetic quality check](../../bench/results/2026-10-15-phase7-q2-quality-64k/README.md) returned all three 10/50/90% markers once and in order, computed the independently verified suffix sum `1971`, and returned same-service `RECOVERED`. Minimum host/admission availability was 15.13/11.50 GiB across 2,205 samples with zero cgroup pressure/OOM events. This extends one arithmetic task to 64K; it is not a broad quality score. Phase 7 remains open.

A Q2_0 [four-slot streamed API screen](../../bench/results/2026-10-15-phase7-q2-concurrency4/README.md) completed four distinct retrieval tasks with all exact prompt and marker checks passing. Four slots were configured, but `/metrics` sampled at most two active slot states, so the four-way overlap gate failed. Minimum host/admission availability was 14.65/11.95 GiB with zero cgroup pressure/OOM events. This does not qualify four-way serving; Phase 7 remains open.

A three-block [staggered four-slot follow-up](../../bench/results/2026-10-16-phase7-q2-concurrency4-staggered/README.md)
used four shorter-arriving distinct requests to exercise prefill yielding. All
12 prompt-count and marker checks passed; both `/metrics` and `/slots` saw four
active slots in two blocks, while the third reached three with one request
outside the slots. The 28-GiB supervised campaign remained above the six-GiB
floor (14.66 GiB host, 10.19 GiB admission), with no cgroup pressure/OOM events.
Because overlap did not reproduce in every block, four-way serving remains
unqualified and no throughput claim is made.

The consolidated [Phase 7 evidence matrix](PHASE7_MATRIX.md) lists tested cells and open support limits.

A [maestro1 accelerator runtime audit](../../bench/results/2026-10-15-phase8-maestro1-device-audit/README.md) found Intel HD Graphics 500 only, no `/dev/kfd`, and zero SYCL platforms in the installed runtime. Existing HIP/SYCL build and help checks therefore remain compile/CLI evidence only. No host settings were changed. Phase 8 remains open.

A targeted [maestro1 HIP rebuild of `native_expert_parity`](../../bench/results/2026-10-16-phase8-maestro1-native-parity/README.md) compiled and linked the parity utility change that adds float dumps, and its usage path showed the new option. This used the retained MTP-reset source snapshot plus the exact current utility file; it is targeted x86_64 compile/CLI evidence, not a full current-source HIP rebuild or GPU runtime result.

The corresponding [current-source Orin CUDA runtime check](../../bench/results/2026-10-16-phase8-current-cuda-parity/README.md) rebuilt that target and passed layer 0 expert 0 twice. GPU dequantization matched the independent `ggml` float conversion bitwise across 4,915,200 values; the dump artifacts were identical between runs. This targets the only code change since the recorded full Orin regression and does not claim a new full test-suite run or full-model quality result.

Full current-source [maestro1 HIP and SYCL builds](../../bench/results/2026-10-16-phase8-maestro1-current-source/README.md) at commit `e6a55b30` completed: HIP linked `strata` and `native_expert_parity`, and the separate `sycl/` subproject linked `strata`; both passed their CLI checks. This is x86_64 compile/link evidence only; maestro1 has no usable AMD or SYCL runtime. Phase 8 remains open for native runtime, supported-profile, regression and rollback evidence.

A fresh isolated [current-source HIP and SYCL build](../../bench/results/2026-10-17-phase8-maestro1-current-source/README.md) at commit `1b369ab4` completed on maestro1. The HIP command passed; its Ninja progress reached 185/186 and a second build reported no work remaining. Optional prefill MMQ was disabled, and both builds used two jobs. SYCL completed 123/123 steps with oneAPI DPC++ 2026.1.1. Both binaries' `--help` commands exited 0 with their toolchain environments loaded. An 800-file manifest of tracked build inputs was verified on the host. The CMake test option was off, so no test execution is claimed. These are x86_64 compile/link/CLI checks, not AMD/SYCL device execution. The full logs and binary hashes are retained in the report. Phase 8 remains open.

After the shared CPU expert route, parity utility and generator changed, both cached maestro1 backends were rebuilt at current commit `7dea072d`. HIP reconfigured and linked `strata` plus `native_expert_parity`; help and parity usage checks passed. SYCL recompiled the changed CPU expert source and linked `strata` after its oneMKL library path and compiler temporary directory were set explicitly. maestro1 still reports zero SYCL platforms, so the current SYCL binary's help invocation aborts during device discovery (exit 134); this is recorded as unsupported runtime evidence, not a passing CLI check. These are x86_64 compile/link results only. See the [current shared-source backend report](../../bench/results/2026-10-16-phase8-maestro1-current-shared-route/README.md). Phase 8 remains open.

A fresh [current-source Orin regression retest](../../bench/results/2026-10-15-phase8-current-source-retest/README.md) rebuilt the CUDA/ARM64 tree with two jobs, passed all 117 fixture-available CTests (two optional IQ tests skipped; two pack-dependent tests excluded), and passed integration Python discovery 144/144. Minimum host/admission availability was 24.47 GiB for build, 19.07 GiB for CTest and 24.49 GiB for Python, with zero cgroup pressure/OOM counters. This is native regression evidence, not a cross-backend runtime claim; Phase 8 remains open.

After adding the opt-in CPU Q8_1 route, the [current-source fixture-available regression](../../bench/results/2026-10-16-phase8-current-source-candidate-regression/README.md)
passed 116 CTests, with two configured IQ fixture tests skipped. The unfiltered
120-test attempt showed that `expert_parity` and `pool_test` require the absent
`pack/full/experts.bin`; those two cells were explicitly excluded from the
supervised rerun. Across 272 one-second samples, minimum host/admission
availability was 19.56 GiB and cgroup pressure/OOM event counters stayed zero.
This validates the current native regression suite with available fixtures; it
does not replace model-serving or backend-runtime qualification. Phase 8 remains
open.

A fresh [current-source Orin regression](../../bench/results/2026-10-17-phase8-current-source-regression/README.md) rebuilt the current candidate under a 28-GiB scope, then passed the fixture-available CTest and integration Python suites under separate supervised scopes. CTest passed 116 tests; the two optional IQ fixture tests skipped and the two `pack/full/experts.bin` tests were excluded. Python discovery passed 161/161. Minimum host/admission availability was 18.66 GiB across 275 CTest samples, with zero sampled cgroup pressure/OOM events. The candidate SHA was unchanged; no serving workload or performance test ran. Phase 8 remains open for release-profile, default-path and rollback evidence.

A Q2_0 [three-cycle reload and teardown check](../../bench/results/2026-10-15-phase7-q2-teardown3/README.md) passed three 7,498-token retrievals with identical marker answers; each listener and engine exited before the next startup. Minimum host/admission availability was 16.85/6.90 GiB across 545 samples, with zero cgroup pressure/OOM events. Phase 7 remains open.

Supported, failed, unsupported and untested cases are recorded. Phase 3
graph-private allocation size remains unisolated and its
graph-disabled native control is unsupported; these limits do not imply a general
capacity or cross-model result. No NInfer execution component has been promoted
into Strata. See the [Phase 3 gate audit](PHASE3_CLOSEOUT.md).

The Phase 5 [adaptive-refill byte check](../../bench/results/2026-10-14-phase5-current-source-swap-byte-verify/README.md)
passed for every incoming expert blob in the current-source Orin short/long/short
recovery reproduction: 1,017 blobs per MTP arm, with exact device-slot/source
equality. The same-service output and persistent-state recovery drift remained,
so corrupt or incomplete refill bytes do not explain this run. MTP0/MTP4 parity
remained exact. Minimum host/admission availability was 13.29/13.19 GiB under
the 28-GiB supervisor, with zero sampled cgroup pressure/OOM events. The
instrumented CUDA build passed on Orin, and the changed file passed the maestro1
HIP service build and help check (compile/link evidence only). The numerical
cause remains unresolved; Phase 5 is open.

A follow-up [device residency-map check](../../bench/results/2026-10-14-phase5-current-source-residency-table-verify/README.md)
passed on a bounded IQ1_M MTP-off request. At all three adaptive apply points,
288 incoming blobs matched their stable source bytes and the complete device
residency table matched `host_res` after upload. The request completed with
14.27 GiB minimum host/admission availability and zero sampled cgroup pressure
or OOM events. The current-source HIP service rebuilt and passed `--help` on
maestro1 (compile/CLI evidence only). Correct slot contents and residency
ownership are now checked for this route; the numerical/state recovery cause
remains unresolved.

A current-source [IQ1_M route-change capture](../../bench/results/2026-10-14-phase5-current-source-route-change-capture/README.md)
found that the first seven matched layer-0 verifier rows had identical inputs
and expert IDs before and after the long request, while 18/70 owner assignments
changed from CPU to primary VRAM. The next 15 aligned rows had different
activations and top-k IDs. Same-activation parity for switched expert 119
measured 1.61% CPU/GPU relative L1 (all 7,680 output words differed bitwise).
Two fresh service sequences matched each other request-by-request but both
reproduced 14/16 recovery-token changes and seven changed state fingerprints.
A follow-up independent oracle sweep compared all 18 switched expert calls on
their exact captured activations: all CPU/GPU output pairs differed in all
7,680 words, with 0.639%–1.66% relative L1 (1.29% median). This is direct
evidence that route-dependent arithmetic contributes to this recovery drift,
but does not explain every changed state field. Minimum
host/admission availability was 14.24/11.91 GiB; all 385 sampled cgroup
pressure/OOM counters were zero. Phase 5 remains open.

A separate held-out [adaptive-recovery task check](../../bench/results/2026-10-15-phase5-iq1-route-quality/README.md)
ran two fresh IQ1_M services through a 512-token exact-code request, the same
2,048-token swap-inducing request, and the exact-code request again. Both
initial and recovery answers returned the expected code, and their token IDs
matched within each service. In both services, GDN, PLE, tail, pooled, full
pooled and KV state fingerprints changed after the long request. Minimum
host/admission availability was 14.07/11.21 GiB across the 353-sample run, with
zero cgroup pressure/OOM events. This supports task correctness for this one
short retrieval task despite reproduced state drift; it does not qualify other
tasks or resolve the state cause. Phase 5 remains open.

The current-source MTP reset fix has now passed targeted HIP builds of the
`strata` service and `native_expert_parity`, and a full 123-step SYCL `strata`
service build on maestro1; both binaries passed `--help` load checks. These are
x86_64 compile/link checks, not accelerator runtime evidence. See the retained
[backend build report](../../bench/results/2026-10-14-phase8-mtp-reset-backends/README.md).
Phase 8 remains open for its Orin runtime, supported-profile, regression and
rollback gates.

A fresh Orin accepted-prefix regression passed all seven publication,
accepted-usage, adaptive-window, verifier, GDN, speculative-verifier and QSA
tests. The GPU convolution-history commit test covered every `keep=0..T` for
`T=1..8` with bitwise comparison to an independent host selector. Under the
28-GiB supervisor, minimum host/admission availability was 24.406 GiB and
cgroup pressure/OOM counters remained zero. Zero-row behavior is covered by
the state helpers; `Verifier::commit` itself requires `1..T`. This adds no
end-to-end performance claim. See the retained
[transaction regression](../../bench/results/2026-10-14-phase5-accepted-transaction-regression/README.md).

A Phase 5 [accepted-only adaptive-window boundary check](../../bench/results/2026-10-14-phase5-accepted-window-boundary/README.md)
passed on Orin with the Q2_0 artifact: MTP off/2/3/4 emitted identical
32-token outputs and matched all recorded persistent state at final state and
every shared accepted prefix. The change isolates and unit-tests the integer
cap policy (1,515 checks); it remains opt-in and provides no performance claim.
A 256-token follow-up with the same prompt also matched all token IDs and final
state across MTP off/2/3/4, with 168/150/134 shared state boundaries matching
for MTP2/3/4. Minimum host/admission availability was 16.88/8.43 GiB under the
28-GiB supervisor; cgroup pressure/OOM counters stayed zero. This does not
resolve same-service recovery drift after adaptive residency changes. See the
[longer accepted-prefix run](../../bench/results/2026-10-14-phase5-accepted-window-256/README.md).
After the fresh-sequence MTP reset fix, a 512-token prompt/64-token output
comparison again matched all token IDs, all nine final main-state fields, and
every shared accepted-prefix state boundary (38/31/27 for MTP2/3/4). Drafts
offered/accepted were 37/26, 60/33, and 78/37. Under the 28-GiB supervisor,
minimum host/admission availability was 16.89/8.50 GiB and sampled cgroup
pressure/OOM counters were zero. This is a single-prompt state check, not a
performance result or proof about same-service cancellation recovery. See the
[post-reset comparison](../../bench/results/2026-10-14-phase5-q2-mtp-window-post-reset/README.md).
The Orin CUDA build and focused ownership/state tests passed. maestro1 HIP and
SYCL builds and `--help` smoke checks both passed on x86_64; the HIP accepted-
window test also passed 1,515 checks. These are compile/help checks, not
accelerator runtime evidence. A fresh supervised artifact-aware PLE rerun
passed all seven stages for three tokens
(worst relative L1 `1.148e-7`), with minimum host availability 24.51 GiB.

The Q2_0 [held-out 8K MTP4 confirmation](../../bench/results/2026-10-14-phase6-q2-mtp8k-heldout-confirm7/README.md)
completed seven randomized fresh-service pairs. All replies matched the held-out
three-marker retrieval oracle. MTP4 improved median decode throughput by 17.09%
(paired bootstrap 95% interval +10.52% to +19.60%), but increased TTFT by a
median 10.72% and total request time by 8.93%; all seven pairs were slower
end-to-end. This confirms a decode-only tradeoff for this prefill-heavy prompt,
not a serving win, and no profile is promoted. Minimum host/admission
availability was 16.854/6.021 GiB with zero sampled cgroup pressure/OOM
counters. See the retained
[campaign](../../bench/results/2026-10-14-phase6-q2-mtp8k-heldout-confirm7/campaign-retry1/).
Phase 6 remains open for its other supported interactions and configurations.

The [Phase 4 closeout](PHASE4_CLOSEOUT.md) records the measured Q6_K warp-
dequant and Q8_1 NEON candidates, backend build evidence, worker screens and
their promotion limits. The opt-in Q6 candidate has exact tested operator
parity and held-out request improvements; the NEON operator win did not produce
a serving win. Defaults remain unchanged, and Phase 5's MTP/adaptive-swap state
failure prevents qualification of a combined profile.

On 2026-10-14 a same-service Q2_0 residency-quality sequence repeated 7,498-
and 15,003-token exact retrieval prompts in 8K → 16K → 8K order, with MTP off
and MTP4. All six replies matched the three-code oracle; answers and selected
persistent-state fingerprints matched across MTP settings for each request.
Within each MTP arm, however, the 8K recovery state differed in GDN, PLE, tail,
pooled, pooled-full and KV fields after the intervening long request, despite
identical recovery answer and token IDs. This confirms a state-drift signal on
this task, not broad task degradation or exact recurrent-state equivalence. A
same-day control delayed adaptation to 100,000 accepted rounds; it emitted no
swap-choice batches and restored exact recovery state in both MTP settings.
This supports adaptive swaps as the trigger for this sequence's state drift,
while the numerical mechanism and broader task effect remain open.
See the [residency-quality run](../../bench/results/2026-10-14-phase5-q2-residency-quality/README.md).
An extended retrieval-plus-arithmetic sequence returned the same exact three
codes and independently checked sum `1971` at both context sizes and MTP
settings; it reproduced the same recovery-state drift fields. This shows no
answer loss on this second bounded task, not broad quality qualification.

The current Q2_0 [real-artifact CPU/GPU expert parity diagnostic](../../bench/results/2026-10-14-phase5-q2-cpu-gpu-expert-parity/README.md)
compared expert 7 from layers 0–3, 20 and 47 on the same seeded inputs. The
whole-expert CPU/GPU relative L1 difference was `9.85e-8` to `1.06e-7`, with
5,561–5,679 of 7,680 output words differing bitwise. Each route differed from
the floating reference by `1.13e-2` to `1.27e-2` due to the represented
activation contract. This demonstrates widespread small CPU/GPU rounding
differences in these operator samples, but does not explain the service drift.
The initial diagnostic used seeded inputs; the later service-capture follow-up
below checks two real activations. The updated diagnostic reports bitwise differences
without changing calculations or its pass criterion; CUDA rebuilt and passed
on Orin, and the HIP target compiled/linked on maestro1. maestro1 supplied no
GPU runtime evidence. See the raw [HIP build log](../../bench/results/2026-10-14-phase5-q2-cpu-gpu-expert-parity/hip-build.txt).

The opt-in [service activation capture](../../bench/results/2026-10-14-phase5-moe-activation-capture/README.md)
records exact Q2_0 verifier activations, routed expert IDs and final CPU/VRAM
ownership without token text. The 8K retrieval and recovery passed. Four
additional short-service smokes captured actual activations at layers 0, 12,
24 and 47; all returned `READY` and passed the six-GiB floor under the 28-GiB
scope. Same-activation CPU/GPU parity passed for one actually routed expert at
each layer (three VRAM routes and one CPU route). Relative L1 ranged from
`6.35e-8` to `1.03e-7`, while 4,638–5,691 of 7,680 words differed bitwise.
This confirms small operator-level differences across the sampled depth; it
does not establish that route differences cause adaptive-residency persistent-
state drift. Capture remains disabled by default. See the [across-depth
results](../../bench/results/2026-10-14-phase5-moe-activation-capture/layer-samples/README.md).

A new [Phase 3 PLE regression refresh](../../bench/results/2026-10-14-phase3-q2-ple-rerun/README.md)
passed all seven PLE numerical stages (worst relative L1 `1.148e-7`), selected
CTest 15/15 and integration Python discovery 134/134. Minimum host availability
was 24.404, 24.504 and 24.492 GiB. This reconfirms the existing Phase 3 Q2_0
scope and does not close its graph-backing exclusions.

A further [Phase 3 regression refresh](../../bench/results/2026-10-14-phase3-q2-ple-followup/README.md)
on the current checkout passed the Q2_0 PLE oracle (7/7 stages, worst relative
L1 `1.148e-7`), selected accounting/ownership/PLE CTests (15/15), and integration
Python discovery (134/134). Minimum host availability was 28.06, 27.86 and
28.02 GiB, respectively, above the six-GiB floor. These commands had no
per-command 28-GiB cgroup ceiling. This reconfirms the scoped Phase 3 result;
it adds no pressure-cell evidence and leaves the documented graph-backing and
graph-disabled native-control exclusions unchanged.

A fresh [Q2_0 PLE and Phase 3 regression rerun](../../bench/results/2026-10-13-phase3-q2-ple-final-refresh/README.md)
passed all seven artifact-aware PLE stages for three tokens (worst relative L1
`1.148e-7`), the selected memory/owner/PLE CTests (15/15), and integration
Python discovery (124/124). A rerun against the current diagnostic build again
passed PLE and the same 15 CTests; minimum availability was 24.44 and 24.56
GiB respectively. This reconfirms selected contracts without changing the
Phase 3 scope or its graph-backing exclusions. The earlier
[same-day refresh](../../bench/results/2026-10-13-phase3-q2-ple-user-rerun-2/README.md)
is retained as a separate run.

After the 40-minute Phase 7 cache-reuse soak, a separate current-build
[Q2_0 PLE regression refresh](../../bench/results/2026-10-14-phase3-q2-ple-post-soak/README.md)
again passed all seven PLE stages (worst relative L1 `1.148e-7`), the selected
15/15 Phase 3 CTests, and integration Python discovery (124/124). Minimum host
availability was 24.427, 24.418, and 24.516 GiB, respectively, under the
28-GiB cgroup ceiling and six-GiB floor. The Q2_0 artifacts were already local;
this refresh does not extend Phase 3's tested scope or its graph-backing limits.

A further [Q2_0 PLE and Phase 3 refresh](../../bench/results/2026-10-14-phase3-q2-ple-final-refresh2/README.md)
on the current checkout passed all seven PLE stages (worst relative L1
`1.148e-7`), the selected 15/15 memory/owner/PLE CTests, and integration Python
discovery (134/134). Minimum host/effective availability was 24.426, 24.462,
and 24.507 GiB, respectively, under separate 28-GiB scopes and the six-GiB
floor. This reconfirms Phase 3's completed Q2_0 scope without closing its
documented graph-backing or native graph-disable exclusions.

The opt-in IQ1_M [8K/16K/32K retrieval and recovery plus 40-minute stream soak](../../bench/results/2026-10-14-phase7-q6-recall/README.md)
passed marker retrieval and same-service short recovery at all three context
sizes. The 40-minute cache-reuse loop completed 1,579 streaming requests with
zero failures; all markers were present once and in order. Minimum host
availability was 12.67 GiB across the context tests and 13.34 GiB in the soak.
Temperature stabilized near 76–77 °C for over 30 minutes. A separate
[three-cycle reload and teardown check](../../bench/results/2026-10-14-phase7-iq1-teardown3/README.md)
passed a warmup and measured request in each fresh service, verified each
listener and engine process exited before reloading, and retained 13.11 GiB
minimum host availability. A [bounded 56×56 CUDA vision smoke](../../bench/results/2026-10-14-phase7-iq1-vision/README.md)
also passed: the API returned HTTP 200, and the answer described the fixture's
checkerboard grid and color gradient. Minimum host/effective availability was
11.99 GiB. A 2048×2048 fixture also passed API admission at 1,024 image tokens
under the same supervisor, with 11.76 GiB minimum host/effective availability
and no cgroup pressure events; its 48-token answer was length-truncated, so it
does not count as a quality pass. The same profile also passed one held-out
30,040-token task: it retrieved three codes at 10/50/90% in order, summed their
suffixes correctly, and recovered on the same service. That request took
1,238.9 seconds and retained 12.75 GiB minimum host/effective availability
with no cgroup pressure events. The first attempt is retained but excluded
because a stale expected-token count caused the driver to discard the response.
Phase 7 remains in progress for broader task quality and other service cases;
these results cover one opt-in profile and do not qualify defaults, higher
image-token counts, or concurrent serving.

The [Q2_0 near-limit retrieval and recovery checks](../../bench/results/2026-10-14-phase7-q2-recall/README.md)
add a second model cohort at 8K, 16K and 32K configured contexts. Exact 7,498-,
15,003- and 30,032-token prompts returned all three markers exactly once and in
order; each same-service short request then returned `RECOVERED`. Minimum host
availability was 16.967/16.797/16.363 GiB and minimum admission availability
was 10.146/10.355/10.307 GiB, with zero sampled cgroup pressure/OOM events.
These three prompt/profile checks do not establish broad Q2_0 task quality or a
general capacity boundary; Phase 7 remains in progress.

The Q2_0 ladder has now passed a [64K near-limit retrieval and recovery
check](../../bench/results/2026-10-15-phase7-q2-recall-64k/README.md): a
60,071-token prompt at 65,536 configured context returned all three planted
markers exactly once and in order, then passed same-service recovery. Minimum
host/admission availability was 15.369/11.255 GiB over 2,144 one-second
samples, with zero cgroup pressure/OOM events. GPU clocks ranged 306 MHz–1.301
GHz; EMC readback was unavailable and energy was not request-attributed. This
adds one Q2_0 task/profile point above 32K, not a general capacity boundary or
broad quality result; Phase 7 remains in progress.

The same Q2_0 ladder has passed a [128K near-limit retrieval and recovery
check](../../bench/results/2026-10-15-phase7-q2-recall-128k/README.md): a
120,149-token prompt at 131,072 configured context returned all three planted
markers exactly once and in order, then passed same-service recovery. Minimum
host/admission availability was 13.651/13.194 GiB over 5,344 one-second
samples, with zero cgroup pressure/OOM events. GPU clocks ranged 306 MHz–1.301
GHz; EMC readback was unavailable and energy was not request-attributed. This
adds one Q2_0 task/profile point above 64K, not a general capacity boundary or
broad quality result; Phase 7 remains in progress.

A separate Q2_0 [32K retrieval-plus-arithmetic replication](../../bench/results/2026-10-14-phase7-q2-recall/quality-replication-32768/README.md)
used a 30,040-token prompt. It returned all three markers in order and the
independently checked suffix sum `1971`, then passed same-service recovery.
The 28-GiB supervisor retained 16.292 GiB minimum host availability and
10.274 GiB admission availability with zero sampled cgroup pressure/OOM events.
This adds one long-context task-quality point; it does not establish a broad
Q2_0 quality score or general capacity boundary. Phase 7 remains in progress.

The Q2_0 profile then passed a [30-minute sustained 8K retrieval run](../../bench/results/2026-10-14-phase7-q2-recall/sustained-8k/README.md)
with 14 serial fresh-prefill requests and zero retrieval failures. Minimum host
availability was 16.971 GiB and admission availability 9.546 GiB; sampled
cgroup pressure/OOM counters stayed at zero. The tegrastats `tj` sensor ranged
54.5–60.1 °C, with first/last five-minute means of 55.3/56.0 °C. Prompt cache
was disabled, so this is not cache-reuse throughput evidence. Phase 7 remains
open for broader quality, other service cases and support boundaries.

The same Q2_0 profile also passed a [30-minute sustained 16K retrieval run](../../bench/results/2026-10-14-phase7-q2-recall/sustained-16k/README.md):
eight serial requests each read 15,003 uncached prompt tokens, returned 41
tokens, and passed independent marker count/order checks. Minimum host/admission
availability was 16.75/9.77 GiB; peak scope use was 18.23 GiB, with zero sampled
cgroup pressure or OOM events. Tegrastats `tj` ranged 49.5–58.5 °C. This adds
one 16K sustained retrieval point, not broad task quality, cache-reuse
throughput, or a general capacity boundary; Phase 7 remains open.

Q2_0 also passed a [30-minute sustained 32K retrieval run](../../bench/results/2026-10-14-phase7-q2-recall/sustained-32k/README.md):
four serial requests completed over 2,298 seconds, each reading 30,032
uncached prompt tokens and passing independent marker count/order checks.
Minimum host/admission availability was 16.29/10.27 GiB; peak scope use was
17.73 GiB, with zero sampled cgroup pressure/OOM events. `tj` ranged 49.2–57.5
°C. This adds one sustained 32K retrieval point for this profile; it does not
establish broad task quality, cache-reuse throughput or a general capacity
boundary. Phase 7 remains open.

The same Q2_0 8K profile then passed a [30-minute streamed prompt-cache reuse
run](../../bench/results/2026-10-14-phase7-q2-recall/cache-reuse-30m/README.md).
All 653 repeated requests reused 7,491 of 7,498 prompt tokens and returned the
three retrieval markers exactly once and in order. Median request time was
2.86 seconds and median first-visible-token latency was 0.390 seconds. Minimum
host/admission availability was 16.93/10.72 GiB; the 28-GiB cgroup reported no
high/max/OOM events. `tj` stabilized near 68 °C during the final ten minutes.
This adds one Q2_0 cache-reuse service point; Phase 7 remains open for broader
quality and support boundaries.

A bounded [Q2_0 streamed API concurrency-2 check](../../bench/results/2026-10-14-phase7-q2-recall/concurrency2/README.md)
then passed on distinct 7,498- and 15,003-token prompts with swaps disabled:
both simultaneous requests used separate active slots and passed exact prompt,
completion, and marker checks. Minimum host/admission availability was
15.66/7.36 GiB under the 28-GiB cap, with zero sampled cgroup pressure/OOM
events. The serial-versus-two-slot latencies were 149/259 and 882/729 seconds
for 8K/16K, so this cell shows no serving-latency benefit. The engine rejects
`--adapt-accepted-only` with `--batch`; that failed start is retained. This
single pair does not qualify general concurrency or adaptive swaps in batch
mode; Phase 7 remains open.

After the Q2_0 context ladder, a fresh [regression refresh](../../bench/results/2026-10-14-phase7-q2-recall/post-checks/README.md)
again passed all seven PLE numerical stages (worst relative L1 `1.148e-7`),
the selected 15/15 accounting/ownership/PLE CTests, and integration Python
discovery 132/132. The supervised GPU checks retained at least 24.388 GiB
host availability with no sampled OOM kills. This confirms the selected
regression set after the campaign; it does not broaden the Phase 3 scope.

The accepted-only Q6 MTP4 path also passed a [three-pair MTP-off retrieval
ablation](../../bench/results/2026-10-14-phase5-q6-mtp-recall-ablation/README.md)
on that same held-out 7,498-token prompt. All six fresh-service arms returned
identical marker answers and recovered; direct accepted-prefix tracing matched
all 41 token IDs, final persistent state, and 14 shared commit boundaries.
MTP4 offered/accepted 32/30 drafts in API runs. This is one prompt and a
three-pair correctness screen; Phase 5 remains open for other prompts,
cache/resizing conditions, and termination paths, with no timing promotion.

Phase 6 Q2_0 graph/eager extended screening is recorded in the
[2026-10-12 result](../../bench/results/2026-10-12-phase6-q2-graph-eager-full/README.md).
The MTP-off long cell failed output parity in 2/7 eager pairs, correlated with
short-before-long request order. A direct no-warmup API driver confirmed that one
512/64 request followed by one 2048/128 request changes the long output at
token index 8 versus a fresh long-only service, identically in captured and
eager routes. Disabling adaptive expert swaps, or delaying them past the test,
made captured and eager sequences match the fresh long-only output. This
localizes the sensitivity to adaptive residency changes, which can change
whether experts use the GPU or CPU path; those paths may round differently.
It is not yet classified as unacceptable quality loss or a state-reset defect.
The state-hash trace changes the output again while reporting different GDN/KV
hashes, so it is perturbative. Graph/eager timing remains descriptive until an
independent output-quality budget is checked, and Phase 6 stays open. The
retained records include a failed `--spec 0` startup, corrected to the native
pack's required `--spec 2` while keeping MTP disabled. No performance candidate
is promoted.

The Phase 6 report now includes a narrow deterministic output-quality screen
for default adaptive expert swaps versus swaps disabled. With a 512-token cap,
both replies passed the 200-word prompt rubric, including its exact arithmetic
statement and all required concepts; they differed only in the output-device
explanation. This is one task-level screen, not a general quality budget or
approval of residency-driven output variation. The initial 256-token pair is
retained as incomplete because it stopped before the output concept. No path or
default is promoted.

A [three-block randomized Q6_K warp-dequant × MTP screen](../../bench/results/2026-10-12-phase6-q6-warp-mtp-screen/README.md)
then completed 12 fresh-service cells with exact generated-output parity in
every block and all memory gates passing. Warp-dequant reduced median total
request time by 6.35% with MTP off and 5.53% with MTP window 4; prompt time
improved while decode time was about 2% slower. The interaction estimate was
small and uncertain. This single-model screen is not held-out confirmation or
a general quality qualification, so no default changed.

The same seven-block Q6 warp × MTP design was rerun with the opt-in
`--adapt-accepted-only --adapt-every 4` policy in every cell. All 28 cells
passed, and generated output matched exactly across all blocks, warp settings,
and MTP off/window4. At fixed MTP settings, warp-dequant reduced median
request time by 7.279% (95% paired bootstrap interval −7.716% to −5.118%) with
MTP off and 6.355% (−7.979% to −4.433%) with MTP4; the interaction estimate
was +0.669% (−0.896% to +1.058%). Minimum host/effective availability was
13.075 GiB with no floor breach. Two 39-second warp decode samples were
retained; their cause is unknown. This supports only the exact held-out model,
prompt, cache and policy configuration. Decode intervals include no-change or
regression, energy is not process-attributed, and no default or general serving
profile is promoted. The original default-adaptation campaign remains a
separate state-parity failure. See the [accepted-only confirmation report](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/README.md).

The [accepted-prefix MTP investigation](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/README.md)
now captures the MoE boundary on the 512-token suffix. At the first bad row
(position 515), layer-1 GDN output and FFN input match, but the combined FFN
output differs (relative L2 0.004423); layer-2 GDN input then differs. With
`--adapt-swaps 0`, the same no-MTP/window-4 pair matches every output token,
accepted-prefix state hash, and captured activation. This strongly implicates
adaptive expert residency for this prompt/configuration, but does not identify
the CPU/GPU arithmetic or swap mechanism. A tracking-enabled
`--adapt-every 100000` control also restores exact parity, so the evidence
points to swaps executing during generation, not tracking alone.
`STRATA_DEC_BATCH=0` did not remove the default-swap mismatch. The supervised
runs retained at least 13.126 GiB host/effective availability with no OOM
events. Focused CUDA regression passed 10/10; the changed verifier translation
unit compiled in the HIP-configured Release tree, while its full application
link was not completed. The separate SYCL verifier sources were unchanged.
Phase 5 remains open; MTP is unqualified for this incident workload, and no
defaults changed.

The opt-in accepted-row/accepted-token adaptation candidate now matches MTP-off
output and accepted-prefix state on the 2,048-token incident prompt for windows
2, 3, and 4, using 32 output tokens. Each arm matched all shared state
fingerprints (22, 20, and 17 shared boundaries); draft offered/accepted counts
were 16/10, 24/12, and 31/15. The supervised four-arm run passed with a
13.37-GiB minimum host availability and no OOM events. This closes the
reproduced parity failure for those window sizes on that prompt. A distinct
held-out watershed prompt at 16K context then matched for the same three MTP
windows, with 21/16/12 shared state checkpoints and offered/accepted counts
15/11, 22/16, and 29/20. It passed the same 28-GiB supervisor with 13.19 GiB
minimum host availability and no OOM events. These are two correctness cells;
other prompts/contexts, performance and task quality remain open. Defaults
are unchanged. See the [accepted-only matrix report](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/README.md).

The same candidate also passed the 32-token MTP 2/3/4 matrix on the local Q2_0
pack at 64K context with FP16 KV. Output IDs and every shared checkpoint
matched, with 21/19/17 shared boundaries; offered/accepted drafts were
16/11, 24/13, and 31/15. The 28-GiB supervisor retained 15.25 GiB minimum host
availability with no OOM events. This extends correctness across the two local
model configurations, but KV alternatives, quality and performance remain
unqualified. An initial startup rejection due to suffix drafting being enabled
is retained and excluded; the measured rerun disabled suffix drafting per the
candidate's stated compatibility limits.

The Q2_0 512-token screen was extended to INT8, Q4_0, and K8V4 KV at 16 output
tokens. All three MTP windows matched all IDs and 11 shared state checkpoints
for each format; offered/accepted drafts were 8/5, 14/5, and 17/5. Minimum host
availability was 16.05, 16.49, and 16.30 GiB, respectively, with no OOM events.
Together with the 32-token FP16 cell, this covers the candidate's short-prompt
state parity across all four supported KV formats on Q2_0. Task quality and
performance remain unqualified.

The Q2_0 candidate matrix was extended to a distinct 2,048-token prompt at
64K context for all four KV formats. MTP windows 2/3/4 matched MTP-off token
IDs and every shared state checkpoint in all 12 comparisons; FP16 used 32
generated tokens and the other formats 16. Minimum host availability was
15.48 GiB (FP16), 16.23 GiB (INT8), 16.62 GiB (Q4_0), and 16.46 GiB (K8V4),
with no OOM events. This completes the opt-in candidate's tested Q2_0 long
prompt × KV × MTP-window correctness matrix for these artifacts. It is not a
quality or performance result; graph/eager behavior and broader prompts remain
open.

The opt-in accepted-only path also passed a [128-token IQ1_M accepted-prefix
trace](../../bench/results/2026-10-14-phase5-iq1-accepted-prefix-128/README.md)
on the exact 2,048-token incident prompt at 8K context. MTP windows 2/3/4
matched MTP-off output IDs, final state, and every shared commit state (78, 74,
and 58 boundaries). They offered/accepted 66/50, 89/54, and 120/70 drafts.
Minimum host availability was 13.34 GiB and effective admission headroom was
10.36 GiB, with no OOM events. This extends the candidate's correctness chain
on IQ1_M; it remains one prompt and one opt-in swap policy, without a quality,
performance or default-promotion claim.

The same IQ1_M [128-token accepted-prefix matrix on eager decode](../../bench/results/2026-10-14-phase5-iq1-eager-accepted-prefix-128/README.md)
also passed for MTP off/2/3/4. Direct captured/eager comparisons matched token
IDs, final state, and every common accepted-prefix state at all four windows
(128/78/74/58 boundaries). Minimum host availability was 13.47 GiB and minimum
effective headroom was 10.43 GiB, with no OOM events. This closes one long-chain
correctness cell for captured/eager routes; tracing makes it unsuitable for
timing, and the default adaptation policy remains unqualified.

Accepted-only adaptation also matched across captured and `--no-capture` eager
routes on the 512-token Q2_0 prompt, FP16 KV, and 16 outputs. MTP off and
windows 2/3/4 matched route-to-route token IDs, final state, and all common
accepted-prefix checkpoints (16, 11, 10, and 10 respectively); both routes also
matched their MTP-off reference. The supervised runs retained 15.30 GiB
minimum host availability for captured and 15.40 GiB for eager, with no OOM
events. This is correctness-only evidence, with eager-versus-captured
performance and same-service resize/recapture behavior still open. The subsequent
accepted-only Q6 seven-block confirmation exercised the warmed captured route:
in every cell, verifier graphs were captured before the measured 2,048-token
request after a distinct 512-token warmup, and outputs matched across MTP
off/window4 and warp off/on. This verifies replay after warmup for fixed
contexts; it does not isolate warm-capture cost. Context capacity is fixed for
each service, and KV mappings are designed to keep addresses stable, so no
resize-triggered graph recapture was expected or observed. A same-service
elastic-KV grow/trim test is now recorded below; see the
[capture order and seven-block report](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/README.md).

The accepted-only stream-cancellation follow-up initially found a real
recovery defect: after the canceled request committed four tokens, the next
request failed because per-window usage staging still had the previous
verifier size. Clearing that staging buffer after its committed rows are
counted fixed the issue. The rerun canceled after one visible delta, matched
all persistent fields at `L=48` and `L=51` in two exact-prefix references, and
recovered on the same service with `Hello Orin!`; minimum host availability was
13.22 GiB and there were no OOM events. This closes only that short MTP4
cancellation/recovery cell; longer prefill cancellation and other termination
paths remain open. The failed run is retained alongside the [passing run](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/README.md).

A new same-service `512 → 2048 → 512` sequence under accepted-only cadence 4
found that the two short requests differed at token 0 and in 14/16 output IDs
for both MTP-off and MTP4. Each request still matched exactly between those
MTP settings, including all nine persistent-state fields. A control with
accepted-only tracking delayed to `--adapt-every 100000` passed exact output
and state equality between the two short requests and across MTP settings on
all three requests. Both runs stayed above 13.24 GiB host availability with no
OOM events. This implicates swaps occurring during the sequence, not a
demonstrated state leak; the exact residency/arithmetic cause and task-quality
impact remain unclassified. See the [same-service report](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/run/same-service-short-long-short/README.md).

A Q2_0 [frozen-residency replay](../../bench/results/2026-10-14-phase5-q2-frozen-residency-replay/README.md) saved the adaptive sequence’s final expert profile, then loaded it in a fresh non-adaptive service. All five 48-token answers matched the independent retrieval/arithmetic oracle. Adaptive short recovery still differed from the initial short request in six of nine persistent fingerprints; two repeated requests under the frozen profile matched in answer and all nine fingerprints. The frozen result matched the adaptive recovery answer but not its final fingerprints. This indicates the final resident set alone did not reproduce the observed state difference; it does not identify the arithmetic cause or qualify adaptive swapping generally. Minimum host/admission availability was 17.85/7.00 GiB, with no cgroup pressure or OOM events. Phase 5 remains open.

A current-checkout [swap-choice attribution rerun](../../bench/results/2026-10-14-phase5-q6-swap-choice-attribution/README.md) logged all expert residency choices during the same sequence. Each request caused four updates; the first two selected 96 swaps each time, while recovery selected 96/79/74/73. All 12 choice batches matched between MTP-off and MTP4, as did outputs and persistent state request-by-request. Yet both settings again changed 14/16 recovery token IDs and seven state fingerprints versus the first short request. This strengthens the residency-change association and shows the symptom does not require MTP, but does not establish the numerical cause or task-quality impact. Adaptive swaps remain unqualified for this stability case; Phase 5 remains open.

The [Q2_0 retrieval-quality follow-up](../../bench/results/2026-10-14-phase5-q2-residency-quality/README.md)
then confirmed all six adaptive-run answers against an exact three-code oracle.
Both MTP settings changed six persistent fields after the 16K request while
returning the exact original 8K answer. With adaptive updates delayed beyond
the measured sequence, both settings recovered the original state exactly.
This controlled contrast narrows the state-drift trigger to adaptive swaps for
this Q2_0 profile; it does not identify the underlying arithmetic difference
or qualify adaptive swaps for other workloads. Phase 5 remains open.

The accepted-only 16K-context elastic-KV test grew from 2,048 to 10,240 cells
for a 9,000-token prompt, then trimmed to 2,048 before the short recovery
request. Both graph sets were captured before growth, and recovery output and
state matched the initial short request. The long MTP-off/MTP4 outputs matched,
but their final GDN, tail, pooled-index and KV state differed; the first shared
boundary with main-state differences was four committed tokens. With full KV
backing and the same context/prompt, MTP-off and MTP4 matched all state checks.
The grow/trim supervisor retained 13.423 GiB minimum host availability; the
full-KV control retained 13.011 GiB, with no OOM events. A cache-matched
diagnostic then selected 3,895 startup slots for MTP-off and 3,903 for MTP4;
after relinquishing 102/110 slots during growth, both held 3,793. The 9K
request matched all nine state fields at shared accepted-prefix boundaries
1/4/8. The full sequence still fails cross-MTP state checks for the short
requests because their startup capacities differed, although within-service
short recovery remained exact. This supports resident cache capacity as an
explanation for the long-request discrepancy in this cell, but does not qualify
elastic-KV × MTP generally. The cache-matched run retained 14.423 GiB minimum
host availability with no OOM events. See the [grow/trim report](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/run/kv-grow-graph-recovery/README.md).

A direct 9K accepted-prefix comparison held initial cache capacity at 3,895
slots for both MTP-off and MTP4. With the default KV floor, growth retained
3,793 slots for MTP-off and 3,786 for MTP4, and persistent state diverged at all
shared commits despite matching token IDs. Setting `STRATA_KV_GROW_FLOOR=3793`
kept both caches at 3,793; MTP4 mapped fresh chunks for its extra KV requirement,
and both arms then matched token IDs and all nine state fields at all 15 shared
commits. Minimum host/effective availability was 13.30 GiB with zero OOM events.
A distinct 15,003-token held-out prompt at 16K context then passed a full
short→long→short-recovery sequence in cache-matched MTP-off and MTP4 services:
outputs and final state matched on all requests, and all 3 common long-request
accepted-prefix states matched. Both arms captured graphs before growth,
expanded to 16,384 KV cells, trimmed to 2,048, and recovered the short request.
Minimum host/effective availability was 13.42 GiB with zero cgroup pressure
counters. A fresh focused [Phase 5 transaction/verifier CTest run](../../bench/results/2026-10-14-phase5-transaction-ctest/README.md) also passed all eight publication, accepted-usage, verifier, draft-policy, probabilistic-sampling, coupled-draft and captured-graph tests. This extends the cache-matched correctness evidence to one longer prompt, but does not qualify elastic-KV × MTP generally, other cache floors, or performance. Defaults are unchanged. See the [matched-cache 9K report](../../bench/results/2026-10-13-phase5-q6-kvgrow-cachematched/README.md) and the [held-out 15K report](../../bench/results/2026-10-14-phase5-kvgrow-heldout/README.md).

After the fix, the four-arm accepted-only MTP-window matrix passed again on
the rebuilt binary: windows 2/3/4 matched all IDs and shared state checkpoints,
with 22/20/17 matching boundaries. The selected CUDA Phase 3 regression passed
15/15 and the integration Python suite passed 124/124. The changed
`generate.cpp` was rebuilt and linked in the maestro1 HIP tree; the separate
SYCL generator copy was not changed, so this gives no SYCL feature claim.

The [exact Q8_0 scalar-versus-ARM quantization experiment](../../bench/results/2026-10-13-phase4-q8-neon-quant/README.md)
compares Strata's explicit scalar oracle against ggml's Cortex-A78AE NEON path
on 256 rows of width 2,560. Three independent processes matched every Q8_0 byte;
the median operator time was 6.297 ms scalar versus 0.787 ms NEON per 16 × 256
rows (−87.517%). This is quantization-only evidence: production Strata uses the
separate Q8_1 activation contract, no expert dot/GPU/request timing is included,
and no dispatch/default changed. Task-level quality remains open and Phase 4
continues.

A Strata-contract Q8_1 NEON candidate now exists behind the opt-in
`STRATA_Q8_1_NEON=1` setting; scalar remains the default. Its independent
mathematical contract tests pass for both dispatches. A seven-pair production
dispatch operator confirmation measured −29.666% (paired bootstrap interval
−29.845% to −29.432%), with exact scale/code/sum/correction values. This does
not qualify CPU expert contention or end-to-end performance. A three-pair
Q2_0 API screen at 512 prompt tokens and 8K context matched generated text in
all pairs. Median paired total-request delta was +0.019%; prompt time was
0.444% slower. This screen gives no end-to-end win and does not cover held-out
prompt/context shapes. The candidate remains opt-in. Full HIP and SYCL builds
passed on maestro1, followed by compilation and app relinking with the exact
current `expert.cpp`; this is x86 compile evidence only, not runtime qualification.
The [backend record](../../bench/results/2026-10-13-phase4-q8_1-neon-contract/MAESTRO1_BUILDS.md)
and [main report](../../bench/results/2026-10-13-phase4-q8_1-neon-contract/README.md)
retain the build and experiment details.

The fresh [Phase 3 Q2_0 regression on the Q8_1 candidate binary](../../bench/results/2026-10-13-phase3-q2-ple-q8-neon-refresh/README.md)
passed artifact-aware `ple_parity` and the selected memory/owner/PLE CTests
(15/15), then integration Python discovery (124/124). The Q8_1 opt-in was
unset. Minimum availability was 24.415 GiB for CTest and 24.408 GiB for Python
tests under the six-GiB supervisor. This refreshes selected contracts only; it
does not extend Phase 3 capacity or graph-backing claims.

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

A fresh [Q2_0 MTP decode-cancellation recovery check](../../bench/results/2026-10-12-phase5-q2-cancel-mtp-8chunks-supervised/README.md) closed the client stream after eight non-empty deltas and 11 committed tokens. The canceled state matched three fresh exact-length references across all six shared accepted-prefix boundaries (L=48 through L=58), including all eleven state fields; the same service then returned `Hello Orin!`. The 28-GiB supervisor retained 15.09 GiB minimum host availability and 13.21 GiB effective headroom, with no OOM events. This adds one decode-cancellation point; longer prefill cancellation and broader termination cases remain open. A preliminary unsupervised attempt is preserved separately and explicitly excluded.

A fresh [Q2_0 MTP accepted-prefix check](../../bench/results/2026-10-13-phase5-q2-accepted-prefix/README.md) used the explicit Q2_0 MTP runtime pack and compared windows 2/3/4 with MTP off. All three active windows offered and accepted drafts, generated identical eight-token sequences, and matched all nine persistent-state fields at every shared commit boundary and at request end. The 28-GiB supervised run retained 15.396 GiB minimum host availability and 11.954 GiB minimum effective admission headroom. The focused published-prefix, speculative-verifier, graph-trace, coupled-draft and probabilistic-draft CTests passed 5/5. This is short-prompt state evidence only; long chains, termination cases, quality and performance remain open.

The same Q2_0 [accepted-prefix matrix extended to 32 tokens](../../bench/results/2026-10-13-phase5-q2-accepted-prefix/README.md) matched all token IDs and every shared/final state fingerprint for windows 2/3/4. The windows offered/accepted 17/15, 24/19 and 33/23 drafts across repeated rounds. Minimum host availability was 15.342 GiB and effective admission headroom 11.392 GiB. A separate [Q2_0 MTP cancellation and recovery check](../../bench/results/2026-10-13-phase5-q2-mtp-cancel-recovery/README.md) then matched all eleven persistent-state fields at `L=48` and `L=50` against three fresh references; same-service recovery returned `Hello Orin!`. The 311/310 requested-allocation event ledger balanced in all four service processes, leaving only the service-lifetime weight arena live at log end. Minimum host availability was 15.341 GiB and effective admission headroom 12.514 GiB. These checks extend transaction/recovery evidence for this model and fixed cache; broader termination cases, quality and performance remain open.

The Q2_0 [128-token accepted-prefix extension](../../bench/results/2026-10-12-phase5-q2-accepted-prefix-128/README.md) matched the MTP-off reference token-for-token and in all nine persistent-state fields at every shared boundary and final state for windows 2/3/4. The arms offered/accepted 75/52, 116/69 and 159/74 drafts, with 76, 59 and 54 shared boundaries. The 28-GiB supervised sequence completed in 394.75 seconds with 15.41 GiB minimum host availability and 10.38 GiB minimum effective headroom; OOM counters stayed at zero. This extends accepted-prefix correctness for one 512-token prompt and configuration, not long-context quality or performance. Other termination cases, broader prompts/KV formats and graph/eager performance remain open.

The new [Q2_0 eager/captured comparison](../../bench/results/2026-10-13-phase5-q2-eager-captured/README.md) adds a serial routed-expert eager path using the existing layer pre/router and post/combine seam. Eager and captured modes matched output IDs, all nine final state fields and every accepted-prefix trace for MTP-off and window 2; the window-2 arm accepted four drafts. Focused PLE, verifier, graph and transaction tests passed 9/9. One sequential run per mode showed slower eager decode, so no performance claim is made. maestro1 rebuilt and linked the changed HIP target; its SYCL target reported no work because that backend has separate session and generator sources. Randomized performance repetitions, other termination cases, quality and longer-chain eager checks remain open.

The fresh [128-token eager/captured MTP state comparison](../../bench/results/2026-10-12-phase5-q2-eager-chain-128/README.md) matched the same Q2_0 prompt across MTP off and windows 2/3/4: token IDs, all nine final state fields, and every shared accepted-prefix boundary matched (128, 76, 59 and 54 boundaries). The supervised run retained 15.27 GiB minimum host availability and 9.83 GiB effective headroom with no OOM events. This is correctness evidence for one prompt/configuration, not performance or quality qualification; other prompts, termination across graph modes and randomized performance remain open.

The randomized [Q2_0 graph/eager screen](../../bench/results/2026-10-12-phase5-q2-graph-eager-screen/README.md) adds three independent same-day pairs at 512- and 2,048-token prompts, with MTP off and window 2. Every pair matched generated text; MTP2 reported four accepted drafts in both routes. Eager decode was slower in the MTP-off cells, while three-pair MTP2 rates varied. Eight output tokens per process are insufficient for confirmation, so this does not qualify a performance change. The campaign retained 28-GiB supervision, read-only clocks and raw memory/telemetry; minimum host availability was 17.04 GiB. Longer-chain correctness, termination behavior, held-out performance and quality remain open. Phase 3's tested Q2_0 scope remains closed under [its closeout](PHASE3_CLOSEOUT.md); this experiment does not change its memory or transfer conclusions.

A new [32-token captured/eager MTP2 state check](../../bench/results/2026-10-12-phase5-q2-eager-mtp2-chain/README.md) compared separate routes against no-MTP references and against each other. Both offered 18 and accepted 13 drafts; token IDs and all nine state fields matched across 19 accepted-prefix boundaries and at final state. The 28-GiB supervisor retained 17.14/17.18 GiB minimum host availability. This closes one longer-chain correctness cell only; it is not performance or quality qualification.

The [eager MTP2 cancellation/recovery run](../../bench/results/2026-10-12-phase5-eager-mtp2-cancel/README.md) canceled after three committed tokens, recovered on the same server, and matched three fresh references. Its accepted-prefix states at `L=48` and `L=50` are identical to the captured-path result, including all eleven fields. Minimum host availability was 17.09 GiB under the 28-GiB scope. Long-prefill cancellation and broader pressure remain open.

After the Q6_K opt-in kernel change, the same [Q2_0 PLE and ownership regression](../../bench/results/2026-10-11-phase3-current-kernel-ple-regression/README.md) passed again on the current binary: all seven PLE stages for three tokens (worst relative L1 `1.148e-7`), 19/19 selected CTests and 103/103 integration Python tests. Minimum host availability was 27.21 GiB. The new kernel environment variable was unset, confirming the default route retains the established PLE behavior.

The opt-in [Q6_K-to-FP16 warp-layout candidate](../../bench/results/2026-10-11-phase4-q6-warp-layout/README.md) is bit-identical on all five profiled real matrix shapes and cuts weighted isolated conversion time by about 49% in three processes. A three-pair held-out 2,048/128 API screen matched output, draft counts and cache slots, with request-time deltas −4.13%, −6.11% and −6.08%; an eight-token accepted-prefix trace matched all five commit boundaries and full state hashes. The CUDA kernel, full HIP build and full SYCL build pass. This remains a one-workload screen without task-quality or multi-context confirmation; default dispatch is unchanged.

A deterministic [semantic output screen](../../bench/results/2026-10-12-phase4-q6-warp-quality-screen/README.md) for the same opt-in Q6_K warp-dequant route compared one exact 512-token computer-processing prompt. Baseline and candidate both finished naturally and passed the 200-word, required-concepts and exact-arithmetic rubric (235 and 252 words); reply wording differed in the closing binary-data explanation. Minimum host availability was 13.26/13.22 GiB under the 28-GiB supervisor. This is one task-quality screen, not broad quality qualification or performance evidence; dispatch remains opt-in.

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

A fresh [current-source Orin regression](../../bench/results/2026-10-18-phase8-current-source-regression/README.md) rebuilt the candidate and passed all 116 runnable tests in the 118-test fixture-available CTest selection; two optional IQ fixture tests were skipped and the two tests requiring the absent `pack/full/experts.bin` were excluded. The 161-test integration Python suite also passed. Minimum host/admission availability was 19.73 GiB during CTest and 24.55 GiB during Python tests, with zero cgroup memory events. This is native regression evidence only; Phase 8 release packaging and Phases 5/6 remain open.

The latest tracked integration source at `0b28cd63` also completed fresh [maestro1 HIP and SYCL builds](../../bench/results/2026-10-18-phase8-maestro1-0b28cd63/README.md). The 801-file source manifest matched before compilation; HIP linked `strata` and SYCL completed 123/123 build steps, and both `--help` checks passed with the toolchain environments loaded. Builds used one job, Release mode and tests off. maestro1 is x86_64 with no usable accelerator runtime, so this is compile/link and CLI startup evidence only. Phase 8 remains open for the supported-profile release package and rollback validation beyond the one-token CLI smoke.

The pinned `0be090c` control binary and the current candidate also passed a same-input [Orin rollback smoke](../../bench/results/2026-10-18-phase8-rollback-smoke/README.md): each generated token ID `846` for input `248045`, with separate 28-GiB scopes, more than 8.9 GiB minimum physical availability and zero cgroup memory events. The pinned binary hash matches its original control manifest. This is one CLI inference cell, not API or performance evidence; rollback uses the control's compatible invocation together with its binary because the newer selected profile includes flags the pinned engine does not accept.

An earlier candidate passed a [Q2_0 selected-profile service check](../../bench/results/2026-10-18-phase8-current-source-q2-profile-smoke/README.md) with the 7,498-token retrieval prompt and same-service recovery. The latest current-source [rerun](../../bench/results/2026-10-19-phase8-current-source-q2-profile-smoke/README.md) used binary `b09ed0b5` from engine source `b6ea6188`: all three markers appeared once and in order, followed by `RECOVERED`; the independent reviewer passed. Across 322 samples, minimum host/admission availability was 18.05/8.57 GiB and cgroup event counters were zero. This is one functional cell, not a performance comparison or broad quality claim. Phase 8 remains open for supported-profile release packaging and broader rollback/API coverage; Phases 5 and 6 remain open.

| Phase | State | Evidence / next gate |
| --- | --- | --- |
| 0 — Repository and import | Complete | Pinned source/evidence manifest, source mapping, plan, offline planner checks |
| 1 — Same-day controls | Complete | Four same-day paired API blocks; exact workloads/artifacts; protocol and baseline checks; capability matrix records limits; expanded HIP/SYCL builds compile |
| 2 — Operator/state contracts | Complete | Ownership review, incompatible projection-profile rejection, independent RMS/IQ4_NL/Q6_K oracles, GDN prefix checks, default spec1 regression and post-fix spec1/spec4 token plus nine-field persistent-state parity recorded; native/HIP/SYCL build evidence and eleven selector tests pass; no NInfer execution component promoted |
| 3 — Memory and transfers | Complete for tested Orin Q2_0 scope | Owner/reservation, pressure, VMM/fallback, cancellation/recovery, cache/context, workspace and transfer gates are covered; no admitted run breached the six-GiB floor and no default changed. Exact graph-pool/private-driver bytes and a graph-disabled native control remain unsupported. See [Phase 3 closeout](PHASE3_CLOSEOUT.md). |
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

| 3 — Admission, memory ownership and transfer | Complete for tested Orin Q2_0 scope | See [Phase 3 closeout](PHASE3_CLOSEOUT.md). The post-soak PLE/CTest/Python rerun passed; graph-private allocation size remains unisolated and graph-disabled native service remains unsupported. |
| 4 — SM87/ARM kernels | Complete for tested candidates | See [Phase 4 closeout](PHASE4_CLOSEOUT.md). Q6_K warp-dequant meets real-shape oracle, held-out request and backend build checks for its recorded opt-in scope; Q8_1 NEON is contract-correct but had no serving win and remains opt-in; worker settings and CTA alternatives remain unpromoted. No default changed. Task-quality, energy and sustained-service evidence belong to later phases. |
| 5 — Speculation and graphs | In progress | The QSA spare-row transaction fix restores the dead key after accepted-prefix replay. MTP off/2/3/4 match IDs and accepted-prefix state across the tested Q2_0 prompts and FP16/INT8/Q4_0/K8V4 formats. The Coder IQ1_M accepted-only matrix now passes all four windows at 512 and 2,048 tokens, with state equality at every shared boundary. The current CUDA candidate also passed a focused 20-test transaction/verifier/KV/GDN/draft/captured-graph CTest selection; see the [regression report](../../bench/results/2026-10-18-phase5-current-cuda-ctest/README.md). The Q6 incident mismatch remains under default adaptive swaps. The opt-in `--adapt-accepted-only` path matches MTP-off output and persistent state in the tested prompt/KV/window matrices, and captured/eager output/state agree on a short Q2_0 case. The Q6 accepted-only seven-block screen confirms exact output parity across MTP off/window4 and warp off/on for its held-out request. The new three-pair 8K marker-retrieval ablation matched MTP-off output and recovery in all six arms; direct tracing matched final state and 14 shared accepted-prefix boundaries. Warm verifier graphs replay successfully after warmup. However, a same-service 512→2048→512 test changed 14/16 short output tokens after cadence-4 swaps for both MTP settings; `--adapt-every 100000` restored output and state equality. This points to swap-dependent output sensitivity but does not identify the arithmetic cause or quality impact. The initial 9K default-floor grow/trim test retained captured graphs and recovered short output/state, but MTP4 long-request state differed from MTP-off despite equal output; the same-context full-KV control passed. Follow-up tracing isolated this tested discrepancy to unequal expert-cache residency during growth: a 3,793-slot cache-matched 9K run and one held-out 15K run both passed state/output parity. Elastic KV × MTP remains unqualified beyond those tested prompt/cache cells. Cancellation/recovery passed after fixing stale usage staging. Source audit found no current per-proposal GDN state trajectory for ReplaySSM to replace: the verifier replays accepted prefixes from FP32 intermediates, and NInfer's BF16 records are incompatible. This is a design decision, not a measured speed or memory result; reconsider only with a measured removable-workspace target and exact FP32 recurrence oracle. Eager/captured performance, broader task-quality qualification and other termination paths remain open; see the [accepted-prefix and graph investigation](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/README.md), [same-service report](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/run/same-service-short-long-short/README.md), [KV grow/trim report](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/run/kv-grow-graph-recovery/README.md), and [long-context MTP retrieval ablation](../../bench/results/2026-10-14-phase5-q6-mtp-recall-ablation/README.md). |
A new [CUDA graph registry lifecycle regression](../../bench/results/2026-10-18-phase5-graph-lifecycle-regression/README.md) verifies updated input data over repeated replay at stable addresses and allocates replacement storage while the original graph is live, then destroys the old registry before recapturing the same graph key against the replacement addresses. The focused graph tests passed 2/2, the accepted-prefix/verifier/KV/GDN/draft/graph selection passed 21/21 under the 28-GiB supervisor, and integration Python tests passed 163/163. Minimum host/admission availability was 24.55/24.55 GiB for CTest, with zero sampled cgroup events. This covers the wrapper and caller ordering contract, not model graph-pool resizing or performance; Phase 5 remains open.

| 6 — Multivariate tuning | In progress | The original three-block worker × transfer screen was inconclusive; a seven-block held-out Q2_0/MTP4 confirmation found a pread request-time reduction at four workers but an inconclusive worker × transfer interaction. Audit corrected its MTP-off label: all 28 requests drafted 25 tokens and accepted 22. A distinct seven-block Q2_0 run with the MTP model absent completed the 4/8-worker × mapped/pread matrix; the interaction was −43.60 points (95% interval −77.21 to −19.39), while each fixed-worker transfer interval included no effect. This is scoped interaction evidence, with no setting promoted. The extended graph/eager screen completed seven MTP-off and three MTP2 pairs, but 2/7 eager MTP-off long outputs differed under short→long order. Direct no-swap and delayed-swap controls match the cold long-only output across captured/eager routes; the state trace changes output and is perturbative. A new seven-block held-out Q6_K warp × MTP confirmation measured warp request-time reductions of 7.25% (MTP off) and 6.15% (MTP4), with exact output parity only within each MTP regime. MTP-off and MTP4 outputs differed across all blocks, and the direct state trace found a material accepted-prefix mismatch, so these timings do not qualify a combined profile or promote a setting. The full-prompt delayed-swap control matches at 32 tokens but remains a correctness-only setting; default adaptive swaps and cadence-only adjustment still fail state parity. The boundary-capped accepted-row candidate passes this one prompt twice with exact state/output parity, but is correctness-only and not yet qualified across workloads or formats. A seven-block held-out Q2_0 graph × MTP2 confirmation on a 512/64 task found no graph/eager effect or interaction; MTP2 increased captured-route request time 6.12% (95% interval +0.38% to +7.12%) without a decode-throughput gain. Its full-task arms shared an opening-instruction failure. The follow-up [task-qualified graph × MTP comparison](../../bench/results/2026-10-16-phase6-q2-graph-mtp-quality-confirm7/README.md) passed all 28 arms on the validated processor task: graph/eager and interaction intervals included no effect, while MTP2 request time rose 4.12% captured and 3.86% eager and decode throughput fell in both routes. Neither result supports profile promotion; other workload interactions remain open. See [worker × transfer](../../bench/results/2026-10-12-phase6-q2-worker-transfer-rerun/README.md), [MTP4 confirmation](../../bench/results/2026-10-14-phase6-q2-worker-transfer-confirm7/README.md), [MTP-model-off confirmation](../../bench/results/2026-10-15-phase6-q2-worker-transfer-off-confirm7/README.md), [graph/eager](../../bench/results/2026-10-12-phase6-q2-graph-eager-full/README.md) and [seven-block confirmation/state investigation](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/README.md), plus [task-qualified graph × MTP confirmation](../../bench/results/2026-10-16-phase6-q2-graph-mtp-quality-confirm7/README.md). |
| 7 — Capacity and service | Complete for bounded Orin matrix | See [Phase 7 closeout](PHASE7_CLOSEOUT.md) and [evidence matrix](PHASE7_MATRIX.md). The selected Q2_0 MTP-off profile passed the documented 8K–256K retrieval/recovery points, arithmetic quality cells through 128K, 30-minute sustained service, API/cancellation/recovery, two-slot functional overlap and teardown checks. IQ1_M vision and cache-reuse results remain separate cohorts. Four-way concurrency, 256K arithmetic/sustained service, energy attribution and broader support are excluded; no profile default is promoted. |
| 8 — Release/upstream | In progress | Clean full HIP (313/313) and SYCL (123/123) compile/link builds passed on maestro1 from commit `4b72a72b`; both binaries returned successfully for `--help`, and the source manifest matched all 782 build-input files. A fresh current-source rebuild after the opt-in MoE capture and parity-tool changes also compiled and linked `strata` and `native_expert_parity`: HIP 84/84 and SYCL 125/125 build steps passed with one job. `strata --help` and each parity tool's no-argument usage path loaded successfully with their respective runtime libraries. These remain x86 compile/CLI checks only; no accelerator runtime was tested on maestro1. The native CUDA MTP-reset rebuild completed all targets. After commit `2b6dc076`, the current-source maestro1 HIP `strata` and `native_expert_parity` targets linked, and the SYCL `strata` target linked in 123 steps; both binaries passed `--help` load checks. These are x86_64 compile/CLI checks only; see the [latest backend report](../../bench/results/2026-10-14-phase8-mtp-reset-backends/README.md). The latest commit `0b28cd63` also passed a clean tracked-input manifest check, full HIP and 123-step SYCL builds, and both service `--help` checks; see the [current-source report](../../bench/results/2026-10-18-phase8-maestro1-0b28cd63/README.md). Full CTest ran 119 tests: 115 runnable tests passed, two optional IQ tests were skipped, and `expert_parity`/`pool_test` failed only because `pack/full/experts.bin` is absent; minimum host/admission availability was 20.39 GiB. Read-only upstream search on 2026-10-14 confirmed PR [#1621](https://github.com/Niko1221/Strata/pull/1621) remains open and separate, and found related open PRs for accepted-token cache barriers [#1779](https://github.com/Niko1221/Strata/pull/1779), pinned stage buffers [#1237](https://github.com/Niko1221/Strata/pull/1237), and compact Q8 fills [#1336](https://github.com/Niko1221/Strata/pull/1336). No distinct upstreamable source change is selected from the current measurements; no PR was opened. Remaining gates are final native runtime/default-path review, supported-profile and rollback packaging, and Phase 5/6 qualification. Phase 7’s bounded Orin matrix is closed under its closeout; Phase 8 must preserve its documented exclusions. See the [current-source MoE activation report](../../bench/results/2026-10-14-phase5-moe-activation-capture/README.md), [current-source native CTest report](../../bench/results/2026-10-14-phase8-native-full-ctest-current/README.md), [maestro1 backend report](../../bench/results/2026-10-14-phase8-maestro1-4b72a72/README.md) and [native CTest report](../../bench/results/2026-10-14-phase8-native-full-ctest/README.md). |

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
untested. Native CUDA rebuilt; no fresh remote backend build was claimed at
that point. A later probe found the ROCm and oneAPI toolchains in maestro1's
validation environment; clean current-source HIP and SYCL builds now pass in
the [Phase 8 backend report](../../bench/results/2026-10-14-phase8-maestro1-4b72a72/README.md).

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

The held-out [seven-pair 16K staging confirmation](../../bench/results/2026-10-13-phase3-q2-stage-pin-16k-heldout/README.md) followed the three-pair screen with a distinct exact-length prompt. All seven timing pairs matched output IDs, and a separate traced pair matched persistent state and stage ownership. Pinned request-time delta was −0.23% (paired 95% interval −2.47% to +0.72%), below the project threshold and spanning no change; median request time was 103.094 s pinned versus 102.873 s pageable. Minimum host availability was 17.505 GiB and effective headroom 7.477 GiB, with no OOM events. Pageable remains default; this candidate showed no reliable held-out benefit. Broader Phase 3 graph-backing and transfer gates remain open.

The staging harness now supports a byte-compatible `primary` prompt and an exact-length `heldout_blue` prompt; its focused tests passed 11/11 and full integration Python discovery passed 122/122.

A randomized [16K pageable-versus-pinned staging screen](../../bench/results/2026-10-13-phase3-q2-stage-pin-16k/README.md) completed three pairs with identical output IDs and persistent state. Each mode requested 337.5 MiB and balanced 256 stage allocations/frees per process. Pinned request time was lower in all three pairs (median paired delta −2.56%; interval −23.13% to −1.53%), but one pageable outlier and the three-pair sample leave this as screening evidence; no mode changed. Minimum host availability was 17.423 GiB and effective headroom 8.747 GiB, with zero OOM events. A seven-pair confirmation on a held-out prompt remains needed.

The owner/state-traced [18-GiB 16K repeat](../../bench/results/2026-10-13-phase3-q2-admit16k-18G-trace/README.md) also passed with a distinct warm-up; its target fingerprint matched the 22-GiB run and the observed allocation ledger again left only service-lifetime weights live. Minimum effective headroom was 6.205 GiB, only 0.205 GiB above the six-GiB floor. This is a narrow single-run pass, not an operating recommendation or capacity threshold.

The same exact [16K request at an 18-GiB cap](../../bench/results/2026-10-13-phase3-q2-admit16k-18G/README.md) completed both warm-up and measured calls. It retained 17.384 GiB minimum host availability and 8.338 GiB effective cgroup headroom, with zero OOM events. The 19-GiB run had 8.686 GiB effective minimum, showing that starting cache conditions affect headroom; the two cells do not establish a monotonic threshold. This 18-GiB run has no owner or state trace.

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


A fresh supervised [Q2_0 PLE and memory regression rerun](../../bench/results/2026-10-13-phase3-q2-ple-user-rerun/README.md)
passed all seven PLE stages for three tokens (worst relative L1 `1.148e-7`),
the selected 15/15 memory/owner/PLE CTests, and integration Python discovery
(124/124). Minimum host availability was 24.42 GiB for PLE and 24.45 GiB for
CTest. This refreshes selected contracts; physical and graph backing under
broader pressure remain open.

The randomized held-out [seven-pair Q2_0 16K mapped-versus-pread confirmation](../../bench/results/2026-10-13-phase3-q2-mapped-pread-16k-heldout/README.md)
matched output IDs, cache capacity and all nine state fields in every pair.
Pread's median request time was 2.23% lower (paired bootstrap 95% interval
−3.91% to −1.94%); prompt time improved 2.42%, while decode was 6.33% slower.
The request gain is below the proposed 5% promotion threshold and decode
exceeds its regression guard, so mapped remains the default. Process major
faults and whole-device reads favored pread, but shared page-cache conditions
and unscoped NVMe counters prevent a cold-read or product-wide conclusion. The
28-GiB systemd ceiling preserved 17.76 GiB minimum host availability and 7.34
GiB effective headroom, with zero OOM kills. Phase 3 remains open for broader
transfer alternatives and graph/driver physical-backing accounting.

A fresh [Q2_0 exact-16K cancellation/recovery run](../../bench/results/2026-10-13-phase3-q2-cancel-16k/README.md)
closed the stream after 1.02 seconds with 512 of 16,384 prompt tokens read and
no output tokens. The same live service then returned `Hello Orin!` (five
tokens). The 28-GiB scope retained 17.10 GiB minimum host availability and
14.82 GiB effective headroom, with zero OOM events. The 304/303 requested
owner ledger left only the service-lifetime weight arena live. This adds one
intermediate-length cleanup/recovery point; broader pressure and graph/driver
backing gates remain open.

The exact [Q2_0 32K cancellation/recovery repeat](../../bench/results/2026-10-13-phase3-q2-cancel-32k/README.md)
also passed at 64K configured context. The stream closed after 1.04 seconds
with 512/32,768 prompt tokens read and no output; the same service returned
`Hello Orin!`. Minimum host and effective headroom were both 16.38 GiB, with
zero OOM events. The 304/303 owner ledger again left only resident weights
live. This is one cell, not a long-context quality claim; graph/driver backing
and broader pressure gates remain open.

A [fine-resolution Q2_0 graph/NVMap trace](../../bench/results/2026-10-13-phase3-q2-graph-fine-nvmap/README.md)
sampled the process NVMap owner counter at a requested 2-ms interval across
three fresh short-request processes. The two later verifier-graph events each
had repeatable 20-ms event-centered owner deltas of 23,117,824 and 22,831,104
bytes, with no instrumented ordinary allocation/free event in those windows.
The nearest-sample changes were smaller and phase-dependent; the first
verifier and commit-graph brackets overlap. This narrows graph-related
attribution but does not isolate executable/pool bytes. The native graph-off
control remains unsupported, so graph-memory qualification remains open.

The held-out [seven-pair 16K prefetch-fill versus staging confirmation](../../bench/results/2026-10-13-phase3-q2-prefetch-stage-16k-heldout/README.md)
passed output, cache-slot and all nine persistent-state comparisons in every
pair. Staging was +0.40% slower end to end (paired 95% bootstrap interval
+0.17% to +1.86%); prompt time was +0.40%, while decode was −0.67% with an
interval spanning no change. Major faults rose from a 38,262 median to 58,975.
The 28-GiB scope retained 17.77 GiB minimum host availability and 7.32 GiB
effective headroom, with zero OOM kills. Shared page cache and whole-device
I/O counters limit storage conclusions; board energy is not process-attributed.
Keep fill-only behavior and defaults unchanged. This closes the held-out
staging comparison for this cell; Phase 3 remains open for broader pressure,
unique physical backing and graph accounting gates.

The held-out [seven-pair 32K Q2_0 mapped-versus-pread confirmation](../../bench/results/2026-10-13-phase3-q2-mapped-pread-32k-heldout/README.md)
matched output IDs, actual cache slots and all nine persistent-state fields in
every pair. Pread's paired median request delta was −1.12%, but two pair
reversals widened the 95% interval to −1.58% through +16.23%; prompt and decode
intervals also span regressions. Major faults and whole-device reads favored
pread, but cache was shared and device counters include unrelated I/O. Minimum
host availability was 17.17 GiB and effective headroom 7.70 GiB under the
28-GiB scope, with zero OOM kills. Keep mapped as default. This adds a held-out
32K point without establishing a general transfer winner; Phase 3 remains open.

A [64K-context fine NVMap graph trace](../../bench/results/2026-10-13-phase3-q2-graph-fine-nvmap-context64k/README.md)
repeated the supported short request in three fresh processes. The second
verifier event again had a repeatable 23,117,824-byte event-centered bracket;
the third event varied from 6.36 to 22.83 MB, unlike the stable 8,232-context
trace. No instrumented ordinary device allocation/free event fell within the
brackets. The 28-GiB campaign retained 16.39 GiB minimum host availability and
13.22 GiB effective headroom with zero OOM kills. This variation does not
isolate graph-pool bytes or support a context sizing rule; graph/driver physical
backing remains open.

A [64K-context spec4 fine NVMap trace](../../bench/results/2026-10-13-phase3-q2-graph-fine-nvmap-context64k-spec4/README.md)
passed the same short request in three fresh processes. It instantiated two
verifier graphs; the later verifier event had a repeatable 22,896,640-byte
20-ms owner bracket, close to spec2's 23,117,824 bytes at the same context.
The first-event bracket ranged from 6.29 to 8.45 MB. Minimum host and effective
headroom were both 16.31 GiB, with no OOM events. These are event-centered
NVMap owner changes, not isolated graph-pool sizes; graph-memory qualification
remains open.

The 64K-context spec3 NVMap trace passed in three fresh processes. It
instantiated three verifier graphs; events two and three had repeatable 23.78
MB and 22.83 MB event-centered owner brackets. A spec1 attempt was refused
before readiness because native Q2_0 requires spec >= 2; its no-request result
is retained as unsupported. These traces extend graph-owner coverage across
supported spec2/3/4 settings, but do not isolate graph-pool storage, so the
Phase 3 graph accounting limitation remains explicit. See the spec3 trace
(../../bench/results/2026-10-13-phase3-q2-graph-fine-nvmap-context64k-spec3/README.md)
and spec1 refusal
(../../bench/results/2026-10-13-phase3-q2-graph-fine-nvmap-context64k-spec1/README.md).

The [IQ1_M graph × MTP screen and held-out confirmation](../../bench/results/2026-10-14-phase6-iq1-graph-mtp-screen/README.md)
matched captured/eager output IDs, final persistent state and every shared
accepted-prefix checkpoint for MTP off/2/3/4 on a distinct 2,048-token prompt.
The initial three-pair MTP4 screen showed a large but inconsistent eager
decode gain. In seven randomized held-out pairs all 14 arms passed, outputs
matched, and eager's paired median request change was −0.57% (95% bootstrap
interval −1.10% to +0.69%); prompt and decode intervals also included no
change. Minimum host/effective availability was 13.12 GiB. The screen result
did not replicate, so capture remains unchanged and no profile is promoted.
Phase 6 remains open for other workload, KV and interaction cells.

The accepted-only adaptive-usage fold is now isolated in a small transaction
helper and directly tested for commit lengths 0/1/intermediate/all, rejected
suffix isolation, staging-size changes between windows, and malformed input.
Five focused CUDA CTests passed; the rebuilt IQ1_M Orin service matched MTP-off
and MTP4 token IDs, final state, and all 17 shared commit boundaries. The
changed generator also rebuilt and linked in maestro1's HIP tree. An initial
comparison overlapped an accidentally launched unsupervised process and is
retained as confounded; the isolated supervised rerun passed. This strengthens
the accepted-row boundary but does not close Phase 5's wider transaction,
quality, or termination gates. See the [refactor record](../../bench/results/2026-10-14-phase5-accepted-usage-refactor/README.md).

A [three-block randomized Q6 cache × context screen](../../bench/results/2026-10-14-phase6-q6-cache-context/README.md)
completed all 12 fresh-service cells and 36 measured requests. Every request
used 512 prompt tokens and generated 64 tokens without prompt-cache reuse; all
cells passed the 28-GiB process ceiling and six-GiB host-availability floor.
Actual cache allocation under the 5,000 `--expert-cache` budget setting varied
(4,600–6,519 resident slots), and response text was not byte-identical in every request. The prompt
was capped before its 200-word quality rubric could be checked, so the
throughput and interaction estimates remain exploratory. This screen does not
promote a cache/context profile or close Phase 6; held-out quality and
confirmation evidence remain necessary.

An IQ1_M [long-prefill cancellation and recovery check](../../bench/results/2026-10-14-phase5-q6-prefill-cancel-recovery/README.md)
closed the 7,498-token stream after the engine read its first 64 prompt tokens
and before generation. The same MTP4 accepted-only service then returned
`Hello Orin!` and remained alive. Under a 28-GiB cgroup cap, minimum host and
effective availability were 12.95 GiB, with no OOM events. This adds one
long-prefill termination point; it does not compare persistent state after
cancellation or close Phase 5's other termination and quality gates.

An IQ1_M [decode-cancellation accepted-prefix comparison](../../bench/results/2026-10-14-phase5-q6-decode-cancel-state-parity/README.md)
then canceled after eight stream deltas and 12 committed tokens. Three fresh
exact-length references matched token IDs and all 11 persistent-state fields at
four shared boundaries (48, 51, 55, 59), as well as matching one another. The
same service recovered with `Hello Orin!`. Minimum host availability was 13.07
GiB and effective headroom was 12.23 GiB under the 28-GiB cap, with no OOM
events. This covers one decode-cancel point for Q6 MTP4 and leaves other
termination, quality and format gates open.

The [Q6 16K accepted-prefix comparison](../../bench/results/2026-10-14-phase5-q6-mtp-16k-state-parity/README.md)
extended the direct MTP-off/MTP4 trace to the 15,003-token retrieval prompt.
Both arms returned all three markers in order and matched token IDs, all nine
persistent-state fields, and each of 14 shared commit boundaries through 41
generated tokens. MTP4 offered/accepted 34/30 drafts. Minimum host/effective
availability was 13.01 GiB in the 28-GiB supervised run. This is one long
prompt and one profile, with no performance claim; broader quality and format
coverage remain open.

A [three-block Q6 prefill-chunk × cache-budget screen](../../bench/results/2026-10-14-phase6-q6-prefill-cache/README.md)
also passed all 12 fresh-service cells and 36 measured requests. Prefill chunk
128 improved prompt throughput in every paired block and lowered median request
time, while decode-rate changes were small and varied with cache setting.
Actual allocation under the 5,000 `--expert-cache` budget ranged from 5,378 to
6,519 resident slots; minimum host availability was 8.29 GiB with no OOM
events. The 512/64 output cap was too short for the task-quality rubric, so this
is exploratory only and does not promote a setting or close Phase 6.

A [full-task quality follow-up](../../bench/results/2026-10-14-phase6-q6-prefill-cache/quality-full-task/README.md)
then reran the same four cache-budget × prefill-chunk conditions with a 512-token
allowance and one fresh service per condition. All four outputs ended naturally
at 315–340 tokens, passed the complete 200-word rubric, and used exactly 512
prompt tokens with no cache reuse. The 28-GiB scope retained 8.16 GiB minimum
host/effective availability; sampled OOM and cgroup limit event counters stayed
zero. This closes only the task-success check for that prompt and four settings;
one request per condition is not a quality comparison or held-out performance
confirmation, so no setting is promoted and Phase 6 remains open.

A [seven-pair held-out prefill confirmation](../../bench/results/2026-10-14-phase6-q6-prefill-confirm7/README.md)
then compared chunks 32 and 128 at fixed cache budget 3,000 on a distinct
1,069-token prompt. All 14 arms passed with 3,903 resident slots; chunk 128
raised median prompt throughput 196.4% (95% paired bootstrap interval
196.4–204.6%) and lowered median client time 65.7% (−66.5% to −65.6%). Minimum
host availability was 13.10 GiB, effective headroom 10.60 GiB, and sampled
cgroup OOM/limit counters stayed zero. However, the generated eight-token
prefix differed between settings in all seven pairs (stable within each arm),
so this short-generation performance confirmation does not establish output
parity or task quality and cannot support profile promotion.

The same 1,069-token prompt was then allowed to complete at both chunk sizes.
Each response ended naturally and exceeded 200 words, but both failed the
prompt's explicit opening instruction to start with the processor. This is a
task failure for both settings, not evidence of a relative quality difference.
The performance signal remains valid only for its short-generation workload;
no profile is promoted. See the [held-out full-task result](../../bench/results/2026-10-14-phase6-q6-prefill-confirm7/quality-full-task/README.md).

A subsequent [current-checkout Q2_0 PLE and Phase 3 refresh](../../bench/results/2026-10-14-phase3-q2-ple-current/README.md)
again passed the artifact-aware PLE oracle (7/7 stages, three tokens, worst
relative L1 `1.148e-7`), selected Phase 3 CTests (15/15), and Python discovery
(130/130). Minimum host/effective availability was 24.284, 24.407, and 24.377
GiB, respectively, under separate 28-GiB scopes with zero cgroup pressure
counters. This reconfirms, without extending, the documented Phase 3 scope.

A [three-block randomized Q2_0 graph × MTP2 screen](../../bench/results/2026-10-14-phase5-phase6-graph-mtp-screen/README.md)
completed all 12 captured/eager × MTP-off/window2 cells. Every 512/16 request
passed and returned identical output text; MTP2 offered/accepted eight/six
drafts in every cell. Prompt timing varied too widely for this small synthetic
screen to distinguish route effects, and decode results did not show a stable
MTP win. The 28-GiB scope retained 16.70 GiB minimum host availability and
6.66 GiB minimum admission availability, with zero cgroup OOM/limit events.
Clock readings were dynamic, EMC access was unavailable, and energy was not
measured per process. This is screening evidence only: no route or serving
profile is promoted, and Phase 5 state/quality gates and Phase 6 held-out
confirmation remain open.

The follow-up [seven-block held-out Q2_0 graph × MTP2 confirmation](../../bench/results/2026-10-14-phase6-q2-graph-mtp-confirm7/README.md)
completed all 28 captured/eager × MTP-off/window2 cells on a distinct 512/64
prompt. Output text matched across every block; all MTP2 cells offered/accepted
33/24 drafts and used the same resident cache and FP16 KV. Neither graph/eager
main effect had a request-time interval excluding no change, and the graph ×
MTP interaction interval also included zero. On this workload MTP2 increased
captured-route request time 6.12% (95% paired bootstrap interval +0.38% to
+7.12%) and reduced prompt throughput 10.33% (95% paired bootstrap interval −11.75% to −1.05%); decode did not improve.
Minimum host and admission availability were 16.85 and 13.12 GiB, with zero
cgroup limit/OOM events. This does not support a default change and does not
qualify longer workloads, other KV formats or MTP windows.

The [task-qualified graph × MTP follow-up](../../bench/results/2026-10-16-phase6-q2-graph-mtp-quality-confirm7/README.md)
repeated this 2×2 comparison with the previously validated processor task,
2,094 prompt tokens and a natural 293-token answer. All 28 cells passed its
opening phrase, topic, arithmetic, length and natural-stop checks, with exact
text equality. Across seven randomized fresh-service blocks, captured/eager
request-time effects were −0.04% with MTP off (95% interval −0.80% to +0.97%)
and +1.11% with MTP2 (−1.05% to +2.07%); the graph × MTP request-time
interaction was +0.37% (−1.06% to +1.58%). MTP2 increased request time 4.12%
(+3.52% to +6.36%) captured and 3.86% (+1.91% to +5.61%) eager, while decode
throughput fell 6.10% and 4.94%, respectively, with both intervals excluding
zero. Minimum host/admission availability was 16.925/11.630 GiB with zero
cgroup event counters. This resolves the prior task-specific quality gate but
supports no default/profile promotion and does not qualify other prompts,
contexts or cache policies. Phase 6 remains open.

A Q2_0 [MTP task-quality check](../../bench/results/2026-10-14-phase5-q2-mtp-quality/README.md)
then ran a 2,048-token computer-processing task with MTP off, MTP2 and MTP4
under the accepted-only adaptation policy. All three fresh services produced
the same naturally completed 293-token answer and passed the full prompt rubric;
MTP2 and MTP4 each offered/accepted 155/108 drafts. A follow-up [MTP3 task
check](../../bench/results/2026-10-14-phase5-q2-mtp3-quality/README.md) used
the same task and policy on the current binary; its naturally completed answer
also passed and matched all three existing answer hashes exactly. Minimum host
availability was 17.02 GiB and minimum admission availability 12.77 GiB under
the 28-GiB scope. These are task-quality checks, not broad quality or
performance evidence; MTP remains opt-in and Phase 5 remains open.

A current-binary [Q2_0 128-token accepted-prefix comparison](../../bench/results/2026-10-14-phase5-q2-accepted-prefix128-current/README.md)
then compared MTP off/2/3/4 on a 2,048-token prompt under both no-swap and
accepted-only adaptive-swap policies. All outputs and final persistent state
matched; every shared accepted-prefix fingerprint matched across 75/64/55
boundaries without swaps and 83/71/61 with accepted-only swaps for MTP2/3/4.
Drafts offered/accepted were 74/53, 126/64 and 162/73 without swaps and 67/45,
101/57 and 132/67 with swaps. The 28-GiB supervisors retained at least 16.867
GiB host availability and 8.703 GiB admission availability, with zero cgroup
pressure or OOM events. This extends longer-chain parity to two policies for
one Q2_0 prompt/cache; it does not resolve other prompt/cache sensitivities or
provide timing evidence. Phase 5 remains open.

A current-binary [256-token Q2_0 accepted-prefix extension](../../bench/results/2026-10-14-phase5-q2-accepted-prefix256-current/README.md)
then compared MTP off/2/3/4 on the same exact 2,048-token prompt with
accepted-only swaps. All four arms emitted the same 256 token IDs and matched
all nine persistent-state fields at final state and every shared accepted
prefix. MTP2/3/4 offered/accepted 136/88, 201/106 and 264/122 drafts, with
168/150/134 shared boundaries. The 28-GiB supervisor retained 16.935 GiB
minimum host availability and 8.107 GiB minimum admission availability; sampled
cgroup pressure, limit and OOM counters stayed zero. This extends one prompt
and cache cell's long-chain correctness evidence, not performance or task
quality; it does not resolve the separate residency-change recovery drift.
Phase 5 remains open.

A follow-up [8K-prompt Q2_0 MTP accepted-prefix check](../../bench/results/2026-10-14-phase5-q2-accepted-prefix8k-current/README.md)
used the current binary, 16K context and the accepted-only adaptive-swap
policy. MTP off/2/3/4 returned the same 32 token IDs and final state, with
direct equality at all shared state boundaries (22/19/15 for MTP2/3/4).
Drafts offered/accepted were 17/10, 24/13 and 31/17. The 28-GiB supervisor
retained 16.713 GiB minimum host availability and 9.581 GiB minimum admission
availability, with zero cgroup pressure or OOM events. This adds one long-
prefill correctness cell; it is not task-quality or performance evidence.
Phase 5 remains open.

The same exact 8K prompt then received a [full-task quality check](../../bench/results/2026-10-14-phase5-q2-mtp8k-quality/README.md)
with a 512-token allowance under MTP off/2/3/4. All four fresh services
stopped naturally at 311 tokens, returned byte-identical 264-word responses,
and covered fetch/decode/execute, RAM, binary information, input/output and
storage. They all failed the same explicit opening instruction to start with
the processor. Minimum host availability was 16.618 GiB and admission
availability 13.539 GiB, with zero cgroup pressure or OOM events. This shared
task failure does not indicate an MTP quality difference and does not qualify
the profile; the separate 32-token accepted-prefix parity check remains
correctness evidence only. Phase 5 remains open.

A separate [Q2_0 8K prefill cancellation and recovery check](../../bench/results/2026-10-14-phase5-q2-mtp8k-prefill-cancel/README.md)
closed the client stream after 15 seconds. The engine had read 512 of 8,192
prompt tokens and generated none. The same service then returned `Hello Orin!`
in 7.53 seconds and remained healthy. The 28-GiB supervisor retained 16.712
GiB minimum physical host availability and 16.712 GiB minimum admission
availability; sampled cgroup pressure and OOM counters stayed at zero. This
qualifies one cancellation point and short-request recovery for Q2_0 MTP4; it
does not compare persistent state after cancellation or cover other positions.
Phase 5 remains open.

A supervised [Q2_0 decode-cancellation state comparison](../../bench/results/2026-10-14-phase5-q2-decode-cancel-state-parity/README.md)
then canceled an accepted-only MTP4 stream after four nonempty deltas. Six
tokens were committed, and the same service recovered with `Hello Orin!`.
Two fresh exact-length references matched token IDs and all 11 persistent
fields at shared accepted-prefix lengths 48, 50, 51 and 53, and matched each
other. The prompt rendered to 48 tokens. Minimum host and admission availability
were 16.731 and 15.910 GiB under the 28-GiB cap, with no cgroup pressure or OOM
events. This covers one short-prompt Q2_0 cancellation cell; longer-prefix,
long-prompt, other-window/format and quality gates remain open.

The same held-out Q2_0 graph/MTP prompt received a separate full-task quality
check across all four settings. With a 1,024-token allowance each answer ended
naturally at 850 tokens, was byte-identical, and covered input, working memory
and storage, but failed the explicit instruction to begin with the memory
controller by opening with meta-commentary about the repeated-blue context.
All four 512-token-cap attempts stopped mid-sentence and are excluded. This is
a shared task failure, not a route difference; it does not qualify a profile.
The outcomes are retained with the [Phase 6 confirmation](../../bench/results/2026-10-14-phase6-q2-graph-mtp-confirm7/README.md).

A replacement [Q2_0 semantic graph × MTP confirmation](../../bench/results/2026-10-14-phase6-q2-semantic-graph-confirm7/README.md)
used an exact 512-token held-out prompt in seven randomized blocks. All 28
captured/eager × MTP-off/MTP2 cells passed, generated identical text, and
preserved at least 16.899 GiB physical host availability and 11.832 GiB
admission availability. Full-task checks under all four conditions then
naturally stopped at 334 tokens, passed the 11-item task rubric, and returned
byte-identical answers; minima were 16.928 GiB host and 13.454 GiB admission
availability. Captured versus eager request-time intervals included zero in
both MTP settings. MTP2 increased median request time by 16.93% captured and
11.52% eager, with paired 95% intervals excluding zero. This task-qualified
finding is limited to this Q2_0 artifact, prompt, cache and adaptation policy;
energy was not request-attributed and no profile/default is promoted. Phase 6
remains open for other workload and interaction cells.

A three-block randomized [Q2_0 8K MTP4 versus MTP-off screen](../../bench/results/2026-10-14-phase6-q2-mtp8k-window-screen/README.md)
used fresh services, a distinct 512-token warmup, a 7,498-token retrieval
prompt, disabled prompt reuse and no adaptive swaps. All six measured requests
returned the same 41-token answer. MTP4 accepted 29/33 drafts; its median decode
delta was +27.16% (three-pair bootstrap interval −3.98% to +28.78%), while
median client TTFT and total-request time were 7.63% and 5.64% slower. This
prefill-dominated screen does not justify a held-out timing confirmation or
profile promotion. No setting changed, and Phase 6 remains open.

A [7,498-token Q2_0 MTP4 decode-cancellation state check](../../bench/results/2026-10-14-phase5-q2-mtp8k-cancel-state-parity/README.md)
extended the cancellation comparison from a short prompt. After four stream
deltas the service had committed six tokens; two fresh exact-length references
matched token IDs and all 11 persistent-state fields at accepted-prefix
lengths 7,498, 7,500, 7,501 and 7,503. The same service recovered with the exact
`Hello Orin!` response. Minimum host/effective availability was 16.86/6.76
GiB under the 28-GiB cap, with zero sampled cgroup pressure or OOM events. The
first attempt is retained but excluded because its 1,024-token generation
allowance did not fit in the 8K context; the qualified rerun used 48 tokens.
The cancellation harness now accepts prompt files and explicit generation
allowances; focused tests passed 9/9 and integration Python discovery 136/136.
This covers one long-prompt cancellation point and does not close Phase 5's
other termination, KV-format, quality or graph-lifetime gates.

A follow-up [8K prefill cancellation state comparison](../../bench/results/2026-10-14-phase5-q2-mtp8k-prefill-cancel-state-parity/README.md) compared same-service recovery with a fresh service. Before the fix, two runs matched all target-state hashes but differed in the MTP draft-state hash after cancellation. A new MTP sequence now clears draft QSA KV/index state at the same `resume=0` boundary as the target state; conversation resumes still restore their saved draft prefix. Two post-fix FP16 runs and one int8-KV run matched all 11 persistent fingerprints at `L=24` and returned `Hello Orin!`; a fourth run confirmed same-service API recovery with prompt cache disabled, where state hashes are unavailable. The FP16 minima were 16.68/14.69 and 16.77/15.45 GiB host/admission; int8 was 16.78/16.31 GiB and no-cache was 16.69/16.69 GiB, with no sampled pressure or OOM events. This fixes the tested MTP4/8K cancellation-recovery cell for FP16 and int8 KV; other cancellation positions, windows and formats remain open. PLE passed 7/7 stages, selected CTests 15/15, and integration Python tests 141/141 after the source change.

After the fresh-sequence MTP reset, the held-out 7,498-token Q2_0 MTP4 decode-
cancellation check was repeated on the current binary. Cancellation committed
six tokens after four visible deltas; two fresh exact-length references matched
the canceled token IDs and all 11 state fields at each of four shared lengths
(7,498/7,500/7,501/7,503), and same-service recovery returned `Hello Orin!`.
Minimum host/admission availability was 16.766/7.181 GiB under the 28-GiB
scope, with zero cgroup pressure/OOM events. This adds one post-fix decode
cancellation point and does not close the other termination or graph-lifetime
gates. See the retained
[post-reset decode cancellation report](../../bench/results/2026-10-14-phase5-q2-mtp4-decode-cancel-post-reset/README.md).

The Q2_0 [compact-KV MTP parity checks](../../bench/results/2026-10-14-phase5-q2-kv-mtp-parity/README.md)
then compared MTP off/2/3/4 with int8 and q4_0 KV on the same 2,048-token
prompt, 128-token continuation and accepted-only swap policy. All eight arms
matched MTP-off token IDs and final persistent state; all shared accepted-prefix
boundaries matched (int8: 84/74/65 for MTP2/3/4; q4_0: 82/75/64). Minimum
host/effective availability was 17.058/8.798 GiB for int8 and 16.977/9.068 GiB
for q4_0 under separate 28-GiB scopes, with zero sampled cgroup pressure or
OOM events. These are traced state-correctness checks, not quality or timing
claims; other prompts, formats and the remaining Phase 5 gates remain open.

A seven-block held-out [Q2_0 prefill-chunk × expert-cache confirmation](../../bench/results/2026-10-14-phase6-q2-prefill-cache-confirm7/README.md) crossed chunk sizes 32/128 with 3,000/5,000 cache-budget arguments. All 28 fresh-service cells and 84 exact-answer requests passed. Chunk 128 reduced median request time 42.65% at 3,000 budget and 40.86% at 5,000; prompt rate rose 87.60% and 85.94%, respectively. The cache effect at chunk 32 and the cache × chunk interaction were inconclusive; the 5,000 budget was nominally slower at chunk 128, but three 5,000-budget cells admitted only 3,861–4,853 actual slots, which confounds that comparison. Minimum host availability was 14.45 GiB, with zero sampled cgroup high/max/OOM counters; `tj` ranged 50.2–59.8 °C. Energy was not request-attributed and no default changed. This supports chunk 128 for this bounded Q2_0 task only. Phase 6 remains open.

A follow-up [fixed-slot Q2_0 cache × prefill confirmation](../../bench/results/2026-10-15-phase6-q2-prefill-cache-fixedslots/README.md) screened and then crossed chunks 32/128 with exact 3,000/3,500-slot caches in seven randomized blocks. All 28 cells and 84 answers passed. Chunk 128 reduced median request time 40.47% at 3,000 slots (paired 95% interval −54.77% to −34.46%) and 42.42% at 3,500 (−43.10% to −41.50%). The first three-measurement-per-cell run showed the 3,500-slot cache slower than 3,000 by 12.53% at chunk 32 and 9.67% at chunk 128. A separate seven-block one-measurement-per-cell confirmation sampled actual clocks and instead showed the larger cache slightly faster (−1.06% and −3.35%, respectively). This reversal leaves the cache-size effect unresolved. The cache × chunk interval crossed zero in the first run (−1.51 points, −8.65 to +13.27); the second showed a small interaction (−1.17 points, −1.65 to −0.33), so it remains exploratory. The initial run's minimum host/admission availability was 16.33/6.66 GiB; cgroup pressure/OOM counters stayed zero. Clock-sampled GPU frequency ranged 306 MHz–1.300 GHz, CPU 730 MHz–2.202 GHz, and `tj` ranged 48.5–57.2 °C; EMC readback was unavailable and energy was not request-attributed. No default changed. The chunk result is scoped to this task/profile; Phase 6 remains open.

A separate seven-block [Q2_0 long-prompt prefill confirmation](../../bench/results/2026-10-15-phase6-q2-prefill-long-workload/README.md) tested a held-out 7,501-token retrieval prompt at exact 3,000-slot capacity with FP16 KV and MTP off. All 14 fresh-service cells returned the exact three-marker answer after exactly 7,501 prompt tokens and 36 completion tokens. Chunk 128 reduced median total request time by 59.56% (paired 95% interval −59.62% to −57.50%) and increased median prompt rate 149.6%; all seven blocks favored chunk 128. Minimum host/effective admission availability was 17.85/6.11 GiB, with the latter only 0.11 GiB above the six-GiB floor; cgroup pressure/OOM counters stayed zero. Dynamic GPU clocks ranged 306 MHz–1.3005 GHz and CPU clocks 729.6 MHz–2.2016 GHz; EMC readback was unavailable and energy was not request-attributed. This confirms the chunk direction for this near-limit task/profile only. No default changed, and Phase 6 remains open.

A seven-block held-out [Q2_0 expert-cache × context confirmation](../../bench/results/2026-10-14-phase6-q2-cache-context-confirm7/README.md) then compared 3,000/5,000 slots at 8K/16K context. All 28 fresh-service cells passed; all 84 measured replies exactly matched the 512-token retrieval-plus-arithmetic oracle and 47-token answer. The larger cache reduced median engine-reported request time by 7.91% at 8K (paired 95% interval −10.29% to −5.67%) and 11.20% at 16K (−16.81% to −9.66%). Context effects were inconclusive, and the cache × context interaction remains screening evidence for this one task. Minimum host availability was 14.14 GiB above the six-GiB floor; tegrastats `tj` ranged 49.1–58.6 °C. Energy was not request-attributed, and no default changed. Phase 6 remains open.

A current-source seven-block [Q2_0 cache × context confirmation](../../bench/results/2026-10-18-phase6-q2-cache-context-current-source-confirm7/README.md) repeated that held-out task against source commit `c1eb609d`. All 28 fresh-service cells and 84 measured answers passed; all cells admitted exactly their requested 3,000 or 5,000 expert slots. The larger-cache timing contrasts included no change at either context (median +15.41% at 8K, interval −1.00% to +20.22%; −2.89% at 16K, −4.72% to +0.96%). The 16K context was slower at 3,000 slots (+8.43%, +2.49% to +23.26%) and indistinguishable at 5,000 slots (−0.43%, −1.17% to +2.52%); the cache-by-context interaction was −13.67 percentage points (−22.32 to −2.30). Minimum host/effective admission availability was 15.33/13.50 GiB, with zero sampled cgroup pressure/OOM events. Dynamic GPU clocks ranged 306 MHz–1.3005 GHz, CPU 729.6 MHz–2.2016 GHz, and `tj` 52.1–58.7 °C; EMC readback was unavailable and energy was not request-attributed. This current-source repeat still does not establish a general cache/context setting or change defaults. Phase 6 remains open.

A seven-block held-out [Q2_0 worker × expert-transfer confirmation](../../bench/results/2026-10-14-phase6-q2-worker-transfer-confirm7/README.md)
completed all 28 trace-free cells for 4/8 workers × mapped/pread on a distinct
512-token retrieval-plus-arithmetic task. All responses returned the exact
three markers and sum `1768`. Pread reduced median request time 15.82% at four
workers (paired bootstrap 95% interval −19.55% to −9.92%); at eight workers,
its interval included no change. The worker × transfer difference-in-
differences interval also included zero, and one four-worker/pread outlier
remains unexplained. Minimum host/effective availability was 16.70/6.91 GiB;
sampled cgroup pressure and OOM counters stayed zero. This supports only the
four-worker/pread cell on this task; shared page-cache history prevents a cold-
disk conclusion, so no default changed. Phase 6 remains open for other
interactions and workloads.

A separate seven-block [Q2_0 MTP-model-off worker × transfer confirmation](../../bench/results/2026-10-15-phase6-q2-worker-transfer-off-confirm7/README.md)
completed all 28 randomized cells for four/eight workers × mapped/pread on a
held-out 512-token retrieval-plus-arithmetic task. `--spec 2` remained as the
pack-required verifier window, while no MTP model or MTP cap was configured.
All cells returned the exact planted codes and suffix sum; output hashes and
actual cache capacity matched. The worker × transfer difference-in-differences
was −43.60 percentage points (paired bootstrap 95% interval −77.21 to −19.39).
The transfer-effect intervals at fixed worker counts both included no change,
so the interaction does not justify a default. Minimum host/effective
availability was 17.34/6.46 GiB; cgroup pressure and OOM counters stayed zero.
The initial setup attempt omitted the verifier-window option and is retained as
an excluded pre-measurement failure. Shared page-cache history prevents a cold-
disk conclusion. Phase 6 remains open for other factors and workloads.

A current-source seven-block [Q2_0 worker × transfer confirmation](../../bench/results/2026-10-19-phase6-q2-worker-transfer-current-source-confirm7/README.md) repeated the 4/8-worker × mapped/`pread` matrix on the current candidate binary. All 28 cells returned the exact 512-token retrieval-plus-arithmetic answer with 46 completion tokens and 3,000 exact cache slots. The paired worker, transfer and interaction intervals all included no change; several decode-time outliers widened the effects, so no setting changed. Minimum host/admission availability was 17.47/6.25 GiB over 2,237 samples, with zero cgroup memory events. A separate integration of retained tegrastats samples estimated three named rails over all 28 request windows. The rail measures include board idle/background activity and are not process-attributed; their paired intervals are broad and support no energy choice. This refreshes the interaction evidence at current source but does not qualify cold-disk behavior. Phase 6 remains open for other interactions and process-attributed energy/Pareto work.

A same-day three-block [Q2_0 MTP-window × KV-format screen](../../bench/results/2026-10-14-phase6-q2-mtp-kv-window-screen/README.md)
compared MTP off/2/3/4 under FP16 and int8 KV on the held-out 512-token
semantic task. All 24 fresh-service cells passed, matched output within each
format/block, and used 3,000 actual expert slots. Window 2 improved median
decode rate by 8.78% with int8 KV and 2.77% with FP16; window 3 improved it by
8.43% and 2.47%. Window 4 reduced decode rate by 5.98% and 9.83%, respectively.
All three windows had higher TTFT medians, and the total-request effects were
small for windows 2/3 but slower for window 4. Minimum physical host/admission
availability was 16.914/6.278 GiB for int8 and 16.842/6.454 GiB for FP16, with
zero sampled cgroup high/max/OOM events. This is a three-block timing screen:
the two format campaigns ran sequentially, clocks were dynamic, and generation
was capped at 64 tokens. The format interaction remains exploratory; no profile
or default changed. The first setup attempt is retained and excluded because a
static-cache screen inherited an incompatible `--adapt-accepted-only` flag;
the argument normalizer now removes that flag when it disables adaptive swaps.
Focused integration tests pass 12/12. Phase 6 remains open.

A seven-block held-out [Q2_0 int8-KV MTP3 confirmation](../../bench/results/2026-10-14-phase6-q2-int8-mtp3-retrieval-confirm7/README.md)
then compared MTP3 with MTP-off on a distinct 512-token retrieval-plus-arithmetic
task. All 14 measured replies exactly returned the three expected markers and
suffix sum `1768`; MTP3 offered/accepted 34/29 drafts in each block. Decode
throughput rose 8.83% (paired 95% interval +7.34% to +10.63%), client total
request time fell 2.82% (−4.68% to −1.23%), and TTFT was unresolved. Minimum
host/admission availability was 16.911/6.211 GiB with zero sampled cgroup
pressure or OOM events. This confirms the tested int8/MTP3 profile on one
held-out task only; energy was not request-attributed, and defaults remain
unchanged. Phase 6 remains open for broader workload and interaction evidence.

A second [seven-block Q2_0 int8-KV MTP3 confirmation](../../bench/results/2026-10-14-phase6-q2-int8-mtp3-8k-confirm7/README.md)
tested a distinct 7,501-token retrieval prompt. All 14 fresh-service requests
returned the three new keys exactly, all seven paired response strings
matched, and MTP3 accepted 23 of 28 drafts per request. MTP3 reduced median
prompt throughput 9.53% (paired 95% interval −12.84% to −6.93%) and decode
throughput 4.24% (−8.45% to −0.09%); client TTFT rose 10.51% and total request
time rose 10.20%, with all seven pairs slower end-to-end. Minimum
host/admission availability was 16.90/10.19 GiB and sampled cgroup pressure/
OOM counters stayed zero. One candidate-first block had a 93.64% latency
penalty and remains included; the other six pairs were 6.62–13.89% slower.
One-second request-window integrations of three named tegrastats rails also
estimated higher candidate energy per output token (2.76% on `VDD_GPU_SOC`,
7.74% on `VIN_SYS_5V0`, and 15.50% on `VDD_CPU_CV`). These include board
idle/background load, are not process-attributed, and are retained as
rail-specific diagnostics rather than whole-board energy claims.
This does not support an int8/MTP3 serving win for this long-prefill workload;
Phase 6 remains open for other interactions and workloads.

These two seven-block int8-KV confirmations are not a valid combined MTP-by-
workload interaction estimate: their recorded binary SHA256 values differ
(`5a72dbad…` for the 512-token campaign and `e84dc9af…` for the 7,501-token
campaign). Treat each paired result within its own campaign only. A direct
interaction follow-up must use one pinned binary/artifact set and randomize both
MTP arms within blocks at each workload length; Phase 6 remains open for that
same-source comparison.

The current-source [Q2_0 accepted-prefix runtime check](../../bench/results/2026-10-14-phase5-current-source-runtime/README.md)
reran MTP off/2/3/4 on the 2,048-token FP16-KV prompt after the accepted-window
cap change. All token IDs and nine persistent main-state fields matched at
final state and every shared prefix boundary (22/19/15 for MTP2/3/4). Minimum
host/admission availability was 16.88/8.38 GiB under the 28-GiB scope, with
zero sampled cgroup pressure/OOM events. This confirms only the tested prompt,
cache, format and adaptation policy; it has no performance implication.

A follow-up [current-source near-limit state check](../../bench/results/2026-10-14-phase5-current-source-long-runtime/README.md)
compared MTP off/window4 on a 7,498-token synthetic prompt at 8,192 context.
The 32-token outputs and all nine persistent fields matched at final state and
14 shared accepted-prefix boundaries; MTP4 accepted 18/30 drafts. Minimum
host/admission availability was 16.98/13.80 GiB, with zero sampled cgroup
pressure/OOM events. This is long-prefill state evidence, not a retrieval or
performance result.

The post-change [current-source Phase 8 regression](../../bench/results/2026-10-14-phase8-current-source-b99b26a2/README.md)
rebuilt the CUDA/ARM64 tree and passed all 117 fixture-available CTests; two
optional IQ checks skipped and the two known missing-`experts.bin` tests remain
excluded. Host/admission availability stayed at or above 22.27 GiB with zero
scope pressure/OOM events. Integration Python discovery passed 141/141.
maestro1 compiled and linked the changed HIP service
and parity target, and its CLI check passed; the existing SYCL service build
needed no recompilation, so that is not evidence for its separate generator
source path. Native model tests and HIP/SYCL device execution remain open.

The current-source [cadence-4 short/long/short diagnostic](../../bench/results/2026-10-14-phase5-current-source-swap-recovery/README.md)
still changed 14 of 16 recovery tokens and persistent state under both MTP-off
and MTP4, after nine adaptive swap updates per service. A paired same-binary
[delayed-swap control](../../bench/results/2026-10-14-phase5-current-source-swap-recovery-delayed/README.md)
logged no updates and restored exact short-output and state equality. This
confirms the observed swap-associated recovery sensitivity survives the new
accepted-window code; the numerical cause and quality impact remain unresolved,
so adaptive swapping remains unqualified for this sequence.

First-window logits captured on that same diagnostic sequence were bit-identical
between MTP-off and MTP4 for each request, but the first and recovery short
prompt logits differed before decoding: top-1 changed, relative L2 was 9.707%,
and 9/10 top tokens overlapped. This narrows the swap-associated effect to
prefill/verifier computation and excludes an MTP-only source; individual layer
or expert attribution remains open. See the
[first-logit analysis](../../bench/results/2026-10-14-phase5-current-source-swap-recovery-logits/README.md).

A source-based comparison of CPU Q8_K and CUDA Q8_1 activation images on the
seven captured route-flip vectors found a median 1.15% mutual relative L1 after
dequantization, with 2,271–2,461 of 2,560 values differing per vector. This
supports the activation-format seam as one plausible contributor to the
isolated expert output mismatch, but does not distinguish it from dot-product
arithmetic or prove the persistent-state recovery cause. The
[quantizer diagnostic](../../bench/results/2026-10-14-phase5-current-source-route-change-capture/activation-quantizers.md)
records the method and limits. Phase 5 remains open.

A follow-up [shared-weight activation-error decomposition](../../bench/results/2026-10-15-phase5-activation-error-decomposition/README.md)
ran the six observed layer-0 route-flip experts on the first captured input.
The CBLAS FP32 expert oracle used GGML-dequantized weights and independently
reconstructed CPU Q8_K/Q8_0 and GPU Q8_1/Q8_1 activations. The median measured
CPU/GPU output difference was 1.57402%; the quantizer-only oracle produced
1.57424%. The median residual vector was 0.40533% of the measured difference,
and actual CPU/GPU outputs stayed within 0.000014%/0.083511% of their
respective quantizer oracles at worst. Across seven captured inputs, the 42
quantizer-only pairs had 1.50755% median relative L1. This strongly attributes
the sampled layer-0 operator gap to activation-format differences; it does not
establish the full service-level persistent-state drift cause. Phase 5 remains
open.

A direct FP32 GDN-state follow-up found that cadence-4 swaps changed GDN values
at accepted-prefix L=527 in the short-only request (relative L2 0.0462) while
preserving output IDs. In that capture, GDN slices 0 and 1 were bitwise equal
to the control and slice 2 was the first to differ. Strata compacts GDN rows
over non-QSA model layers (`qsa_interval=4`), so slice 2 maps to transformer
block 2, matching the earlier route trace's first activation divergence. The
first owner changes were at block 1; this localizes propagation without
establishing the arithmetic cause.
After a long request, delayed adaptation reproduced the initial state
bit-for-bit; active adaptation changed 29,414,608 of 29,417,472 floats
(relative L2 0.7376) and all 16 output IDs. This is one diagnostic run per arm:
it quantifies the state drift on this path, but does not identify an internal
cause or close Phase 5. See the
[numeric capture report](../../bench/results/2026-10-16-phase5-coder-q8_1-adaptive-swap-screen/gdn-state/README.md).

The [current-source Coder IQ1_M path check](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m/README.md)
used the `IQ1_M` variant from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`,
pinned by the local Hugging Face snapshot at revision
`5348543e0147355ac9cbcb031184a3546350988e`. Its two shard hashes exactly match
the Coder IQ1_M shards used in previous service tests; this is a current-source
path check, not a comparison between quantizations or inference engines. The existing pack's
48-layer/256-expert mapping and source sidecar matched; six sampled expert
blobs were byte-identical. On the current candidate, the 7,498-token 8K
planted-marker request returned all three codes once and in order, followed by
same-service `RECOVERED`; MTP accepted 30/32 drafts. Minimum host and admission
availability was 13.25 GiB under the 28-GiB supervisor, with zero cgroup
pressure/OOM events. This validates the downloaded directory path for an
already-tested artifact identity; it is not a new model cohort or a Phase 7
closeout.

The follow-up [current-source 16K Coder IQ1_M check](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m-16k/README.md)
used the same exact shard hashes and profile at 16,384 configured context. Its
15,003-token uncached retrieval returned all three markers once and in order;
same-service recovery passed, with MTP accepting 30/32 drafts. Minimum
host/admission availability was 12.76 GiB across 673 samples, with no cgroup
pressure or OOM events. This adds one current-source 16K cell; broader quality,
independent repetitions and Phase 7's other open gates remain.

The [current-source 32K Coder IQ1_M check](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m-32k/README.md)
completed the same retrieval/recovery task at 32,768 context with 30,032
uncached prompt tokens. All three markers were exact and ordered, recovery
passed, and MTP accepted 30/32 drafts. Minimum host/admission availability was
12.60 GiB across 1,266 samples, with zero cgroup pressure/OOM events. Together
these current-binary runs cover 8K/16K/32K retrieval cells for the already
tested Coder artifact identity; broad quality, thermal soak and independent
repetitions remain open, so Phase 7 stays in progress.

The [current-source Coder IQ1_M near-limit 128K check](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m-128k/README.md)
used the same pinned shard hashes and candidate binary with 131,072 configured
context. Its exact 120,149-token prompt returned all three planted markers
once and in order, then the same service returned `RECOVERED`; MTP accepted
28/33 drafts. Minimum host/admission availability was 10.20 GiB across 5,837
samples, with zero cgroup pressure/OOM events. An earlier attempt was
interrupted by supervisor signal 15 near the end of prefill and is excluded;
the independent retry passed. This remains one functional point, not a
quantization or engine comparison, and Phase 7 remains open.

The [current-source 40-minute sustained Coder service check](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m-soak/README.md)
used the same binary, profile and exact shard hashes. After a cold 7,498-token
retrieval precondition, all 1,586 streamed cache-reuse responses contained
each planted marker exactly once; none failed, and all reused 7,491 prompt
tokens. The 2,400-second loop had 13.30 GiB minimum host/admission availability
and zero cgroup pressure/OOM events. `tj` stayed between 71.1 and 73.3 °C from
14:40 through 15:11. This refreshes sustained
service evidence for the tested profile; concurrency, broader quality and
other model/configuration cells remain open.

A current-source [Coder IQ1_M image-grounding check](../../bench/results/2026-10-17-phase7-current-source-coder-iq1m-vision-count/README.md)
repeated an exact quadrant-circle count on a synthetic 224×224 image in three
fresh services. All three responses returned the independently pixel-oracle
answer exactly; each API returned HTTP 200, stopped naturally and shut down
cleanly. The CUDA encoder used 16 image tokens. Minimum host/admission
availability was 11.76 GiB, with zero cgroup pressure/OOM events. This is one
bounded visual-counting task, not broad vision quality or high-resolution
support. Phase 7 remains open.

A three-block [Coder IQ1_M MTP × KV × prompt-length screen](../../bench/results/2026-10-16-phase6-coder-mtp-kv-workload-screen/README.md)
crossed MTP off/MTP4, FP16/INT8 KV and 512/7,501-token retrieval prompts.
All 24 arms passed the exact answer oracle and six-GiB guard. Four of 12 MTP
pairs had different actual expert residency and were excluded from timing
effects. The remaining per-cell decode effects are descriptive with only one
to three paired blocks; no block had all eight factorial arms at identical
residency, and only two long-prompt MTP × KV interaction blocks qualified.
Minimum host/admission availability was 13.33/8.94 GiB across 4,887 samples,
with zero cgroup pressure/OOM events; clocks were dynamic and energy was not
request-attributed. This screen does not select or promote a profile. Its
1,500 MiB residency-matched repeat and follow-up below restore three fully
qualified screening blocks; seven-block held-out confirmation and other Phase
6 interactions remain necessary.

The randomized three-block [Coder IQ1_M cache-bounded MTP × KV × prompt-length
screen](../../bench/results/2026-10-16-phase6-coder-mtp-kv-workload-screen-cache1500/README.md)
used a 1,500 MiB expert-cache budget. All 24 answers passed; 10/12 MTP pairs
qualified by same-day and exact-residency rules, with two exclusions. The
randomized one-block [follow-up](../../bench/results/2026-10-17-phase6-coder-mtp-kv-followup-budget1500/README.md)
then passed all eight arms with the same 1,934 slots / 3,807 MiB and produced
four same-day qualified pairs. The combined audit retains original blocks 0
and 2 plus the follow-up block; all 12 cell pairs and all three full factorial
blocks qualify. Median MTP4 decode changes were +11.91%/+4.34% for FP16
short/near-limit and +14.02%/+6.90% for INT8. Client total-time changes were
−2.04%, −0.09%, −1.18% and +0.35%, respectively. Three-way interaction values
varied across blocks; these remain screening estimates, not held-out
confirmation or a profile recommendation. Follow-up minimum host/admission
availability was 17.08/7.79 GiB across 1,709 samples, with zero cgroup
pressure/OOM events. The initial post-collection summary hit a one-block
bootstrap serialization bug; the raw arms passed, the summary was regenerated
after fixing and testing the analysis path, and no arms were rerun. Phase 6
remains open.

A seven-block [held-out Coder IQ1_M MTP × KV confirmation](../../bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-confirm7-cache1500/README.md)
then crossed MTP off/MTP4 and FP16/INT8 KV on the retrieval-plus-arithmetic
512-token task at the same 1,500 MiB cache budget. All 28 arms returned the
exact answer; all 14 MTP pairs qualified at 1,934 slots / 3,807 MiB, and all
seven blocks ran on Oct 17. MTP4 decode-throughput effects were +0.59% FP16
(paired 95% interval +0.15% to +2.39%) and +1.47% INT8 (+0.87% to +2.70%).
Client total-time intervals included zero for both formats. The held-out MTP ×
KV decode and client-time interaction intervals also included zero. Minimum
host/admission availability was 17.09/6.14 GiB across 1,984 samples, with no
cgroup pressure/OOM events; admission headroom came within 0.14 GiB of the
required floor. This confirms only this one task, cache cap, model quantization
and MTP/KV interaction; no profile changed, and Phase 6 remains open for its
other supported interactions and configurations.

A current-source [seven-block replication](../../bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-confirm7/README.md)
repeated that short-prompt 2×2 MTP × KV screen on Oct 20 with the current
candidate binary. All 28 arms returned the exact answer and all seven pairs
per KV format qualified at 1,934 expert slots / 3,807 MiB. For FP16 KV, MTP4
paired decode throughput was 3.15% lower (95% interval −4.14% to −0.86%),
while client total time was 3.83% higher (+0.58% to +5.49%). For INT8 KV,
decode throughput changed −0.17% (−9.86% to +1.68%) and client total time
+0.12% (−0.75% to +4.37%); two opposing decode outliers make that estimate
imprecise. Minimum host/admission availability was 16.70/15.62 GiB across
1,977 samples, with zero cgroup pressure/OOM events. This is a same-task
replication rather than a new held-out workload. It does not justify
promoting MTP4 or change the profile; Phase 6 remains open.

The current-source campaign's 28 tegrastats streams were subsequently integrated
over their paired API request windows. Median `VIN_SYS_5V0` energy per 45-token
answer was 4.697/4.665 J for FP16 MTP-off/MTP4 and 4.708/4.608 J for INT8;
paired MTP4 effects were −0.05% (95% interval −2.55% to +1.23%) and −2.20%
(−3.05% to +1.28%), respectively. The MTP × KV interaction interval also
included zero. These are separate board-rail estimates including idle and
background activity, not process-attributed energy; the other named rails and
per-arm results are in the linked report. This adds a bounded energy dimension
to the same-task replication without promoting MTP4 or a KV format.

A seven-block held-out [Coder IQ1_M MTP × KV × prompt-length confirmation](../../bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-workload-confirm7-cache1500/README.md)
extended that task to the 7,501-token retrieval-plus-arithmetic prompt, crossing
short/long workload with FP16/INT8 KV and MTP off/MTP4. All 56 measured arms
returned exact answers, with seven qualified paired blocks per cell at 1,934
resident expert slots / 3,807 MiB. Long-prompt MTP4 decode throughput was
10.16% lower with FP16 KV (paired 95% interval −11.76% to −8.07%) and 7.95%
lower with INT8 KV (−9.70% to −7.46%); short-prompt decode effects were small
(+0.20% FP16 and +1.77% INT8). The three-way interaction intervals include
zero. One pressure-aborted attempt reached 5.71 GiB effective admission while
host availability remained above 22 GiB; its isolated retry passed. Passing
arms stayed above 6.279 GiB effective admission and cgroup pressure/OOM counts
were zero. This is workload-specific evidence for the same Coder IQ1_M artifact,
not a quantization or engine comparison; no profile changed. Phase 6 remains
open for other supported interactions, Pareto/energy work and remaining
configuration domains.

Follow-up integration of the retained tegrastats samples brackets all 56
passing API request windows. `VIN_SYS_5V0` energy per 45 output tokens changed
with MTP4 by −0.95% (paired 95% interval −2.03% to +0.18%) at short FP16,
−1.47% (−4.36% to +0.86%) at short INT8, +0.67% (+0.45% to +0.94%) at long
FP16 and +0.85% (−0.01% to +1.53%) at long INT8. Separate CPU/GPU rail values
and all paired rows are retained in the report. These request-window rail
integrals include board idle/background activity and are not process-attributed
or summed into whole-device energy; they remain supporting diagnostics rather
than a standalone Pareto energy measure.

A cell-scoped [latency / input-rail plot](../../bench/results/2026-10-17-phase6-coder-mtp-kv-heldout-workload-confirm7-cache1500/pareto-latency-energy.png)
uses the same seven-block medians, with decode rate and minimum admission as
annotations and exact-answer success as a feasibility constraint. Within the
identical workload/KV cells, MTP off dominates MTP4 on both long-prompt
latency and input-rail energy; MTP4 dominates on short INT8; short FP16 retains
a latency/rail tradeoff. This is scoped diagnostic evidence because the rail
includes board idle/background activity, not a process-energy Pareto frontier
or a cross-workload ranking. No profile is selected.

A current-source seven-block [Q2_0 prefill-chunk confirmation](../../bench/results/2026-10-17-phase6-q2-prefill-long-workload-current-source/README.md)
repeated the held-out 7,501-token retrieval workload with prefill chunks 32
and 128 at exactly 3,000 resident expert slots. All 14 fresh-service requests
returned the exact 36-token retrieval answer. Chunk 128 reduced median request
time 59.71% (paired 95% interval −59.82% to −59.52%) and raised median prompt
rate 151.33%; all seven pairs favored it. Minimum host/effective admission
availability was 18.07/11.39 GiB, above the six-GiB floor, with no cgroup
pressure or OOM events. Complete request-window rail estimates also favored
chunk 128 on the three separate named rails; they include board idle/background
activity and are not process-attributed or summed. The initial shared-scope
attempt and two conservative pressure aborts are retained but excluded; the
isolated per-cell retry completed all blocks. This confirms the result for
this Q2_0 long-prompt task and runtime profile only. No default changed, and
Phase 6 remains open.

A same-day [current-source Q2_0 cache × prefill confirmation](../../bench/results/2026-10-17-phase6-q2-prefill-cache-current-source/README.md)
crossed exact 3,000/3,500 expert slots with chunks 32/128 in seven randomized
blocks on the 512-token held-out retrieval task. All 28 measured responses
matched the exact 47-token answer and all services admitted their requested
cache capacity. Chunk 128 reduced median request time 45.85% at 3,000 slots
(paired 95% interval −47.07% to −45.08%) and 45.38% at 3,500 slots
(−47.98% to −43.68%). The cache × chunk interaction interval includes zero;
the cache-size effect at chunk128 also includes zero. One 3,500-slot/chunk32
cell took 70.25 seconds while its in-request median GPU clock was 612 MHz; the
exact-answer cell remains included and no causal claim is made. Minimum
host/effective admission availability was 17.38/13.49 GiB with zero cgroup
pressure/OOM events. The separate `VIN_SYS_5V0` request-window integral fell
44.23% at chunk128 with 3,000 slots (six complete pairs) and 44.29% at 3,500
slots (seven pairs); one window is unsupported due to a telemetry gap. These
estimates include board idle/background activity and are not process-attributed.
No profile changed; Phase 6 remains open.

A current-source seven-block [Q2_0 graph × MTP2 confirmation](../../bench/results/2026-10-17-phase6-q2-graph-mtp-current-source/README.md)
repeated captured/eager CUDA graph × MTP-off/window2 on the task-quality-
validated 2,094-token processor explanation. All 28 responses stopped at 293
tokens, passed the rubric and were byte-identical; MTP2 offered/accepted 153/97
drafts per request. Captured versus eager request-time effects included zero
for both MTP settings. MTP2 raised request time 5.46% captured (paired 95%
interval +4.46% to +7.07%) and 3.39% eager (+2.17% to +5.54%), with decode
throughput down 6.10% and 3.75%, respectively. One captured/MTP2 cell had a
95.80-second request and remains included. Minimum host/admission availability
was 16.95/11.58 GiB with zero cgroup pressure/OOM events. All 28
`VIN_SYS_5V0` request windows were integrated; the values include board
idle/background activity and are not process-attributed. This Q2_0 variant
comes from the same pinned ISTA Coder-GGUF repository as the IQ1_M Coder tests,
but it is not an IQ1_M or cross-quantization comparison. No profile changed;
Phase 6 remains open.

A three-block [current-source Q2_0 long-retrieval cache × prefill screen](../../bench/results/2026-10-18-phase6-q2-cache-prefill-long-screen3/README.md)
crossed exact 3,000/3,500 expert slots with chunks 32/128 on a 7,501-token
retrieval prompt. All 12 fresh-service cells passed the exact answer and token
count checks. Chunk 128 reduced median request time 59.56% at 3,000 slots and
61.38% at 3,500. The screen's cache × chunk estimate was −2.93 percentage
points (three-block paired bootstrap interval −3.79 to −1.75); cache size was
uncertain at chunk 32 and nominally favored 3,500 at chunk 128. These three-block
intervals are exploratory, and no profile changed. Minimum host/admission
availability was 17.42/10.59 GiB; cgroup pressure/OOM events were zero. Dynamic
GPU clocks ranged 306 MHz–1,300.5 MHz; EMC readback was unsupported, and energy
was not request-attributed.

The separate [seven-block held-out Q2_0 long-retrieval confirmation](../../bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/README.md)
completed the same cache × prefill grid on a distinct 7,506-token prompt. All
28 fresh-service responses returned the exact expected answer; all supervisors,
exact-slot checks and memory guards passed. Chunk 128 reduced paired median
request time 59.54% at 3,000 slots (95% bootstrap interval −59.80% to −54.93%)
and 59.74% at 3,500 (−60.82% to −59.59%). The cache-size effect was small or
uncertain, and the cache × prefill interaction interval included zero. Minimum
host/admission availability was 17.47/11.45 GiB across 14,411 memory samples,
with zero cgroup events. Dynamic GPU clocks ranged 306 MHz–1,300.5 MHz; EMC
readback was unsupported, and energy was not analyzed. This confirms the strong
chunk effect for the tested held-out retrieval workload only; no profile changed
and Phase 6 remains open.

A second seven-block [Q2_0 cache × prefill confirmation](../../bench/results/2026-10-18-phase6-q2-cache-prefill-short-confirm7/README.md)
tested a fresh exact-512-token retrieval-plus-sum task, with all 28 measured
answers matching the three markers and independent suffix sum `1602`. Chunk
128 reduced median request time 46.79% at 3,000 slots (paired 95% interval
−47.86% to −45.90%) and 46.53% at 3,500 (−47.23% to −45.52%). The cache ×
prefill interaction interval included zero. A separate-block comparison with
the 7,506-token campaign found the near-limit prompt's chunk benefit larger by
12.75/13.21 percentage points for request time at 3,000/3,500 slots; prompt-
time differences were 8.25/8.71 points. All independent-block intervals
excluded zero, showing a workload interaction between these two tasks while
not isolating prompt length from their differing content/output. The short
campaign retained 17.39/9.33 GiB minimum host/admission availability over 3,002
samples with zero cgroup events. No profile changed; Phase 6 remains open.

The [Q8_1 verifier-window parity check](../../bench/results/2026-10-18-phase5-coder-q8-1-windows-ctest/README.md)
extends the synthetic IQ2_S/Q2_0 expert oracle across verifier widths 1–8.
CPU and CUDA results matched bitwise at every width, and CPU single-token
versus grouped gate/up/down rows had zero differences. The default operator,
existing Q8_1 dot, and new window CTests passed 3/3; the Python integration
suite passed 163/163. This narrows the tested operator contract but does not
resolve the service-level adaptive-residency state divergence or close Phase 5.
The changed shared files also passed current-source maestro1 HIP and SYCL
rebuilds from commit `58be4d54`; the HIP and SYCL service `--help` checks
passed. These are x86_64 compile/CLI checks only, with no accelerator runtime
qualification. See the [complete report](../../bench/results/2026-10-18-phase5-coder-q8-1-windows-ctest/README.md).

A six-case [Coder Q8_1 verifier-window check](../../bench/results/2026-10-19-phase5-coder-q8-1-real-windows/README.md)
used the pinned IQ1_M GGUF, actual IQ2_S/Q2_0 expert tensors and captured
service activations for routed layer 1 experts. Across widths 1–8, all 48
CPU/CUDA outputs were bitwise equal and all 48 width-invariance checks had
zero differing rows. The focused CTests passed, and the updated diagnostic
built for CUDA on Orin and HIP on maestro1. This confirms operator parity for
these cases only; it does not prove persistent state or end-to-end service
parity and does not resolve adaptive-residency divergence. Phase 5 remains
open.

The parity utility now accepts exact multi-row FP32 activations. A captured
short-request two-token layer-0 dispatch routed expert 70 to CPU for both rows;
replaying those distinct rows together reproduced zero CPU grouped-vs-single
row differences, while the actual IQ3_XXS/IQ4_NL CPU-vs-CUDA output relative L1
was 1.52%. The CPU Q8_1 experiment does not apply to this layer's tensor types,
so it is recorded as unsupported. This validates grouped-row behavior for one
captured expert/window but does not close the service-level state divergence or
Phase 5. See the updated [probe report](../../bench/results/2026-10-19-phase5-coder-q8-1-real-windows/README.md).

A device-side reanalysis corrected the earlier Phase 5 layer-1 capture
interpretation. The host JSONL route capture is stale for two all-GPU rows, but
the verifier's graph-side `ffn_x` is bitwise identical between CPU-mirror and
GPU-profile arms across all 16 decoded positions. Their combined layer-1 output
first differs at position 512, matches again at 513, then differs at 514–526.
Eight real-expert checks on exact device-captured inputs found Q8_1 CPU/CUDA
bitwise parity for all tested experts; the experts remaining CPU-owned in the
GPU-profile run instead use the default CPU activation path, which differs from
Q8_1 by 1.37–1.69% on the tested rows. This strongly supports activation-format
arithmetic as a cause of the observed row-level combined-output changes, while
full weighted-sum reconstruction and later persistent-state attribution remain
open. See the updated [Phase 5 report](../../bench/results/2026-10-19-phase5-coder-q8-1-real-windows/README.md).

A full 16-position [current-source route/output capture](../../bench/results/2026-10-18-phase5-coder-layer1-route-isolation/README.md#all-16-generated-positions--2026-10-19)
now records all 48 layers and every layer-1 CPU-owned output. Device-side
`ffn_x` stayed bitwise identical across the three arms for all 16 rows. Default
and Q8_1 mirror input rows also match bitwise; all 98 CPU expert output vectors
differ (median relative L1 1.372%, range 0.485%–1.757%). The 83 CPU outputs
still owned by CPU in both default and GPU-profile runs match bitwise. Combined
`ffn_y` differs between default and mirror at all positions; mirror and
GPU-profile agree only at 511 and 513, where the GPU profile moves every CPU
owner. This strengthens the activation-format attribution but does not
reconstruct the full weighted sum or resolve the distinct persistent-state
fingerprints after the request. All arms passed 28-GiB supervision with zero
cgroup memory events and at least 14.14 GiB host/admission availability. Phase
5 remains open. The changed final fingerprints are `gdn`, `kv`, `pooled`,
`pooled_full` and `tail`; PLE fingerprints match.

The [accepted-prefix join](../../bench/results/2026-10-18-phase5-coder-layer1-route-isolation/all-16-positions-three-arm-wildcard/prefix-state-alignment.json)
aligns all 16 committed-prefix GDN hashes with the 48-layer route trace. For
both default-versus-mirror and mirror-versus-GPU-profile pairs, the first GDN
slice that differs maps to the same model layer as the first valid host route
activation difference at every position. This is layer 2 for all default/
mirror positions; for mirror/GPU it is layer 9 at position 511 and layer 2 at
positions 512–526. All 36 prefill GDN checksums match per pair, but they are
16-bit checks and do not establish exact prefill state equality. This narrows
the first observed state divergence but does not prove the full causal path or
close Phase 5.

A follow-up [exact prompt-end GDN comparison](../../bench/results/2026-10-18-phase5-coder-layer1-route-isolation/prefill-gdn-exact-three-arm-checked/README.md)
dumped and compared all 117,669,888 GDN payload bytes per arm before decode.
Default CPU, Q8_1 mirror, and GPU-profile payloads were byte-identical across
all 36 state slices; the same prompt produced the same 16 completion IDs. The
first post-commit GDN differences therefore begin during decode in this
workload. This does not prove exact equality for prompt-end KV or other state,
identify the responsible decode calculation, or close Phase 5.

A focused [device-side layer-9 pair](../../bench/results/2026-10-18-phase5-coder-layer1-route-isolation/layer9-device-pair/README.md)
for mirror CPU versus GPU profile confirms the all-layer host route activation
matches verifier `ffn_x` bitwise on all 16 rows. At position 511, layer-9 device
`ffn_x` and `ffn_y` differ even though expert IDs and owners still match; this
validates the first GDN divergence layer for that token and places its change
in the activation values before layer-9 routing. It does not localize the
earlier decode operation that changed those values or close Phase 5.

A [per-QSA accepted-prefix fingerprint campaign](../../bench/results/2026-10-18-phase5-coder-layer1-route-isolation/qsa-state-three-arm/README.md)
now shows the first differing persistent QSA hash at model layer 3 for all 16
default-CPU versus Q8_1-mirror positions, following the first differing route
activation at layer 2. For mirror versus GPU placement, the first position
shows QSA layer 11 after route activation layer 9; the remaining positions show
QSA layer 3 after route activation layer 2. These are 64-bit fingerprints,
which localize changes but do not prove state identity or causality.

A focused [layer-8 same-input CPU arithmetic comparison](../../bench/results/2026-10-18-phase5-coder-layer1-route-isolation/layer8-output-pair/README.md)
found identical device inputs, routes and owners at position 511/token 271,
while all seven CPU expert outputs and all 2,560 combined device output values
differed between default arithmetic and Q8_1. An independent native expert
oracle confirmed service-to-tool output identity in each arithmetic mode and
bitwise Q8_1 CPU/CUDA agreement for all seven IQ2_S/Q2_0 experts. This is
single-row operator evidence and does not resolve full weighted combination,
quality impact or the persistent-state continuation divergence. Phase 5
remains open.

A final-source [layer-8 weighted output reconstruction](../../bench/results/2026-10-18-phase5-coder-layer1-route-isolation/layer8-weighted-output-pair-final/README.md)
now captures exact verifier device router weights as well as the layer input,
routes, CPU expert rows and combined output. At position 511/token 271, the
Q8_1-mirror and default-CPU paths have identical device inputs, top-10 IDs,
router weights and expert owners. The weighted sum of seven CPU expert-output
deltas reconstructs the combined device-output delta across all 2,560 values;
relative-L1 residual is `2.266e-5`, with maximum absolute residual `5.63e-9`.
Both arms retained at least 14.38 GiB host/admission availability and had zero
observed cgroup memory events. This closes the numeric weighted-combine
attribution for one row, but does not prove answer-quality impact or resolve
persistent-state continuation divergence. The opt-in verifier route capture
built and passed focused CUDA tests 6/6; the full HIP service also compiled
and linked on maestro1, and its `--help` check passed. maestro1 is build/CLI
evidence only. No performance claim follows and Phase 5 remains open.

A fixed-residency [layer-1 weighted-output reconstruction](../../bench/results/2026-10-19-phase5-coder-layer1-weighted-output-pair/README.md)
now checks the first implicated MoE boundary. At position 511/token 271,
default CPU and Q8_1 mirror had bitwise-identical device inputs, expert IDs,
router weights and owners. All seven CPU expert outputs changed; their weighted
delta reconstructs the combined layer-1 output delta with relative-L1 residual
`1.952e-5`. A same-prompt layer-2 capture found its device input already
different in all 2,560 values and all ten router weights changed, so the
layer-2 weighted analyzer rejected that cell's same-input precondition. This
directly attributes the layer-1 combined-output change to CPU arithmetic and
confirms a downstream activation change, but does not prove the complete
persistent-state or quality consequence. Both pairs passed 28-GiB supervision
with zero observed memory events and at least 14.37 GiB host/admission
availability. Adaptive migration remains unqualified and Phase 5 remains
open.

The exact shared source at `c5f9f319`, including the Q8_1 format-pair
selector, also completed fresh maestro1 HIP and SYCL compile/link builds. Both
`strata --help` checks exited 0, and SYCL completed 123/123 build steps. The
scope was capped at 1.5 GiB; `memory.events` recorded 171 `max` events and no
OOM/kill events. These are x86 build and CLI checks only, not accelerator
execution or Orin performance results. See the [backend report](../../bench/results/2026-10-19-phase5-coder-layer0-iq3xxs-only-service/backend/maestro1/README.md).

A new [layer-1-only Q8_1 service diagnostic](../../bench/results/2026-10-19-phase5-coder-layer1-q8_1-mirror/README.md)
scoped the CPU arithmetic route to IQ2_S/Q2_0 experts at zero-based layer 1
of the pinned Coder IQ1_M artifact. All four supervised arms passed, and all
64 accepted-prefix fingerprints per arm were compared directly. The layer-
scoped mirror changed persistent state from commit 1 in every request; adaptive
recovery changed 10/16 token IDs, while fixed-residency recovery token IDs
matched despite state differences. Minimum host/admission availability was
14.26/14.26 GiB, with zero cgroup pressure/OOM events. This isolates a sufficient
layer-local arithmetic perturbation for the tested sequence; it does not
establish answer quality or qualify adaptive migration. Phase 5 remains open.

The layer-1-only selector source also completed maestro1 HIP and SYCL
compile/link builds from the pinned source plus the recorded four-file overlay.
Both CLI checks exited 0; the 1.5-GiB build scope recorded zero memory limit or
OOM events. This remains x86 build evidence only, with no accelerator execution.
See the [backend report](../../bench/results/2026-10-19-phase5-coder-layer1-q8_1-mirror/backend/maestro1/README.md).

A three-block [layer-1 CPU/GPU owner-equivalence check](../../bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/README.md)
held the layer-1 Q8_1 selector constant while a matched 3,007-slot profile
moved seven IQ2_S/Q2_0 experts from CPU to CUDA. All three 512→16 pairs matched
all token IDs and 16 accepted-prefix state fingerprints; prompt-end GDN dumps
were byte-identical. A supplemental device-side route capture confirmed that
layer-1 expert IDs and router weights matched at all 16 output positions, and
the changed owner assignments were confined to the seven targets. Minimum
host/admission availability was 16.009 GiB, with zero cgroup events. No
speculative drafts were accepted, no performance or quality claim follows, and
this does not qualify other layers, formats or adaptive migration. Phase 5
remains open.

A three-block [layer-2 IQ2_S/IQ4_NL owner-placement check](../../bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/README.md)
recorded a layer-2 state and output divergence for the original standalone
four-warp IQ4_NL CPU mapping. The grouped service mapping was subsequently
corrected and validated at the operator level; a current-source three-block
follow-up now captures every routed expert row and combined `ffn_y`, finding
bitwise equality across all 16 positions, accepted-prefix state and completion
IDs in every fixed-residency owner pair. See the [grouped-map report](../../bench/results/2026-10-19-phase5-coder-layer2-hidden-q8_1/README.md)
and the [service expert-row capture](../../bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/service-parts-confirm3/README.md).
The initial counterexample remains in the historical report and is superseded
for this corrected layer-2 selector. Neither result qualifies adaptive
migration, other layers/formats, quality or performance. Phase 5 remains open.

A current-source, serial [full CUDA/CPU CTest run](../../bench/results/2026-10-19-phase5-current-source-full-ctest/README.md)
completed 124/128 tests successfully. `iq_parity_fixtures` and `iq_parity`
were explicitly skipped because their fixture is absent. `expert_parity` and
`pool_test` failed because the legacy `pack/full/experts.bin` input is absent;
that pack format is incompatible with the available Coder pack, and the former
also requires AVX-512 not present on Orin. The focused accepted-window/usage,
GDN, speculative-sampling, verifier-batch, KV, PLE, graph-lifecycle and native
expert/Q8_1 tests all passed. The supervised run retained at least 20.70 GiB
host/admission availability with zero observed cgroup pressure/OOM events.
This records current-source regression coverage and explicit unsupported
legacy test cells. The layer-2 persistent-state counterexample is superseded by
the corrected grouped-map follow-up; Phase 5 remains open for its other gates.


A current-source [adaptive migration pair with matched Q8_1 CPU arithmetic](../../bench/results/2026-10-19-phase5-coder-q8_1-adaptive-matched-pair/README.md) used `STRATA_NATIVE_CPU_Q8_1_DOT=all` in both cadence-100,000 delayed and cadence-4/cap-8 adaptive services, then compared 64 accepted-prefix state records per arm across a 512→2,048→512→continuation sequence. Both services passed supervision at 28 GiB with at least 14.24 GiB host/admission availability and zero cgroup events; the adaptive arm passed 15 swap-byte and 15 residency checks. Despite matched Q8_1 arithmetic, adaptive recovery differed at all 16 state boundaries and 10/16 token IDs; delayed-control recovery matched all state and token IDs. The continuation had equal token IDs but differed at all 16 state boundaries, reaffirming direct state checks. At layer 1, the first seven activation/ID rows matched between initial and recovery prompts while 27 adaptive owner assignments flipped; nine later activation rows then differed. This rejects the tested selector as a migration-parity remedy, but does not prove exclusive causality because unsupported format pairs retain their default path. Phase 5 remains open.

A current-source [long-prompt Coder IQ1_M MTP accepted-prefix matrix with FP16 KV](../../bench/results/2026-10-20-phase5-coder-current-source-mtp-prefix-long-fp16/README.md) crossed MTP off/windows 2/3/4 on a 7,498-token prompt and 16-token continuation. All token IDs and nine persistent main-state fingerprints matched at completion and every 11/9/8 shared accepted-commit boundaries; windows 2/3/4 accepted 5/7, 7/10 and 8/13 drafts offered. The 28-GiB supervisor passed with 13.04 GiB minimum host availability, 11.34 GiB admission availability and zero cgroup high/max/OOM events. Current integration Python tests passed 163/163 and focused accepted-window/GDN/KV/graph CTests passed 11/11. Sequential one-shot timings are descriptive, not a performance estimate. This adds one long-prompt FP16 correctness cell; Phase 5 remains open.

The four tested current-source Coder MTP accepted-prefix cells now span 2,048- and 7,498-token prompts with FP16 and int8 KV. MTP-off/windows 2/3/4 matched token IDs and all nine main-model state fields at final completion and shared commit boundaries in each cell; the short cells are documented in the [FP16](../../bench/results/2026-10-19-phase5-coder-current-source-mtp-prefix/README.md) and [int8](../../bench/results/2026-10-19-phase5-coder-current-source-mtp-prefix-int8/README.md) reports, and the long cells are linked below. This closes that bounded correctness matrix only, not the remaining Phase 5 gates or its separate adaptive migration issue.

A current-source [Coder MTP4 decode-cancellation check](../../bench/results/2026-10-20-phase5-coder-current-source-mtp-decode-cancel/README.md) canceled after eight streamed deltas and 12 committed tokens. Three fresh exact-length references matched the token IDs and all 11 persistent-state fields at accepted lengths 48, 51, 55 and 59; same-service recovery returned `Hello Orin!`. The supervised run passed with 13.26 GiB minimum host availability, 12.00 GiB admission availability and zero cgroup events. The focused cancellation harness tests passed 9/9 and integration Python discovery passed 163/163. This adds one current-binary decode-cancellation point; other boundaries and adaptive migration qualification remain open.

A current-source [early-prefill cancellation and recovery check](../../bench/results/2026-10-20-phase5-coder-current-source-mtp-prefill-cancel/README.md) closed the 7,498-token Coder IQ1_M stream after 64 prompt tokens had been read and before any output token was generated. Same-service recovery returned `Hello Orin!`; all 11 persistent-state fingerprints matched a fresh-service reference, including MTP state. The 28-GiB supervisor passed with 13.05 GiB minimum host/admission availability, 13.34 GiB peak scope use, and zero cgroup events. This adds one early-prefill cancellation point for the tested FP16/MTP4 profile; it does not resolve the separate adaptive-migration drift or qualify other boundaries.

The matched [int8-KV long-prompt matrix](../../bench/results/2026-10-20-phase5-coder-current-source-mtp-prefix-long-int8/README.md) used the same prompt-token digest and crossed MTP off/windows 2/3/4 at the same 7,498-token length. All token IDs and nine persistent state fields matched at completion and every shared 11/9/8 commit boundary; MTP2/3/4 accepted 5/7, 7/8 and 8/11 drafts offered. Supervision passed with 13.29 GiB minimum host availability, 12.00 GiB admission availability and zero cgroup events. The sequential one-shot measurements are not performance evidence. Together with the FP16 run, this closes the two-KV-format long-prompt accepted-prefix correctness cell for this prompt only; broader Phase 5 gates remain open.

A current-source [Coder IQ1_M MTP accepted-prefix check with int8 KV](../../bench/results/2026-10-19-phase5-coder-current-source-mtp-prefix-int8/README.md) compared MTP off/2/3/4 on the same 2,048-token prompt, with 16 generated tokens per fresh service. Windows 2/3/4 offered and accepted 7/5, 10/7 and 13/8 drafts; all token IDs and all nine persistent-state fingerprints matched MTP-off at the final state and each of 11/9/8 shared commit boundaries. The 28-GiB supervised run took 396.8 seconds; minimum host/admission availability was 13.18/10.10 GiB over 376 samples, and all cgroup memory-event counters were zero. This extends current-source accepted-prefix evidence to int8 KV for one prompt/profile; it does not qualify other formats, quality, performance, or adaptive migration. Phase 5 remains open.

A paired [pinned-control API rollback run](../../bench/results/2026-10-19-phase8-current-source-api-rollback/README.md) used the same Coder IQ1_M artifacts and compatible 8K configuration on the pinned control and current candidate, changing only the executable and per-run logs. Both passed the seven real-model protocol cases: repeated exact responses, OpenAI and Anthropic streaming, decode cancellation and prefill disconnect, each followed by same-service exact recovery. Minimum host/admission availability was 14.18 GiB for control and 14.28 GiB for candidate, with zero cgroup events. The short prefill disconnect did not retain prompt-progress evidence, so this does not validate active-prefill cancellation. The broader Phase 5/6 gates and Phase 8 release work remain open.

A current-source [Coder IQ1_M MTP4 long-prefill cancellation check](../../bench/results/2026-10-19-phase5-coder-current-source-prefill-cancel/README.md) closed the stream after 30 seconds, when the engine had read 512/7,501 prompt tokens and generated none. Same-service recovery returned `Hello Orin!`; all 11 persistent-state fingerprints matched a fresh-service reference at `L=24`. The 28-GiB run took 73.9 seconds, with 13.16/9.80 GiB minimum host/admission availability over 71 samples and zero cgroup memory events. This confirms one current-source mid-prefill cancellation point for IQ1_M, FP16 KV and MTP4; other boundaries and formats remain open, as does adaptive migration parity.

A [two-position adaptive recovery router trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/README.md) on the pinned ISTA-DASLab Coder IQ1_M GGUF compared verifier positions 505 and 506 across initial and same-service recovery requests. Owner placement already differed at layer 1, while activations and expert IDs matched through layer 25/26 respectively; layer 26 was the first changed activation at both positions. Expert IDs first differed at layer 27 for position 505 and layer 31 for position 506. A randomized delayed-control/adaptive pair reproduced this pattern only in the adaptive arm: delayed control matched route owners, IDs, activations, token IDs and recorded terminal state across initial/recovery requests. Both supervised services passed with 14.27/14.19 GiB minimum host/admission availability and zero cgroup events. This associates the observed change with the tested adaptive configuration, but does not isolate its operation; Phase 5 remains open.

A new [position-512 prefill/state trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-prefill-gdn2/README.md) used an opt-in layer-31 CPU Q8_1 mirror with a fresh delayed/adaptive pair. Layer-2 GDN state was bit-identical across all eight prefill chunk boundaries for the repeated 505-token prompt and across both arms. At verifier position 512, the delayed-control state and layer-2 GDN fields remained exact; adaptive initial/recovery state differed in 786,044/786,432 recurrent values and 30,711/30,720 convolution values at commit, although token IDs matched. The first observed owner change is at layer 1 with identical input activations and expert IDs; layer-2 dispatch input differs in all 2,560 values. A follow-up [layer-1 verifier-parts pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-layer1-verifier-pair/README.md) found the adaptive combined MoE output changed in all 2,560 values (relative L2 `0.00489364`), while the delayed arm was exact. An independent same-input parity oracle found the adaptive recovery rows for experts 95, 11 and 205 match the GPU results bit-for-bit; initial adaptive and delayed rows match CPU results. The separate all-layer trace reports 95 and 11 switching CPU-to-GPU but reports expert 205 as CPU-owned, contradicting the verifier-row oracle. The arithmetic difference is localized to CPU/GPU expert execution, while the owner telemetry mismatch remains unresolved. Minimum host/admission availability across the two pairs was 14.18–14.35 GiB, with zero sampled cgroup events. Phase 5 remains open.

A [full layer-26 commit-state comparison](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/commit-state-pair/README.md) at accepted position 506 confirms that the delayed initial/recovery states are identical and that delayed initial also matches adaptive initial. Adaptive recovery differs in 786,389/786,432 recurrent values and 10,240/30,720 convolution-history values. This locates the first measured persistent-state delta at the adaptive arm's accepted commit endpoint; it does not isolate the operation that introduced it. The delayed capture passed in 208.0 s with 14.38 GiB minimum host/admission availability and zero cgroup memory events. Phase 5 remains open.

A [multi-row layer-26 GDN trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/gdn-intermediate-adaptive/README.md) captured the verifier's two-token window directly. At position 505, layer-26 GDN input `x` already differed (2,560/2,560 values). At position 506, `x` and `qkv` matched, but convolved `h` differed (10,238/10,240 values), consistent with the carried convolution history differing after the preceding row. This shows the adaptive recovery input is already different before layer-26 GDN at 505 and the stateful convolution path carries a difference into 506; it does not locate the upstream layer that first changed `x`. The single-token pre/post-state hook cannot cover this T=2 window; its missing capture is recorded as unsupported. Phase 5 remains open.

An opt-in [layer-1 arithmetic mirror follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-layer1-mirror-pair/README.md) matched the adaptive initial/recovery tokens and the captured layer-1 verifier outputs at position 512; layer-2 GDN verifier and committed state also matched across arms at that position. The mirror did not restore adaptive terminal-state equality. A fresh [four-position trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-layer1-mirror-prefix-trace/README.md) confirmed layer-2 verifier and committed state remain exact at positions 512–515. However, per-GDN service hashes first diverge at endpoint 511 in GDN ordinal 3 (model layer 4), with 33/36 GDN hashes changed thereafter; delayed control stays exact through endpoint 522. Both paired arms passed supervision, with 14.14/14.20 GiB minimum host/admission availability and zero sampled cgroup memory events. The next direct raw-state target is layer 4 at endpoint 511. Phase 5 remains open; this correctness diagnostic is not a performance result.

A targeted [layer-4 prefill trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer4-prefill-state-pair/README.md) found identical GDN hashes at every repeated-prompt chunk boundary and bit-identical raw recurrent/convolution state at the end of prefill. At decode position 511, adaptive recovery's first changed dispatch activation is layer 4; delayed control remains exact. A follow-up [layer-4 verifier and state capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer4-generated-position511-verifier-pair/README.md) confirmed that the adaptive layer-4 recurrent state already differs before the selected row, its first changed GDN intermediate is input `x`, and the committed-state capture matches the service hash. Delayed control is exact, and adaptive initial matches delayed initial at the committed endpoint. This verifies a persistent-state divergence at layer 4 but leaves its upstream cause open; the next target is the preceding layer-3 transition. Both runs passed supervision with at least 14.21 GiB minimum host/admission availability and zero cgroup memory events. Phase 5 remains open.

A [layer-3 verifier capture and independent expert oracle](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer3-generated-position511-verifier-pair/README.md) isolated the preceding transition at position 511. Input activation, route IDs and router weights matched; only expert 87 changed CPU-to-GPU and its row differed. The same-input native oracle matched the service's CPU row in adaptive initial and delayed control, then matched the GPU row in adaptive recovery. The comma-separated, exact-layer selector was tested in the combined [layer-1/layer-3 mirror pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-combined-mirror-position511-pair/README.md): both targeted layer-3 output and layer-4 committed state matched at position 511. A position-516 follow-up also matched layer-4 MoE/GDN and state. However, both pairs found the adaptive trace first diverged at layer 5; the first differing generated token was at position 517. Phase 5 remains open.

The targeted [layer-5 state pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-combined-mirror-layer5-state-pair/README.md) found the verifier's layer-5 GDN intermediate first differs at `h`, with recurrent and convolution state already changed before that row. A repeated-prompt [layer-5 prefill trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-combined-mirror-layer5-prefill-pair/README.md) was bit-identical at each captured boundary for the 505-token payload. The corrected [prompt-tail trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-combined-mirror-prompt-tail505-511-corrected-pair/README.md) captured positions 505–511 and found the first layer-5 GDN input `x` difference at position 505; delayed control stayed exact. The selected prompt-tail commit states differ at captured endpoints 506, 508, 510 and 511. The position-511 raw commit hash cross-check passed. A first state-capture selection for every position is retained as a failed/unsupported cell because the hook only records one-token windows; it is documented separately. The next localization target is layer-4 GDN/MoE over those prompt-tail positions. This is correctness evidence, not a performance result.

The [layer-18 owner capture and expert-110 oracle join](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-2-3-4-5-6-8-9-10-11-12-13-15-16-18-19-24-layer18-owner-capture-pair/README.md) confirmed IQ3_XXS/IQ4_NL expert 110 as the only changed routed row at positions 506–511. Its exact-input CPU/GPU oracle outputs match both service rows bit-for-bit, with a 1.5597% CPU/GPU relative-L2 difference. Layer-18 GDN first changes at `ffn_y`; raw state at accepted position 511 is exact. The layer-5 mirror made token IDs match all 12 positions, but adaptive accepted-state hashes still differ at all prefixes. A layer-18 mirror pair is the current diagnostic follow-up. Phase 5 remains open.

The shared-source [maestro1 HIP/SYCL rebuild](../../bench/results/2026-10-20-phase5-maestro1-silu-backends/README.md) used the current CPU expert source and selector contract. HIP compiled and linked the changed CPU expert and parity sources; SYCL rebuilt the changed CPU expert source with `STRATA_SYCL_PARITY=OFF`. Both rebuilt `strata --help` checks passed in their required runtime environments. This supplies x86 build evidence only; neither backend ran a GPU model, and no Orin performance evidence follows. Phases 5 and 6 remain open.

The second randomized [layer-24 mirror context-shift pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer25-repeat2-pair/README.md) reproduced the prior inconclusive result: with the layer-24 IQ2_S/IQ4_NL selector present, adaptive initial/recovery's first captured activation difference was already at layer 3 for positions 505–511. Adaptive recovery differed at all 12 token IDs and every selected accepted-state/GDN prefix; the layer-24 committed state differed in all 786,432 recurrent and 30,720 convolution values. Delayed control remained exact. The two randomized pairs make cross-request adaptive-history influence plausible, but do not isolate its source or attribute the result to expert 173. Both new arms passed their 28-GiB supervisors with 14.23/14.27 GiB minimum host/admission availability and zero cgroup memory events. The result is a correctness diagnostic, not a performance claim; Phase 5 remains open.

A follow-up [layer-2 boundary capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer2-boundary-pair/README.md) found expert 62 (IQ2_S/IQ4_NL) changing CPU/GPU owner at positions 505–511 with IDs, inputs and router weights matched. It was the only changed routed row; combined MoE output differed at all seven positions, while layer-2 GDN `ffn_y` changed and captured earlier GDN fields matched. Raw recurrent/convolution state at accepted position 511 remained exact across initial/recovery. A paired [layer-2 mirror follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-2-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer3-boundary-pair/README.md) made the selected rows, combined output, GDN fields and position-511 state exact, but adaptive recovery still differed at all 12 tokens and accepted prefixes; first captured activation differences moved to layers 6 and 27. The [layer-5 capture and expert-26 oracle join](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-2-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer5-boundary-pair/README.md) then tied the layer-5 owner flip at positions 506–511 to the service output: exact-input independent CPU/GPU oracle rows matched, with a 1.4092% CPU/GPU relative-L2 delta. A [layer-5 mirror follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-2-3-4-5-6-8-9-10-11-12-13-15-16-19-24-mirror-layer6-boundary-pair/README.md) restored the sampled layer-5 outputs and state and made all 12 adaptive recovery token IDs match, but accepted-state hashes still differed at every prefix. First activation differences moved to layer 19 for positions 506–511 and layer 27 for position 505. Layer-18 expert 110 changes CPU-to-GPU at the six-position boundary; the same-input standalone oracle is not yet joined to service rows. Delayed control stayed exact. Phase 5 remains open.


A randomized [three-short-request adaptive history control](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-short-short-short-history-control/README.md) tested whether the intervening long request was necessary for the observed divergence. With three identical 512-token requests, adaptive token IDs matched across all three requests. Accepted-state and GDN fingerprints first differed at prefix 4 between initial and intermediate, while intermediate and recovery fingerprints matched exactly; delayed control stayed exact. At captured position 505, owner placement changed across both transitions although activation inputs and expert IDs remained exact. A same-day short/long/short repeat showed the same state-prefix result. At positions 505–511, activation inputs and expert IDs matched initial/recovery while adaptive owner placement differed. The long request is therefore not required in these tested sequences, but the causal operation remains unresolved. Both pairs passed supervision with at least 14.13 GiB minimum host/admission availability and zero cgroup memory events. Phase 5 remains open; no performance claim is made.


A same-sequence [generated-position trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-short-short-short-generated-positions512-523/README.md) captured positions 512–522 across initial, intermediate and recovery short requests. Adaptive accepted state first differed at prefix 4 between initial and intermediate, then matched exactly between intermediate and recovery; delayed control remained exact. The first selected input-activation difference in that transition was layer 27 at position 512, with expert IDs unchanged and owner placement differences at layers 26 and 27. Position 523 had no subsequent dispatch and is marked unsupported. This narrows the next owner-row/state capture but does not prove causality. Both arms passed with at least 14.13 GiB minimum host/admission availability and zero cgroup events. Phase 5 remains open.


The [layer-26 first-write localization](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-short-short-short-layer26-localization/README.md) captured positions 512–516 after repeated short requests. Adaptive layer-26 raw state first differed after position 515: pre-state was exact, then 786,410/786,432 recurrent and 10,239/30,720 convolution values changed. Layer-26 GDN `x` was the first differing captured field at position 515; its input and router weights already differed. Expert 213 changed owner CPU-to-GPU, but all ten rows changed with those different inputs, so the row is not isolated as causal. Raw states cross-check to service GDN ordinal 20; delayed control stayed exact. Layer 27 was rejected as a GDN state capture layer and is recorded as an unsupported diagnostic. Phase 5 remains open.


A [layer-16 owner / layer-17 state follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-short-short-short-layer16-owner-layer17-state-position515/README.md) captured expert 118 changing CPU-to-VRAM at position 515 with identical activation, expert IDs and router weights across three requests. The layer-17 pre-state matched before the accepted token and post-state differed; the second-to-third transition and delayed control were exact. A direct CPU-pool output capture initially appeared to disagree with the standalone CPU oracle, but the oracle used its default arithmetic mode while the service used `STRATA_NATIVE_CPU_Q8_1_DOT=all`. The mode-matched same-input CPU oracle then matched the actual service row to relative L2 9.51e-10; CPU/GPU outputs differed by 0.01352%. The verifier-parts capture is the verifier's assembled mixed-owner per-expert buffer consumed by weighted combine, not an independent CUDA oracle. A later same-service [cross-check](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position512-layer40-expert114-mirror-state-pair/README.md#verifier-parts-capture-semantics-cross-check) matched direct CPU rows to that buffer within JSON serialization precision. This validates the selected expert output for this input and mode; layer-17 input/router weights already differ, so it does not isolate the downstream state change. Phase 5 remains open.


A [position-515 layer-4 owner follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-short-short-short-layer4-owner-gdn-position515/README.md) checked the earliest observed owner switch: IQ1_M expert 153 moved CPU-to-VRAM with identical activation, IDs and router weights. A direct CPU-pool capture matched the mode-matched CPU oracle to relative L2 1.21e-9; CPU and CUDA oracle outputs were bit-identical. Layer-4 CUDA-verifier GDN intermediates and raw state were also exact across requests. This means the selected layer-4 owner row has no measured arithmetic delta in this cell. Layer 16's expert-118 transition is the first selected owner change with a CPU/GPU oracle delta, but its link to the layer-17 state difference remains unproven; Phase 5 stays open.
A layer-17 [prefill state trace with the layer-16 targeted CPU selector](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer16-q8-targeted-prefill-state/README.md)
found identical GDN chunk hashes across fresh adaptive and delayed-control
services at boundaries 64–505, plus bit-identical end-of-prompt raw state
(786,432 recurrent and 30,720 convolution values). This clears a cross-arm
prefill difference for that selector and prompt; repeated same-service prompts
reused cached work, so it does not explain the adaptive request-history state
mismatch. A requested position-505–511 verifier-state capture was unsupported
for positions 505–510 (the hook observed position 511 only) and stopped before
the second arm. Both completed prefill-pair services passed supervision with
at least 14.05 GiB host/admission availability and zero cgroup pressure/OOM
events. The failed hook coverage is retained. Phase 5 remains open.


The latest [layer-30 oracle and layer-32 state diagnostic](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer8-13-16-24-28-29-30-q8-targeted-no-cache-layer32-state511/README.md)
confirms bit-identical service CPU rows and same-input CPU/GPU oracle outputs
for experts 121 and 212. A verifier request-3 row differs from that oracle,
but the verifier input activation is not captured; this cell is unresolved and
does not qualify as a parity failure. Raw layer-32 state changes after the
accepted token from adaptive intermediate to recovery, with exact pre-state.
Phase 5 remains open.


A corrected [all-layer verifier MoE-input capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-no-cache-verifier-input-all-layers-corrected/README.md) compared three no-cache requests. All 48 delayed-control layer inputs matched; adaptive inputs first differed at layer 34 (initial-to-intermediate) and layer 12 (intermediate-to-recovery). The direct [layer-12/layer-34 pre/post state follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-no-cache-gdn-state-layers12-34/README.md) now confirms each raw post-state against the service GDN hash. Adaptive pre-state matched across the corresponding transitions, while layer-34 post-state changed initial-to-intermediate and layer-12 post-state changed intermediate-to-recovery; delayed control remained exact. All four arms passed with at least 14.09 GiB minimum host/admission availability and zero cgroup memory events. The state changes follow the already-divergent activation inputs, so the upstream cause remains unresolved. The earlier offset-bug capture is retained as invalid. Phase 5 remains open.

The [layer-33 expert-57 operator diagnostic](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer33-q8-mirror-diagnostic/README.md)
found a same-input CPU/CUDA output difference of 1.32% relative L2 for the
default operator. The opt-in targeted Q8_1 path made that isolated output
bit-identical, but applying it in a fresh-prompt no-cache service pair did not
restore adaptive accepted GDN state. Since prompt caching was disabled, these
captures do not support retained live-session or batch-slot reuse as the
cause. The isolated operator gap is confirmed; its role in the remaining
service-state mismatch is unresolved. Phase 5 remains open.

The [layer-33 expert-57 operator diagnostic](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer33-q8-mirror-diagnostic/README.md)
found a same-input CPU/CUDA output difference of 1.32% relative L2 for the
default operator. The opt-in targeted Q8_1 path made that isolated output
bit-identical, but applying it in a fresh-prompt no-cache service pair did not
restore adaptive accepted GDN state. The all-layer trace moved the first
activation difference from layers 34/12 to layers 33/32 for the two adaptive
transitions. Since prompt caching was disabled, these captures do not support
retained live-session or batch-slot reuse as the cause. The isolated operator
gap is confirmed; its role in the remaining service-state mismatch is
unresolved. Phase 5 remains open.

Generated-position tracing with the cumulative tested Q8_1 selector localized
an adaptive difference at position 512 to layer 27. Expert 213 at layer 26
changed CPU-to-VRAM owner on identical IQ2_S/IQ4_NL input; its default CPU/CUDA
oracle delta was 1.49% relative L2, and the targeted Q8_1 oracle plus captured
service CPU row matched. The layer-26 raw state became exact across the first
adaptive transition, moving the first changed activation to layer 41. That
trace then identified layer-40 expert 114, IQ3_S/IQ4_NL, changing owner on
identical input; its default oracle delta was 1.33% and its targeted Q8_1
oracle was bit-identical. The [layer-40 service mirror pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position512-layer40-expert114-mirror-state-pair/README.md) matched the captured CPU service row to the Q8_1 oracle and moved the first position-512 activation difference from layer 41 to 42. Raw layer-40 state was exact through the initial-to-intermediate transition; the later recovery transition and accepted-prefix hashes still diverged. These captures are correctness localization, not performance evidence; Phase 5 remains open.

The [layer-41 expert-171 mirror pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position512-layer41-expert171-mirror-state-pair/README.md)
measured another owner-dependent IQ3_XXS/IQ4_NL row at position 512. Its
default CPU/CUDA oracle outputs differed by 1.21% relative L2; the targeted
Q8_1 outputs matched bitwise, and the captured service CPU row matched the
oracle within relative L2 1.61e-9. With this rule, all 48 initial/intermediate
verifier inputs at position 512 and layer-42 raw pre/post GDN state matched.
Intermediate-to-recovery first differed at layer 13, and accepted GDN hashes
still differed at all 12 initial/recovery prefixes despite identical output
tokens. This remains a narrow correctness localization; Phase 5 remains open.

A [layer-41 expert-171 Q8_1 mirror](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position512-layer41-expert171-mirror-state-pair/README.md)
made the captured IQ3_XXS/IQ4_NL CPU/GPU row exact and the actual service row
matched the independent oracle within relative L2 1.61e-9. All 48 captured
initial/intermediate inputs at generated position 512 and raw layer-42 state
matched. The intermediate/recovery transition still first diverged at layer 13;
accepted GDN hashes differ at all prefixes even though token IDs match. The [layer-12 raw-state and verifier-MoE follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position512-layer12-state-after-layer41-mirror-pair/README.md) completed: its pre/post state and all captured MoE routes, parts and combined output were bit-identical across the intermediate/recovery transition, with raw state matching service GDN ordinal 9. Yet the next layer-13 input differed. This clears the sampled layer-12 MoE and recurrent state as the source at this boundary; layer-12 intermediate/residual outputs remain to be captured. Phase 5 remains open.

The [layer-12 state and verifier-MoE follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position512-layer12-state-after-layer41-mirror-pair/README.md)
and [GDN-intermediate follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position512-layer12-gdn-intermediates-mirror41-pair/README.md)
found identical layer-12 intermediates, raw state, and MoE outputs across the
three requests, with raw state matching service ordinal 9. The [layer-12/13
boundary pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position512-layer12-boundary-capture-retry-offset1/README.md)
then found identical residual, pending write, inject, and layer-13 first-read
values at position 512. An initial CPU-pool trace appeared to show the layer-13
routed activation changing, but the recovery row had no CPU-owned experts: the
verifier had not populated that host activation buffer, so the trace contained
stale data. The opt-in capture now marks activation validity per row. A
Verifier-side captures confirm layer-13 MoE inputs, all layer-13 GDN
intermediates, and raw pre/post GDN state are bit-identical across all three
adaptive requests; raw state matches service GDN ordinal 10. The first changed
authoritative verifier MoE input is layer 15 on intermediate-to-recovery (33
later layers differ); delayed control is identical at all layers. Both new
arms passed with at least 14.065 GiB host/admission availability and zero cgroup
memory events. Phase 5 remains open; layer 15 is the next boundary to localize.

A separate [position-512 layer-15 recapture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position512-layer15-gdn14-recapture-retry-countfix/README.md)
with seed 20261126 found all 48 CUDA-side verifier inputs and layer-14 raw
GDN pre/post state bit-identical across four same-service requests in both
arms. Adaptive accepted-prefix hashes diverged only at indexes 10 and 11
between the initial and intermediate requests; intermediate-to-recovery was
exact, and delayed control remained exact. CPU dispatch traces contained owner
changes, but several host activation buffers were invalid because no CPU expert
materialized them. Thus this position-512 result does not confirm a stable
first-divergence layer across seeds/history; it narrows the next capture to
generated positions 521 and 522. Phase 5 remains open.

The subsequent [positions 512/521/522 verifier and QSA trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-positions512-521-522-layer14-state/README.md)
confirmed the adaptive accepted-state delta at prefixes 10–11 is request-history
dependent: selected position-512 tensors remained exact, while position 521
first differed at verifier input layer 40 and position 522 at layer 41 during
initial-to-intermediate. Per-QSA hashes changed at layers 43 and 47; raw
layer-14 GDN state remained exact, and delayed control was exact at all selected
positions. At layer 39, experts 66, 135 and 90 (IQ2_S/IQ4_NL) changed CPU/GPU
ownership with matching IDs before those later input differences. Applying the
previously tested Q8_1 rules everywhere except layer 39 preserved matching token
IDs but did not eliminate the layer-40 verifier-input or layer-43/47 QSA deltas.
The matched-seed selector contrast then kept the tested Q8_1 rules at every
eligible layer except layer 39. The all-layer-Q8_1 run first differed at
verifier input layer 40 (position 521) and 41 (position 522) only on
initial-to-intermediate; intermediate-to-recovery was exact. Leaving layer 39
on default CPU arithmetic preserved the first mismatch at layer 40 but made
that second transition differ at layer 40 for both positions. QSA hashes at
layers 43 and 47 changed across this recovery transition only with default
layer-39 arithmetic; delayed control remained exact, and raw layer-14 GDN state
was exact across all requests in both configurations. The same-input oracle
found default CPU/GPU relative-L2 differences of 1.32–1.53%; targeted Q8_1
made five of six position/expert rows bit-identical, with the remaining
position-521 expert-90 row at 0.0120% relative L2. A cache-disabled service
capture confirmed that all three position-521 CPU rows match the standalone
default-CPU oracle bit for bit. This supports a narrow layer-39 contribution
to sampled recovery-state behavior, while the earlier adaptive divergence
remains unexplained. It is one correctness cell, not quality or performance
qualification. A same-input oracle screen of 16 earlier adaptive owner-switch
rows (23 position/expert samples below layer 39) found default CPU/GPU output
deltas of 1.06–1.56% relative L2 and bit-identical Q8_1 outputs for all sampled
rows. The position-522 layer-40 follow-up captured verifier inputs, routes, expert
parts and combined output: layer-40 IDs, weights, parts and output were exact
across all adaptive requests, as was raw layer-14 GDN state. The independent
layer-40 expert oracles for owner-changing experts 92 and 164 had 0.773% and
1.456% default CPU/GPU relative-L2 deltas, but exact layer-specific Q8_1 output.
The first adaptive verifier-input difference remains at layer 41; QSA hashes at
layers 43 and 47 change on initial-to-intermediate, while delayed control is
exact. A dedicated residual trace then found all eight values after layer 40,
before layer 41's read, and after that read bit-identical across all requests.
The layer-41 GDN capture at position 522 found that adaptive raw pre-state
already differs before this token: 785,998/786,432 recurrent values and all
10,240 convolution-history values changed. `x` and `qkv` intermediates match;
`h` is the first differing GDN field. The raw post-state hashes match the
service at ordinal 31; intermediate-to-recovery and delayed-control states are
exact. A paired [positions-521/522 layer-41 GDN capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-positions521-522-layer41-gdn-q8-diagnostic/README.md)
found exact raw layer-41 pre-state at position 521, then a differing `x` and
post-state; by position 522 the pre-state already differs. The paired
[position-521 layer-40 residual capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position521-layer40-boundary-q8-pair/README.md)
shows all eight boundary fields already differ after layer 40, before layer
41's read. Both delayed controls remained exact. A follow-up [layer-40 verifier MoE capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position521-layer40-moe-q8-pair/README.md)
found identical expert IDs but changed router weights on the adaptive initial-
to-intermediate transition; all 25,600 expert-part values and 2,559/2,560
combined output values changed, followed by the changed residual boundary.
Because the layer-40 input was already the first changed captured input, this
is a downstream effect, not the source. The position-521 [layer-39 expert-output trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position521-layer39-moe-q8-pair/README.md)
then found expert 90 moving CPU-to-GPU with matching input, IDs and router
weights. Its captured CPU and GPU rows each match an independent same-input
oracle exactly; the rows differ in 2,559/2,560 values. Stage isolation finds
matching Q8_1 inputs and gate/up dots, three hidden-block FP16 scale deltas
with identical codes/sums, and an exact down projection when fed the CUDA
hidden blocks. The changed expert contribution alters the combined layer-39
output and residual boundary, then the following read; delayed control remains
exact. This directly explains this sampled divergence at the SwiGLU/hidden
scale seam. A [global division-expression trial](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position521-layer39-moe-q8-pair/silu-order-trial.md)
made expert 90 exact but regressed the previously exact layer-31 expert-22
case, so it was reverted. The current layer-41 raw state delta is relative L2
`7.27893e-4` after position 521 and `7.38754e-4` after 522; this is not a
long-chain bound. Phase 5 still needs a cross-format correction or a validated
drift contract. See also the [matched-seed layer-39 contrast](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-positions521-522-layer39-q8-all-others-seed20261127/README.md),
[layer-40 verifier capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position522-layer40-verifier-q8-recapture/README.md),
and [position-522 layer-40 residual trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position522-layer40-boundary-q8-pair/README.md).
Phase 5 remains open.

A follow-up direct-division replay on the layer-3 IQ2_S/IQ4_NL expert-182
activation changed 408/1,920 reconstructed hidden floats but left the packed
Q8_1 bytes and final expert output unchanged; both remained bit-identical to
CUDA. The parity helper's reciprocal-form float assertion reported a
diagnostic failure, so the run is not a passing parity test. This confirms
that the division expression is activation-sensitive: it alters three
layer-39 hidden scales, changes no encoded values at layer 3, and regresses
the layer-31 IQ3_XXS case. No formula change was retained. Details and the
reproducible temporary patch are in the [layer-3 diagnostic](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer3-generated-position520/operator-checks/expert182-q8_1-mirror/direct-silu-division/README.md).

Current-source backend rebuilds have also completed on [maestro1](../../bench/results/2026-10-20-phase5-maestro1-boundary-rebuild/README.md): HIP and SYCL compiled and linked serially, and both CLI help checks passed. The five changed shared-source/header hashes match the Orin checkout. This is x86_64 build evidence only; no HIP or SYCL runtime was exercised.

A follow-up [maestro1 rebuild](../../bench/results/2026-10-20-phase5-maestro1-native-expert-rebuild/README.md) used the current `src/kernels/cpu/native_expert.cpp` hash after its selector and Q8_1 arithmetic changes. HIP rebuilt 22 targets, including `native_expert_parity`; SYCL rebuilt the shared CPU library and `strata` in three steps. Both CLI help checks passed. One SYCL Clang warning is retained in the logs. This is x86_64 compile/link evidence only; no accelerator runtime was tested.

A [current top-level source refresh](../../bench/results/2026-10-20-phase5-maestro1-current-shared-rebuild/README.md) verified all five modified C++/header hashes against maestro1 and rebuilt the HIP source tree serially; its CLI help check passed. SYCL uses a separate migrated overlay: the shared CPU `native_expert.cpp` was compiled at the current hash in the targeted rebuild above, while this refresh found no SYCL work for the additional CUDA verifier/trace diagnostic files. Those CUDA-specific diagnostics are not claimed as ported to SYCL. maestro1 remains x86_64 build evidence only.

A randomized current-source [64-token accepted-prefix pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-long64/README.md) on the pinned Coder IQ1_M model (binary SHA256 `081212f0…`) completed under both 28-GiB supervisors. Delayed control matched all initial/recovery short-request state fingerprints and token IDs. Adaptive recovery differed from its initial short request at 40/64 token IDs, first at output index 23 (accepted position 534); its accepted state first differed at position 515 (zero-based prefix 4), with GDN ordinals 13–35 changing and 60/64 recovery-prefix states differing. Across treatments, initial-short token IDs matched despite state differences beginning at prefix 30; long-request output first differed at prefix 20. Minimum host/admission availability was 13.97 GiB (adaptive) and 14.34 GiB (delayed control), with zero cgroup memory events. This current-binary result narrows the accepted-chain mismatch but does not identify its cause or bound drift beyond this sequence. Phase 5 remains open.

A follow-up [position-515 all-layer trace](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-position515/README.md) reproduced the first state difference at accepted prefix 4. Adaptive per-GDN hashes first differ at ordinal 13 (model layer 17); delayed control remains exact. The first valid changed dispatch input is layer 18, where all 2,560 values differ (relative L2 `0.0035630`) while expert IDs and owners match. A current-binary [raw layer-17 verifier capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer17-position515/README.md) then found bit-identical pre-state but a changed `x` input (2,555/2,560 values, relative L2 `7.7344e-6`) before the recurrence update; 785,280/786,432 recurrent and 10,232/30,720 convolution values differed afterward. Delayed control matched all raw state and intermediate fields. This moves the numerical source upstream of layer-17 recurrence but does not identify the upstream operation. Both new pairs passed with zero cgroup events and at least 14.17 GiB availability. Phase 5 remains open.

A further current-binary [layer-16 service CPU-row capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer16-service-cpu-output/README.md) joined position 515 to independent same-input expert oracles. Actual service outputs for experts 118 and 39 matched the CPU Q8_1 oracle bit-for-bit in both arms. Expert 118's same-input CPU/CUDA outputs differed in all 2,560 values (relative L2 `1.35199e-4`); expert 39 was bit-identical. The current dispatch trace shows both experts move CPU→VRAM on adaptive recovery with matching layer-16 input and IDs. This identifies expert 118 as an owner-dependent numerical contributor at this sampled boundary, but does not establish the complete combined-layer delta or a general correction. Both arms passed with zero cgroup events and at least 14.25 GiB availability. Phase 5 remains open.

A [temporary direct-division SwiGLU experiment](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer17-position515/division-formula-trial/README.md) on the exact expert-118 activation left the CPU output and CPU/CUDA delta unchanged. Q8_1 input and gate/up dots matched CUDA; CPU down on CUDA hidden blocks also matched. Hidden Q8_1 blocks 10, 30 and 50 differed only in FP16 `d` (`de16` CPU, `dd16` CUDA); sums and integer codes matched. A source-faithful CUDA replay from the captured gate/up rows, built for SM87 with the production `--use_fast_math` setting, reproduced all 60 captured Q8_1 blocks byte for byte. Its hidden floats differed from the CPU direct-expression values in 600/1,920 entries (maximum absolute difference `2.98023e-8`, relative L2 `5.12883e-8`), localizing this sample's difference after gate/up and before hidden quantization. The [cross-capture scale analysis](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/hidden-q8-scale-tie-analysis.md) found this CPU scale exactly at the FP16 midpoint, while two other same-input captures place the midpoint on the opposite side or miss it by two float32 ULPs. A global scale tie-bias is therefore not a correction. An accurate-`expf` CUDA replay retained the same three scale mismatches, so that single change did not correct the sample. The alternate CPU formula also failed the parity harness's reciprocal-form independent reconstruction. It was rejected; `src/kernels/cpu/native_expert.cpp` was restored and `native_expert_parity` rebuilt to SHA256 `bd7f8f01…`. Phase 5 remains open.

A randomized [64-token layer-17 raw-state pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer17-common-prefix-samples/README.md)
confirmed the same boundary over a longer accepted chain. Adaptive per-GDN
hashes first differ at accepted position 515 (layer 17), before output tokens
diverge at position 534. With the same token and bit-identical layer-17
pre-state at position 515, 785,280/786,432 recurrent values and 10,232/30,720
convolution-history values differ after the update. Delayed control is exact
through all four sampled positions. The run passed both 28-GiB supervisors with
at least 14.09 GiB host/admission availability and zero cgroup events. A first
attempt selecting uncaptured position 575 is retained as a failed harness cell;
the valid repeat covered positions 515, 519, 522 and 527. This does not establish
the cause or a general drift bound; Phase 5 remains open.

A current-binary [layer-16 to layer-17 boundary capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer16-to17-position515/README.md)
joins the adaptive state change to one changing expert row. At accepted
position 515, layer-16 input, token, expert IDs and router weights match across
initial/recovery. The shared output and nine expert rows match; only expert 118
changes, and the combined MoE output differs (relative L2 `2.50977e-5`). The
next layer's first changed GDN field is `x` (relative L2 `7.73436e-6`) with an
identical pre-state and changed post-state. A same-binary dispatch trace and
same-input oracle identify expert 118's CPU-to-VRAM owner transition and its
CPU/GPU arithmetic difference. Delayed control is exact. This strongly
identifies an owner-dependent contributor for this sample, without proving a
general correction; Phase 5 remains open.

A [current-binary layer-16 residual-boundary capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer16-boundary-position515/README.md)
recorded the layer-16 MoE delta entering the following layer. At position 515,
post-layer `bo` differs in 2,557/2,560 values, while `R` and `inj2` before the
next read stay exact. The subsequent `xn` changes in 8,898/10,240 values
(relative L2 `6.09090e-6`), followed by layer-17 GDN `x` and raw-state changes.
Delayed control is exact in every captured field. The analysis script was
corrected to handle two-record pairs and validated on the retained adaptive and
delayed captures. Together with the expert-118 row and same-input owner oracle,
this strongly localizes the sampled state divergence but does not prove a
general correction or error bound. Phase 5 remains open.

A randomized [short-only layer-27/28 capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer24-short-short-short-no-cache-layer27-state28-pair/README.md)
removed the preceding long request and compared three repeated 512-token
requests. At layer 27, input, token, routed expert IDs and router weights are
bit-identical. Expert 175 moves CPU-to-CUDA in the adaptive arm; each captured
service row matches a same-input native CPU or CUDA oracle exactly. The owner
change affects its 2,560-value row and combined MoE output, while the shared
expert output is unchanged. Delayed control remains exact. Adaptive layer-28
committed GDN state then differs in 786,199/786,432 recurrent and
10,240/30,720 convolution-history values; raw state hashes match the service
for all three requests. This verifies an owner-dependent contributor at the
sampled transition but does not establish the full drift cause or a general
bound. Both arms passed supervision with at least 14.10 GiB host/admission
availability. The layer-28 intermediate capture identifies `x` as the first
changed field (2,560/2,560 values, relative L2 `9.3027e-4`); subsequent fields
and committed state differ, while the intermediate-to-recovery trace is exact.
Delayed-control intermediates remain exact across both transitions. This links
the sampled layer-27 owner change to a changed next-layer input and state, but
does not establish the full drift cause or a general bound. A second supervised
run with seed 20261079 reproduced the layer-27
dispatch, verifier inputs, expert parts, combined output and raw committed
state byte for byte. This verifies reproducibility for this fixed prompt and
greedy decode, not an independent randomized workload sample. Phase 5 remains
open.

A [current-binary Q8_1 owner-mirror chain](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer27-33-q8-mirror-chain.md)
extended the same short-only prompt boundary through layers 27–30 and 33.
Same-input native CPU/CUDA oracles and verifier captures confirm exact selected
expert rows for the requests whose activation matches the oracle. Layer-28 raw
committed GDN state is exact in these mirror pairs, with service-hash
cross-checks. However, adaptive accepted-state fingerprints still differ at
all 12 prefixes; two selector combinations also change recovery token IDs by
9/12. The first captured dispatch-input boundary shifts with the selector
chain (layers 29, 30, 31 and 34); the two-row dispatch capture does not cover
all three verifier requests, and the layer-33 recovery input already differs
from the oracle activation. These opt-in interventions do not provide a
general adaptive-migration fix or drift bound; no default changed. Phase 5
remains open.
A fresh-source [64-token Q8_1 all-dot adaptive migration pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-source-q8-all-long64-pair/README.md)
rebuilt the current working tree (binary SHA256 `b6721876…`) and directly
compared all accepted-prefix token IDs, aggregate state fingerprints, and 36
per-GDN hashes across a same-service short/long/short sequence. Delayed-control
recovery matched all 64 tokens and state prefixes. Adaptive recovery differed
at 40/64 token IDs and 60/64 state prefixes, first at prefix 4 / accepted
position 515, where GDN ordinals 13–35 changed. This confirms that enabling
Q8_1 on all eligible CPU dots does not resolve or bound migration drift. Both
28-GiB supervisors passed with zero cgroup memory events and at least 13.78
GiB host/admission availability; this was a correctness run, not a performance
comparison. Phase 5 remains open.

At the same pair's captured prompt-tail dispatch position 511, all expert IDs
and all 46 available verifier input activations matched between the initial and
recovery short requests; the capture had no CPU activation rows at layers 36
and 45. Adaptive residency changed owners at 23 layers, while delayed control
changed none. The updated comparator maps those captures to the initial and
recovery requests rather than mislabeling them as initial and long.

A follow-up [144-row three-request layer-27–33 capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer27-33-q8-mirror-all-three-dispatch-state28-pair/README.md)
corrects the earlier two-row dispatch coverage. The initial-to-intermediate
adaptive activations and expert IDs match, with owner changes at ten layers;
the intermediate-to-recovery activation first differs at layer 32 and expert
IDs change at layers 32, 34, 39, 43 and 47. The third adaptive layer-33
verifier input is now included and does not match the independent oracle
activation. Adaptive accepted-state hashes still differ at all 12 prefixes
and recovery differs at 9/12 tokens, so the expanded coverage does not close
the migration-state issue. Both runs passed with at least 14.13 GiB
host/admission availability and zero cgroup memory events.

The current-source [seven-block Coder IQ1_M long-prompt MTP × KV confirmation](../../bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-long-confirm7/README.md)
completed 28/28 arms on 2026-10-20: MTP off/4 × FP16/INT8 KV on the held-out
7,501-token retrieval-plus-arithmetic task. All exact 45-token answers passed;
all same-day pairs matched 1,934 expert slots / 3,807 MiB measured residency.
The minimum host availability was 16.96 GiB and admission availability 10.71
GiB; per-arm 28-GiB cgroups recorded zero high/max/OOM/OOM-kill events. Named
rail energy was estimable for all 28 request windows. On this task MTP4 reduced
decode throughput by 10.10% with FP16 KV and 8.67% with INT8 KV; client total
time rose 0.94% and 1.06%, respectively, with seven-block paired intervals
reported in the result. VIN_SYS_5V0 request-window energy rose 0.57% and 0.71%.
These are board-rail estimates including idle/background draw, not process
energy. The result does not select a general MTP/KV profile or close Phase 6;
other planned workload and cross-factor cells remain. Phase 5's adaptive
persistent-state divergence also remains unresolved, so Phase 8 stays open.

The separate [2026-10-20 short-task confirmation](../../bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-confirm7/README.md)
used a different candidate binary hash from the long-task confirmation above,
so those two campaigns are not pooled for a workload interaction. A fresh
randomized seven-block short+long MTP × KV campaign on one binary began on
2026-10-21 at
[`bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/`](../../bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/).
All 56 arms passed with exact held-out answers and no cgroup memory events.
The paired design matched same-day execution and 1,934 expert slots / 3,807
MiB residency across all eight cells. On the 7,501-token task, MTP4 reduced
decode throughput by 9.17% with FP16 KV and 9.24% with INT8 KV; client total
time rose 0.59% and 1.01%. On the 512-token task, latency intervals included
no change, with two slow MTP4 arms retained and documented. All 56 named-rail
energy windows were estimated. The campaign report includes cross-factor
intervals, clock and memory observations, the cell Pareto table and the raw
arm records. MTP4 is dominated for both long-task KV cells on the measured
latency/board-rail coordinates; no default changed. This current-source
confirmation closes only the held-out MTP × workload × KV cells; Phase 6
remains open for its other planned factors and response-model work. The
blocked log-response fit has full design rank but flags the two slow short-task
MTP4 arms (absolute studentized residuals up to 6.47), so its intervals are
diagnostic and the paired bootstrap remains primary. A separate randomized
eight-arm follow-up block passed all exact-answer and memory audits; neither
short-task delay recurred, while long-task MTP4 decode throughput was again
about 9% lower in both KV cells. Its one-pair comparisons have no confidence
interval and remain separate from the seven-block primary analysis. See the
[follow-up report](../../bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/followup/README.md).

A randomized current-source [Coder IQ1_M cache × context screen](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-screen3/README.md)
then crossed requested cache arguments 1,500/3,000 with configured contexts
8K/16K on the exact 512-token retrieval task, holding MTP off, FP16 KV, prefill
64 and eight workers fixed. All 12 measured requests returned the exact
45-token answer. The larger cache admitted 1,934 versus 3,903 expert slots
(3,807 versus 7,615 MiB); median client total time was about 12% lower at both
context settings, while configured context changed medians by less than 0.5%.
One slow 16K/smaller-cache request was retained. Minimum host/admission
availability was 14.14 GiB with zero cgroup high/max/OOM events. This is a
three-request-per-cell screen on one short prompt, not independent confirmation
or a setting recommendation. A held-out task exercising the larger context
was subsequently confirmed in the seven-block run linked below; Phase 6 stays
open for the remaining interactions and response-model analysis.

A seven-block current-source [Coder IQ1_M cache confirmation](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-confirm7/README.md)
then paired cache arguments 1,500/3,000 at fixed 8K context, MTP off, FP16 KV,
64-token prefill and eight workers. Fourteen fresh service cells completed 42
measured requests; all exact held-out 47-token answers passed. The 3,000
argument admitted 3,903 slots / 7,615 MiB versus 1,934 / 3,807 MiB at 1,500.
Across seven independent same-day pairs, the larger cache reduced median client
TTFT 13.47% (95% paired-block bootstrap interval −13.61% to −12.90%) and total
request time 12.83% (−12.96% to −12.30%); prompt and decode throughput rose
15.77% and 10.24%. Minimum host/admission availability was 14.19 GiB with
zero sampled cgroup pressure/OOM events. This confirms only the cache effect
for this short Coder IQ1_M task at 8K; the 16K context screen did not exercise
long-context behavior. No default changed, and Phase 6 remains open.


A current-source [7,501-token Coder cache × context screen](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-screen3/README.md) completed three randomized blocks across 1,500/3,000 cache arguments and 8K/16K configured context, with one warmup and one measured request per fresh service. All 12 requests returned the exact answer at 7,501 prompt and 45 completion tokens. At 8K the larger cache improved median paired client TTFT/total time 7.99%/7.97%; at 16K it improved 7.45%/7.45%. Actual allocation was 1,934/3,903 expert slots (3,807/7,615 MiB). Minimum host/admission availability was 14.11/8.88 GiB with zero cgroup pressure/OOM events. The context effect was near zero at the smaller cache and about 1% at the larger cache; the cache-by-context ratio-of-ratios was under 1% for client total time. This is screening evidence only: no confidence intervals, energy, sustained service or profile promotion. A seven-block confirmation with a different held-out long prompt subsequently confirmed the cache effect at fixed 16K context; the complete 8K/16K cache interaction remains under held-out confirmation below. An initial cell was confounded by an overlapping model-shard checksum read that loaded data into host memory; it is retained and excluded. The clean rerun used stored hashes and passed. Phase 6 remains open.

A held-out [seven-block Coder IQ1_M cache confirmation at 16K context](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-confirm7/README.md)
completed all 14 fresh-service cells with 42 exact measured responses on the
current binary. Each answer matched the independent 7,501-prompt/48-completion
token workload oracle. With MTP off, FP16 KV, 64-token prefill and eight
workers fixed, the 3,000-MiB requested cache reduced paired median client
request time by 7.10% (95% paired-block bootstrap interval 6.99%–7.15%) versus
1,500 MiB; prompt and decode throughput rose 7.46% and 9.17%. The campaign's
minimum host/admission availability was 14.02 GiB, with zero sampled cgroup
pressure, limit or OOM events. This confirms the held-out cache effect for this
near-limit task at configured 16K context; it does not estimate the context
interaction or select a general setting. No default changed, and Phase 6
remains open for the remaining supported interactions and response-model
analysis. Separate tegrastats integration estimated all 42 measured request
windows: paired-block median `VIN_SYS_5V0` joules/output-token fell 6.94%
(95% interval 6.61%–7.08% lower), `VDD_GPU_SOC` fell 4.38% (4.26%–4.51%) and
`VDD_CPU_CV` fell 21.69% (21.64%–22.52%). These named rails include board
idle/background draw and are not process-attributed. The wrapper reported a
shell error after the final service cell had completed; all cell manifests and
the campaign analyzer passed, and rerunning the wrapper verified all seven
blocks without modifying results.

A held-out [seven-block Coder IQ1_M cache × context confirmation](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/README.md) completed 28 measured fresh-service cells: a randomized 2×2 of requested expert-cache arguments 1,500/3,000 MiB and configured contexts 8K/16K, using a held-out 7,501-token retrieval/arithmetic prompt with exact 48-token output. The original block 7 crossed local midnight and is preserved but excluded from inference; a separately randomized same-day replacement supplies the seventh block. The final analyzer passed with no errors, exact-answer/token checks in all cells, 18,126 scoped telemetry samples, and zero cgroup pressure/limit/OOM events. Minimum host and admission availability were both 13.93 GiB.

At 3,000 versus 1,500 MiB, median paired client total latency fell 7.95% at 8K context (95% paired-block bootstrap interval 7.93%–15.11%) and 7.71% at 16K (7.23%–7.82%). Median TTFT fell 7.99% at 8K (7.94%–15.20%) and 7.72% at 16K (7.21%–7.81%). The client-total cache-by-context interaction was +1.12% (95% interval +0.22% to +8.58%); the wide 8K interval reflects block variation, including a 395s measured request at 1,500 MiB/8K. These results apply to the pinned current-source Coder IQ1_M model, MTP-off/FP16-KV profile, and this long held-out task. They do not promote a general serving profile or close Phase 6's other Phase 6 interactions, broader response-model and energy/Pareto work. Clocks were sampled dynamically; EMC frequency was unsupported. Exact model, binary, source and workload identities are pinned in the campaign design.

The [block-adjusted log-response analysis](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/README.md#block-adjusted-log-response-model) of the same 28 cells is full rank (10 parameters, 18 residual degrees of freedom). Its mean-log client-total cache-by-context estimate is +2.97% (whole-block bootstrap interval +0.56% to +5.67%), directionally consistent with the primary paired median ratio-of-ratios of +1.12% (+0.22% to +8.58%). Decode throughput has an internally studentized residual of 3.93 at block 7 / 1,500 MiB / 16K, beyond the exploratory 3.0 screen; the response model remains diagnostic, with the paired-block median bootstrap primary. This adds no energy or serving-default claim; Phase 6 remains open.

A current-source [direct-division adaptive-state rerun](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-64pos/README.md) completed a randomized same-binary adaptive/control pair on 2026-10-22. It repeated the pinned Coder IQ1_M 512→2,048→512-token request sequence, MTP2, CPU Q8_1 dot selector `all`, and 64 generated tokens per request. Delayed control was bit-exact in committed layer-32 GDN recurrent/conv state at positions 515/534/574 and in all 64 recovery tokens. Adaptive state was exact at 515, then recurrent/conv relative L2 was 0.00527/0.01052 at 534 and 0.01435/0.02024 at 574; all 64 recovery tokens nevertheless matched. Raw captures matched accepted-prefix service hashes. A same-day [multiply-by-sigmoid comparison](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-multiply-sigmoid-same-day-state-bound-64pos/README.md) then repeated the same seed, model, prompts, controls, and request sequence with only the CPU SwiGLU expression changed. It reproduced 40/64 recovery-token differences and 0.524/0.916 recurrent/conv relative-L2 drift at position 574; direct division had 0/64 token differences and 0.0144/0.0202 drift. Delayed-control state was exact in both pairs, and all raw captures matched accepted-prefix service hashes. Together with the captured single-row operator oracle, this attributes this scenario's regression to CPU SwiGLU expression ordering. The temporary multiply-expression source was reverted and the direct-division build restored. Both pairs passed with at least 14.21 GiB host/admission availability and zero sampled cgroup memory events. This does not bound longer chains, other models or operators, measure a throughput effect, or close Phase 5.

A reversed-order [128-token direct-division recovery pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/README.md) tested the same short→long→short inputs at twice the generated length. Delayed control remained exact for all 128 recovery tokens and all captured states. Adaptive recovery first differed at output index 47 (73/128 tokens differed); layer-32 recurrent/conv relative L2 was 0.3106/0.6531 at position 574 and 0.4537/0.8835 at position 638. Position 574 follows the first token difference, so later state deltas include changed token history. The run shows that the direct-division result on 64-token requests does not bound the longer chain. A targeted [boundary capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/first-drift-boundary/README.md) found nonzero layer-32 state drift at positions 557 and 558 (recurrent/conv relative L2 0.01355/0.00964 and 0.01319/0.00986) before the first differing output at index 47; consumed token IDs still matched through index 46. This places state divergence before the changed token but does not locate the earlier layer/operator. Both paired arms passed with minimum host/admission availability above 14.24 GiB and zero sampled cgroup memory events; the adaptive-only boundary replay passed with 14.25 GiB. Phase 5 remains open.

The full restored direct-division Orin Release CTest suite passed 132/132 with the generated one-layer Q2_0 S2 fixture; the two optional IQ fixture tests remained skipped. The x86 AVX-512 VNNI-only `expert_parity` check now reports an explicit skip on ARM64 instead of attempting unsupported instructions. A later CTest attempt using a nonexistent fixture path failed only `pool_test`; rerunning with the actual generated fixture passed the entire suite. Current shared CPU expert source also rebuilt and linked for HIP and SYCL on maestro1 with one job; both CLI-help checks passed. See the [maestro1 build report](../../bench/results/2026-10-22-phase5-maestro1-q8-selector-backend-build/README.md). These are compile/startup checks, not GPU runtime results.

A supervised [all-layer committed-GDN replay](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/all-gdn-layers/README.md) extended the 128-token adaptive recovery sequence with raw state at all 36 GDN layers and six positions. All 432 raw records matched the per-layer accepted-prefix service hashes. Position 515 is exact at every GDN layer. At position 534, the earliest changed model layer at that selected endpoint is layer 22: 786,051/786,432 recurrent values differ (relative L2 `1.405e-4`), while its convolution history and all earlier GDN layers are exact. Layer 22 remains the earliest changed layer at positions 557 and 558 (`2.554e-4`/`1.113e-3` and `2.524e-4`/`7.552e-4` recurrent/convolution relative L2); token IDs still match at those positions. This is a position-specific comparison, not the earliest state difference over the full accepted-prefix timeline; a later full hash scan found position 519/layer 32. It does not isolate the responsible operation at either boundary. The 128-token adaptive run completed with 14.13 GiB minimum host/admission availability and zero cgroup memory events. This is one-prompt correctness localization, not a performance result or general migration bound. The all-layer dump is 1.4 GiB and remains local. The opt-in capture extension passed 10 focused accepted-window, verifier, GDN and graph CTests. maestro1 rebuilt and linked the HIP target with one job and passed `strata --help`; SYCL reported no work because the CUDA verifier translation unit is not part of that target. No accelerator runtime was exercised there. Phase 5 remains open.

A paired [all-layer verifier-input capture at position 534](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer-inputs-position534/README.md) then found model layers 0–21 bit-exact for the same token in initial and recovery requests, with the first changed activation at layer 22 (all 2,560 values differ; relative L2 `3.7883e-4`). This aligns the earliest changed layer-22 committed GDN state with an already changed layer-22 input, narrowing the onset to layer 21's output path. It does not yet separate expert dispatch/output from other layer-21 operations. The same three-request 128-token replay passed at 14.14 GiB minimum host/admission availability with zero cgroup events. Next: capture layer-21 dispatch ownership and same-input expert outputs, then verify them against the independent native expert oracle. Phase 5 remains open.

The subsequent [layer-21 dispatch capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer21-owner-position534/README.md) found identical layer-21 inputs, routes, weights, owner kinds, all ten expert rows, and shared/combined MoE outputs for token 3155 at position 534. This rules out a layer-21 MoE-owner or MoE-output change for that token; it does not yet resolve the post-MoE GDN/residual path. The run passed with 14.20 GiB minimum host/admission availability and zero cgroup events. Next: capture layer-21 GDN intermediates and residual boundaries at position 534. Phase 5 remains open.

The [layer-21 GDN and boundary follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer21-gdn-boundary-position534/README.md) found all ten layer-21 GDN intermediates, pre/post state, and every captured residual/hyperconnection field through layer 22's first read bit-exact for the same token. A separate router-input capture showed a changed tensor at layer 22 for that selected position. The subsequent [fused GR-read probe](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer22-gr-read-position534/README.md) found all five fields bit-identical there. These are later-position negative checks; the full accepted-prefix scan and raw position-519 capture summarized below supersede them for onset localization.

The [layer-22 fused GR-read capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer22-gr-read-position534/README.md) found all five read fields bit-identical at position 534 for token 3155, despite the 73/128 recovery-token mismatch later in the sequence. That selected-position result did not locate the first divergence. Scanning accepted-prefix per-layer service hashes over all 256 positions instead found the earliest changed hash at position 519, GDN model layer 32; later hashes differ in additional GDN and QSA layers. This is hash-only and supplies no raw numeric delta. The previous layer-22 and position-534 captures are later boundaries and must not be described as the onset. A supervised paired raw-state/intermediate capture across positions 515–519 is underway. Phase 5 remains open.

The paired [position-515–519 raw-state and boundary capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer32-position515-519/README.md) confirmed the position-519 onset on the same Coder IQ1_M 128-token recovery sequence. Adaptive layer-32 committed state is exact through position 518; at 519 its recurrent matrix differs in 564,534/786,432 values (relative L2 `1.2833e-7`) while convolution history stays exact. All ten raw records match service hashes, and delayed control is bit-exact across the five positions. At 519, verifier input first differs at layer 32 (2,554/2,560 values, relative L2 `1.4294e-5`); layer-31 `bo` already differs while `R` and `inj2` remain exact. The layer-32 `x` is its first changed GDN field, and verifier pre/post state matches adjacent commits. Layer-32 router IDs stay fixed but its weights, expert rows and combined output differ downstream. Both arms had 14.18 GiB minimum availability and zero cgroup events.

The follow-up [layer-31 owner capture and expert-22 oracle](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer31-owner-position519/README.md) found bit-identical layer-31 input, route IDs and weights at position 519, with experts 76, 22, 198 and 210 changing CPU-to-CUDA ownership. Expert 22 alone changed among the ten output rows (2,559/2,560 values; relative L2 `1.31996e-4`); its CPU and CUDA service rows each match their same-input independent oracle bit-for-bit. The combined layer-31 output changes before the layer-32 input/state delta. This identifies an owner-dependent numerical contributor in this single transition. It does not establish that mirroring the row resolves longer accepted-prefix recovery. That full-chain arithmetic-mirror test is recorded below. Next: trace the earlier position-515/GDN-ordinal-17 difference across long-request restoration, with delayed control, per-layer hashes, raw state and token IDs as gates. Phase 5 remains open.


A layer-31 [reciprocal-SiLU arithmetic mirror experiment](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer31-reciprocal-silu-state-bound-128pos/README.md) tested the narrow owner-dependent contributor from the position-519 capture. The independent same-input expert-row oracle passed bit-for-bit under the reciprocal expression (0/60 hidden blocks and 0/7,680 output words different), but the full 128-token adaptive recovery pair rejected it: the adaptive arm first differed at output index 6 (121/128 total) and its layer-32 committed state had already shifted at position 515 (recurrent relative L2 `0.001685`, convolution `0.006613`). The direct-division adaptive baseline first differed at index 47 (73/128); both delayed controls were exact. At position 515 the GDN input `x` already differed, and the candidate also had changed layer-31 router weights and expert parts, so this experiment does not isolate a causal expression-level effect. Both arms passed with at least 14.07 GiB minimum host/admission availability and zero sampled cgroup events. Keep the selector opt-in and default-off; reject it as a recovery correction. Next Phase 5 work returns upstream in the adaptive chain to localize changed inputs/owners with raw state, hashes and token history.


After adding the opt-in reciprocal-SiLU experiment selector, the shared native CPU expert sources were rebuilt against the current source on maestro1. HIP linked and its current `strata --help` returned 0. SYCL compiled all 20 steps and linked after exposing the installed oneMKL directory through `LIBRARY_PATH`, but the current `strata --help` attempt aborted with exit 134 and no diagnostic. Record SYCL as compile/link-only for this snapshot; no runtime or accelerator behavior is qualified. Source and binary hashes are in the [maestro1 backend report](../../bench/results/2026-10-22-phase5-maestro1-q8-selector-backend-build/README.md).


A narrower [layer-31/expert-22 reciprocal-SiLU test](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer31-expert22-reciprocal-silu-state-bound-128pos/README.md) followed the rejected layer-wide mirror. In a same-binary seed-`20261085` 128-token pair, delayed control remained exact but the adaptive arm differed on 85/128 recovery tokens, first at index 43. Its accepted-prefix per-layer GDN hash scan first diverged at absolute position 515/GDN ordinal 17; the separate direct-division reference first diverged at position 519/ordinal 24. At position 515, captured layer-32 recurrent/conv state differed by relative L2 `0.001685`/`0.006613`; raw bytes matched service hashes. Minimum host/admission availability was 14.126/14.097 GiB for adaptive/control, with zero sampled cgroup memory events. This candidate is rejected as a recovery correction. The layer-31 owner capture remains local evidence; it does not identify the source of the earlier transaction difference. Next: trace state across long-request restoration and earlier GDN ordinals, keeping accepted tokens and direct raw state as gates.


A 64-token [layer-22 raw-state follow-up](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer22-position515-expert22-reciprocal-followup-64pos/README.md) used the same seed, binary and expert-22 selector. Adaptive recovery still differed on 21/64 tokens, first at index 43, while delayed control was exact. Raw layer-22 state was bit-exact between initial and recovery requests at positions 512–519 in both arms. The completed same-seed 128-token [raw recapture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer22-position515-expert22-reciprocal-followup-128pos/README.md) confirms the length-dependent boundary: adaptive recurrent and convolution state first change at position 515, and all captured raw hashes match service GDN ordinal 17 at positions 512–519; delayed-control state is bit-exact throughout those positions. A same-seed [layer-21 owner capture](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer21-position515-expert22-chain-128pos/README.md) narrows this further: layer-21 MoE input, expert IDs and router weights match across initial/recovery requests, but rank 7 / expert 132 moves CPU→GPU. Its row changes in all 2,560 values (relative L2 0.014265), shifting the combined layer-21 output by relative L2 0.002059. Raw all-layer verifier inputs first differ at layer 22 (relative L2 0.0009497); delayed control stays exact. A same-seed [direct-division control pair without the selector](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer21-position515-direct-division-control-128pos/README.md) keeps expert 132 on CPU and has exact layer-21 rows/output at position 515, making the migration selector-associated in those runs. Adaptive direct-division recovery still first differs at index 47 (73/128) and its first GDN divergence is ordinal 24; delayed control is exact. A traced repeat records accepted-only adaptive round 88 at position 598 selecting layer 21 `132>12` (expert 132 in, expert 12 out), preceding the recovery owner change. The [trace report](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer21-position515-expert22-adapt-trace-repeat-128pos/README.md) confirms the same layer-21 row/output deltas and exact delayed control. This is repeated same-seed evidence, not yet a held-out prompt validation or a general performance claim. A distinct [held-out retrieval prompt pair with the selector](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer21-position515-expert22-heldout-prompt-128pos/README.md) and its [direct-division control](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer21-position515-heldout-direct-division-128pos/README.md) both show 19 adaptive recovery-token differences (first GDN ordinal 0), with delayed controls exact. At layer 21 / position 515 the selector and direct-division adaptive captures have identical combined-output hashes; expert 132 remains GPU-owned in both requests. That retrieval prompt ends before round 88. The later [open-response selector/no-selector pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer21-position515-expert22-open-response-128pos/README.md) reaches round 220, reproduces expert-132 CPU→GPU migration and adaptive drift in both configurations, and has identical tokens, accepted GDN hashes, and captured layer-21 rows across configurations. Its same-input independent oracle confirms the owner-specific output delta. The open-response runs passed with at least 14.09 GiB availability and zero sampled cgroup events.

The [open-response selector pair](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer21-position515-expert22-open-response-128pos/README.md) and [matched no-selector control](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer21-position515-open-response-direct-division-128pos/README.md) used the prepared 7,512-token held-out report prompt (2,048-token suffix), short–long–short sequence, seed `2026102251`, and 128 generated tokens per request. All four arms passed with minimum host/admission availability between 14.09 and 14.27 GiB and no cgroup memory events. Both adaptive recoveries differed on 113/128 token IDs and first GDN hash difference was ordinal 17; both delayed recoveries were bit-exact. At layer 21/position 515, routes and weights matched; expert 132 moved CPU→GPU in both configurations, with identical changed row and combined-output capture bytes. The combined MoE output changed in 2,559/2,560 values (relative L2 `0.001528`), and the first changed verifier input is layer 22 (relative L2 `0.0009572`); layer-20 boundary fields are exact. The [independent native-expert oracle](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/operator-oracle-open-response/layer21-expert132/README.md) used the exact same activation and matched initial CPU and recovery GPU service rows bitwise; the oracle CPU/GPU rows differ in all 2,560 values (relative L2 `0.016716`). Across selector settings, all three request token sequences, all 387 accepted-prefix GDN hash records, and layer-21 routes/parts/combined-output captures are identical. Both adaptive traces record expert 132 admitted at position 2138/round 220 (`132 → 87`); neither reproduces the earlier round-88/position-598 decision. This confirms that the open-prompt owner migration and drift are not selector-specific, while limiting the prior selector-associated result to its original prompt/sequence. These are correctness/localization results, not serving-performance measurements.

After the open-response capture, the focused current-build accepted-prefix and graph checks passed 7/7: `published_prefix_test`, `accepted_usage_test`, `accepted_window_test`, `verify_parity`, `spec_verify_parity`, `verify_batch_parity`, and `captured_graph_trace_test` (CTest `-j1`). The GDN verifier parity includes bitwise convolution-history commits for every `T=1..8` and retained prefix `0..T`. These operator/contract tests complement, but do not replace, Phase 5's remaining end-to-end state-transaction, cancellation-boundary, and graph-lifetime gates.

A no-selector [256-token short–short–short held-out chain](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/open-response-short-chain-256pos/README.md) extended the same Coder IQ1_M recovery sequence beyond the prior 128-token cap. Each arm generated 256 tokens for its initial, intermediate and recovery requests. Adaptive recovery differed on 237/256 token IDs, first at index 10; aggregate persistent fingerprints differed at all 256 recovery prefixes, with first per-GDN hash divergence at ordinal 17. Delayed control matched all tokens and state hashes. Both arms passed with 14.14/14.19 GiB minimum host/admission availability and zero cgroup events. This establishes that drift persists over the longer chain but does not bound it; the run collected hashes, not raw all-layer state. Phase 5 remains open for raw-state/operator localization, a measured recovery contract, and remaining API/graph gates.

The current-source [Coder API/cancellation run](../../bench/results/2026-10-22-phase5-coder-api-cancellation-current-source/README.md) passed all seven basic protocol scenarios on Orin: three greedy completions, OpenAI and Anthropic streaming, and cancellation during both decode and prefill. Same-process short recovery returned `Hello Orin!` after each cancellation. This run did not compare persistent-state fingerprints. The current build's `graph_registry_lifecycle_test` also passed, exercising stable-address replay and caller-driven replacement recapture, but not the model graph pool resize path. Minimum host/admission availability during the API campaign was 12.95 GiB with zero sampled cgroup memory events. Phase 5 remains open for raw-state/operator localization and numerical bounds, model graph-pool resize/recapture, and broader state/cancellation contracts.

A same-day [long-chain layer-22 raw-state capture](../../bench/results/2026-10-22-phase5-coder-long-chain-raw-state-pair-pos767/README.md) extends the no-selector held-out short–short–short adaptive sequence to direct numeric state. Raw commits at positions 515, 530 and 640 all cross-check to accepted-prefix GDN ordinal 17. At position 515, initial and recovery token IDs match while adaptive recurrent state differs in 786,405/786,432 values (relative L2 `2.60e-4`) and convolution history differs in 30,719/30,720 (`7.86e-4`). Delayed control is bit-identical at all selected positions. Adaptive state movement therefore precedes the first token-ID mismatch; the operator cause and a general drift bound remain unknown. The harness attempts are retained as failed because the requested final position 767 is not emitted (the final verifier position is 766); the three selected points were fully captured and independently hash-verified in the adaptive and delayed traces. This is bounded selected-position evidence, not a passing four-point campaign. Phase 5 remains open for upstream operation/owner localization and a stated recovery contract; runtime pool resize remains untested, while eviction/recapture is covered at low and default caps.

A [16-token position-515 ownership control](../../bench/results/2026-10-22-phase5-coder-position515-owner-followup-16/README.md) passed in both arms. Adaptive accepted-prefix IDs/state remained exact, and layer 21 had no owner change at position 515; CPU/GPU ownership changed at other layers after adaptation. This short chain does not reproduce the 256-token drift. The completed [256-token owner capture](../../bench/results/2026-10-22-phase5-coder-longchain-owner-capture/README.md) finds layer-21 expert 132 moving CPU→GPU after the initial request while token, MoE input, routes and router weights stay exact. Its verifier row changes in all 2,560 values (relative L2 `0.016716`), shifting combined output in 2,559/2,560 (`0.001528`). The activation is bit-identical to the input already qualified by the independent CPU/GPU expert oracle, and the service rows repeat bit-for-bit. Layer-22 input and committed state then change; the state also changes intermediate→recovery after layer-21 expert-132 output becomes exact, so this is one numerical contributor rather than a complete causal account. Delayed layer-22 state remains exact at the selected positions. Phase 5 remains open for remaining upstream owner/operator transitions, recovery behavior and dynamic graph-pool resize coverage.


A [batch-MTP graph lifecycle diagnostic](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md) on the current Orin build admitted eight Coder IQ1_M requests and captured 16 unique layouts under the 64-layout pool limit. A separate cap-1 stress run exercised 14 LRU evictions and 11 recaptures; an 80-request default-cap stress run exercised 88 layouts, 26 evictions and completed all requests. These cover graph-pool eviction and recapture under both forced low cap and default-cap pressure, without a speed claim. Batch output matched serial MTP2 on 1/8 prompts and serial target-only on 2/8; the latter used a different context/cache profile, so it is only a diagnostic. A same-profile single-live-request follow-up matched serial MTP2 exactly. With two live requests, slot 0 matched and slot 1 first differed at token 60 for both batch-MTP vs serial MTP2 and MTP-disabled batch vs serial target-only. At token 60 the two serial controls select different tokens, and batch-MTP also differs from its same-shape target-only batch control. This narrows the issue to multirow verifier numerics and their interaction with MTP, without locating the responsible logit/state operation. Target-only terminal state fingerprints matched each request's directly computed committed prefix. Batch logs expose handoff fingerprints but no terminal per-slot state, leaving persistent-state parity unknown. Minimum available physical RAM was 14.77 GiB (11.39 GiB at batch admission) for the eight-request test, 16.05 GiB for the single-live follow-up, 16.67 GiB for the two-live MTP test and 17.41 GiB for the two-live target-only test; scoped cgroup memory events including OOM were zero. This is a correctness finding, not performance evidence. Phase 5 remains open for direct per-slot terminal-state capture and localization of the first multirow logit/state difference.

A corrected [delayed target-only layer-12 activation capture](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md) writes STGDIAG5 records with the scheduler's per-row positions, slots and tokens after the graph streams synchronize. Its supervised Coder IQ1_M Orin run captured positions 118–120: position 118 matched serial bit-for-bit, while position 119/token 16 first differed among the captured layer-12 fields at input `x` (2,560/2,560 values, relative L2 0.001664). All 96 slot-0 output tokens still matched. The scheduler averaged 1.00 rows per window, so this is not a multirow numerical reproduction and does not locate the full-model first changed operation. Minimum available and admission RAM were 17.80 GiB, with six-GiB headroom preserved and zero cgroup memory events. CUDA focused graph/parity tests passed 3/3. The current-source maestro1 HIP target rebuilt and linked, with matching source hashes and a successful CLI help check; SYCL reported no build work for the CUDA-only verifier translation unit, and its existing binary passed CLI help. Neither backend had accelerator-runtime coverage. Phase 5 remains open.

A second supervised [two-live target-only capture](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md) covers actual multirow decode windows: 96 windows averaged 1.96 rows. Slot 1 again first differed from its fresh serial control at output token 60. At position 127, the batch and serial rows consumed the same token, but all ten captured layer-12 fields differed; input `x` differed in 2,560/2,560 values (relative L2 `0.06058`, max absolute `0.16310`). A repeat reproduced the token-60 mismatch and bit-identical batch activation arrays at positions 125–127 for both rows. This establishes a repeatable numeric activation delta before the output mismatch, not the first model-wide changed operation or a causal explanation. Minimum available RAM was 17.52/17.53 GiB for the repeat/first run, with zero sampled cgroup memory events. Phase 5 remains open for earlier-operation/logit localization, persistent-state contract coverage, and remaining lifecycle gates.

The [early layer-12 activation and committed-state capture](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md) sampled positions 68–72 in the same two-live target-only workload. Batch slot 0's layer-12 committed state matched its fresh serial control through position 70 and first differed at 71 (796,604/817,152 values; relative L2 `0.003790`); its activation `x` changed at 71 (relative L2 `0.009436`). Slot 1's state already differed at position 68 (796,640/817,152; relative L2 `0.008221`), with changed `x` (relative L2 `0.02354`); that row's onset is before or at the first sampled position. Consumed token IDs matched in all paired rows. The layer-12 activation arrays at overlapping positions repeated bit-for-bit against the activation-only run. This is one layer's committed state and activation evidence, not an all-layer onset or operator cause. Minimum available RAM was 17.49 GiB and zero sampled cgroup memory events were nonzero. Phase 5 remains open.

A six-token [all-layer committed-state capture](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md) provides a separate row mapping from physical slots to fresh serial controls based on all 36 GDN state records. In that run slot 0 maps to prompt 1 and is exact at position 68; its first changed GDN layer at position 71 is model layer 2 (relative L2 `0.000707`). Slot 1 maps to prompt 0 and is already changed at position 68, first at model GDN layer 5; by position 71 its first changed layer is 4. Both six-token outputs match serial. The layer-12 activation deltas align with the mapped states. The short run does not reach token 60, and its physical-slot mapping differs from the longer capture, so it narrows only these selected early boundaries. Minimum available RAM was 17.46 GiB with zero nonzero sampled cgroup event counters. Phase 5 remains open.

A same-day [layer-1 MoE output capture](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md) records shared-expert and combined MoE vectors with per-row slot, position and token identity. In this six-token run, all-layer state comparison mapped slot 0 to prompt 0 and slot 1 to prompt 1. At position 71, slot 1's layer-1 inputs, GDN fields and shared-expert output matched serial, while the combined MoE output changed in 2,560/2,560 values (relative L2 `0.00086265`, max absolute `0.00004228`). The peer row was exact at the selected layer, and every generated token matched its fresh serial control. This points to routed expert output/combination or related per-row state, without identifying a responsible expert or operation. Minimum available RAM was 17.465 GiB; cgroup memory event counters stayed zero. This is diagnostic correctness evidence, not performance qualification. Phase 5 remains open.

A 96-token extension sampled layer 1 at positions 68, 71 and 118–127, with direct layer-1 committed state and MoE outputs captured in the same run. Slot mapping from the matched layer-1 state paired physical slot 0 with prompt 1 and slot 1 with prompt 0. Prompt 1's layer-1 inputs and shared MoE output were exact at position 71, while combined output differed (relative L2 `0.00086265`). By positions 118–127, both requests' layer-1 states, GDN fields, MoE inputs, shared outputs and combined outputs differed. Prompt 1 still first differed in output at token 60. This shows selected early and later boundaries, not a causal link or a named expert. Minimum available RAM was 17.434 GiB with zero nonzero cgroup events; the diagnostic run is not performance evidence. Phase 5 remains open.

A paired [route and expert-parts capture](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md) at layer 1 / position 71 found prompt 1's ten expert IDs and router weights exactly equal to its serial control. Nine expert output vectors were also exact; expert 11 at rank 8 differed in all 2,560 values (relative L2 `0.01336`). Its router weight (`0.051304`) times the expert-11 part delta predicts the combined MoE output change with maximum residual `3.24e-9` and L2 residual `0.00484%` of the observed delta. This isolates the selected output delta to expert 11's output path for this configuration, but does not determine why that output differs or prove it causes the later token-60 mismatch. Both six-token continuations matched serial. Minimum available RAM was 17.643 GiB and sampled cgroup event counters remained zero. This is correctness evidence, not performance qualification; Phase 5 remains open.

A further [dispatch-owner follow-up](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md) maps the layer-1 position-71 batch row to its fresh serial control by exact activation. For prompt 1 / physical slot 1, rank 8 expert 11 changes from primary VRAM in serial to CPU in batch; the captured CPU owner output for dispatch 3601 matches that batch expert part within `5.0e-11` maximum absolute difference, the JSON serialization precision. This ties the selected expert-part delta to a CPU/GPU execution-owner change for this run. It does not explain the kernel-level numerical difference or prove the later token-60 mismatch is caused by this row. Raw owner and CPU-output traces remain local. Phase 5 remains open.


The [expert-11 oracle follow-up](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md) confirms prompt 1's owner-dependent output on the exact activation: serial GPU matches the independent GPU oracle bit-for-bit, and batch CPU matches the CPU oracle bit-for-bit (the CPU/GPU rows differ by relative L2 `0.01335`). For prompt 0, the exact single-token CPU oracle matches both the serial CPU output and batch dispatch 3505 to JSON serialization precision (`5.0e-11`). The earlier reported relative-L2 difference about `2.19` used prompt 1's oracle activation by mistake and is withdrawn. The selected expert-11 pack blob matches the source GGUF byte-for-byte. Prompt 1's CPU/GPU arithmetic difference and the broader state-transition qualification remain open; Phase 5 stays open.

A queue-aware target-only capture reproduced exact layer-10 GDN stages and a layer-12 input difference at committed position 119, token 16. The harness queued its competitor after caller-observed output token 48; engine logs show two in-flight solo tokens completed before `STOP`, so the actual solo prefix was 50 outputs (118 total prompt-plus-output tokens). At layer 12, all 2,560 input values differed (relative L2 `0.00166446`, maximum absolute `0.00342625`); layer 10 and every captured field were bit-identical. Both arms matched 96 serial output tokens, and the peer completed. The interval includes model layer 11 but this does not isolate an operation or establish quality impact. Each supervised run retained at least 17.78 GiB physical availability with zero cgroup events. Details and scripts are in the [batch-MTP diagnostic](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md). The integration unit suite passed 163 tests. Phase 5 remains open.

A paired two-live six-token diagnostic advances the boundary localization. Both
requests matched all 36 serial GDN states at position 68. At position 71, prompt
1's first changed committed GDN state was model layer 2 (796,072/817,152 values,
relative L2 `0.00070708`), while its emitted tokens still matched. In that same
run, layer-1 inputs, route IDs/weights and shared output were exact; rank 8 /
expert 11 alone changed from primary VRAM to CPU and its weighted part delta
explained the combined MoE output to `3.23e-9` maximum residual. A same-input
native oracle matched the serial service part to CUDA and the batch part to CPU
bit-for-bit. The aggregate GDN difference at position 71 was 27,762,032 /
29,417,472 values (relative L2 `0.0231436`). Minimum physical/admission
availability was 17.445 GiB, with zero cgroup events. This is one correctness
diagnostic, not a quality or performance result; Phase 5 remains open.

A 3,000 MiB cache-cap repeat still changed layer-1 expert 11 from primary VRAM
to CPU and reproduced its owner-specific parts with same-input native oracles.
Within that configuration the serial/batch layer-1 activations and routes were
exact, but its activation differed from the 1,500 MiB cell, so the two settings
do not form a same-input numerical comparison. The 3,000 MiB run's first changed
committed GDN state remained model layer 2; 27,085,131/29,417,472 values
differed at position 71 (relative L2 `0.00780748`). This does not show that the
larger cache improves parity. Minimum physical/admission availability was
13.909 GiB, with zero cgroup events. Phase 5 remains open.

A temporary residency-profile intervention promotes layer-1 expert 11 to the
first profile rank (profile SHA256
`8a590044b65ae494e3462067cd76878f3b71ca23519c182ac4660d88c6d9f114`; stored
only under `/tmp`). For prompt 1 / slot 1, the layer-1 MoE parts and combined
output then match the serial control exactly, and the first changed committed
GDN state moves from model layer 2 to layer 4. Layer 2 still has an exact-input
VRAM-to-CPU switch for expert 164; independent native owner oracles match both
service outputs bit-for-bit, with CPU/GPU relative L2 `0.0142044`. This is a
single diagnostic intervention, not a supported profile or performance result.
The row-pairer now rejects owner/verifier route-ID disagreement; valid baseline
and intervention joins pass, while a known cache-3,000 MiB mismatch is
rejected. The capture lacks an explicit owner-row slot, which remains a
limitation. See the [experiment notes](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

A same-profile [two-live layer-4 capture at positions 68 and 71](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/layer4-profile-e11-first-positions68-71/README.md) refines that intervention. Prompt 1 / slot 1 already differs from serial at position 68, first at GDN layer 5; at position 71 its first changed state is layer 4, where the activation and router weights also differ, so that expert output is not attributable. Prompt 0 / slot 0 is state-exact at position 68 and first differs at layer 6 by position 71, even though its layer-4 input, all expert parts and combined output are exact. The supervisor retained 17.44 GiB minimum host/admission availability with zero sampled cgroup events. This identifies distinct row histories, not the operation responsible for either state delta; multi-live qualification remains open.

A same-service current-source [layer-27 owner-transition capture](../../bench/results/2026-10-22-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer27-current-source-generated-position515/README.md) exercised expert 129 changing CPU→CUDA on the third identical request at generated position 515 (`Q8_1_DOT=all`). The verifier activation, route, expert part, shared/combined MoE outputs and generated IDs were exact across repetitions; all 36 committed GDN states were byte-identical across both arms. Minimum physical/admission availability was 13.78 GiB. This narrowly does not reproduce the historical expert-175 report, and does not establish general owner parity or close Phase 5.

A same-profile [expert-248 owner-pair follow-up](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/layer4-expert248-q8-all-owner-pair/README.md) isolates one exact-input layer-4 row at position 68. In the default-selector two-live capture, prompt 1's rank-4 expert 248 changes CPU→CUDA; its input activation, route IDs and router weights match serial. Expert 248 is the only changed part, the shared output is exact, and the combined output differs at relative L2 `0.0028174`. With the independent oracle on that same activation, CPU/GPU outputs differed at relative L2 `0.0113`; `STRATA_NATIVE_CPU_Q8_1_DOT=all` made the isolated outputs bitwise equal. In a separate Q8_1-all two-live capture, prompt 0 has an exact-input rank-1 CPU→CUDA transition for expert 248 and all parts plus combined output are exact. Prompt 1 committed state is bitwise exact at positions 68 and 71; prompt 0 first differs only at layer 30 / position 71, with relative L2 `5.84e-9` and maximum absolute delta `1.27e-7`. Selector cells have different route histories, so they are not a controlled whole-model comparison. One six-token sequence per cell is correctness localization, not performance or quality evidence; Phase 5 remains open.

An opt-in layer-21 IQ3_S/Q2_0 CPU Q8_1 selector now matches CUDA expert output
bit-for-bit on both the captured initial and intermediate real activations.
However, a paired 256-token adaptive-cap8 versus delayed-control chain still
changed recovery on 254/256 tokens and changed accepted persistent-state
fingerprints. The first two adaptive requests had the same token and top-10
expert IDs at layer 21/position 515, but their 2,560-value layer input vectors
already differed (relative L2 0.02186), as did router weights and committed
layer-22 state. The selected expert arithmetic mismatch is not sufficient to
explain the recovery drift; the first upstream source remains unknown. This is a
narrow, opt-in correctness diagnostic with no performance conclusion; Phase 5
remains open. See the [intervention report](../../bench/results/2026-10-22-phase5-coder-iq3s-q2_0-layer21-parity-intervention/README.md).

A separate two-live target-only diagnostic with `STRATA_NATIVE_CPU_Q8_1_DOT=all`
and a temporary expert-11-first residency profile matched both six-token serial
outputs. At position 68, expert 248 changed primary-VRAM→CPU ownership on an
identical activation and route, yet all expert parts and combined output were
bit-identical. Both prompts also had exact MoE outputs at position 71. One slot's
committed GDN state first differed at model layer 30 there, at relative L2
`5.84e-9` and max absolute `1.27e-7`; the other slot remained exact. This is a
bounded owner-parity result, not a general long-chain or quality bound. Phase 5
remains open. See the [Q8_1 owner report](../../bench/results/2026-10-22-phase5-coder-e11-first-q8all-two-live/README.md).

The new IQ3_S/Q2_0 Q8_1 selector was rebuilt against matching source hashes on maestro1. HIP rebuilt and linked `strata` and `native_expert_parity`; the selector-contract diagnostic and HIP `strata --help` passed. SYCL rebuilt and linked `strata` (20/20 steps), and its `--help` passed after loading the oneAPI runtime. These are x86 compile/startup and CPU-contract checks only, with no accelerator or model execution. See the [backend build record](../../bench/results/2026-10-23-phase5-maestro1-iq3s-q2-selector/README.md).

A retrospective [named-rail energy analysis](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/rail-followup/README.md) integrated tegrastats over all 28 passing measured request windows in the seven-block Coder cache × context confirmation. The median `VIN_SYS_5V0` rail estimate per output token fell 7.42% at 8K (paired block-bootstrap 95% interval 6.88%–11.41% lower) and 7.05% at 16K (6.61%–7.15% lower) with the 3,000 vs 1,500 MiB requested cache. Its cache-by-context ratio-of-ratios was +0.39% (+0.29% to +4.85%). The separately integrated `VDD_GPU_SOC` and `VDD_CPU_CV` rails are also reported. These named rails include idle/background activity, are not process-attributed and are not summed or called whole-device energy; Phase 6 remains open for broader Pareto and energy scope.
