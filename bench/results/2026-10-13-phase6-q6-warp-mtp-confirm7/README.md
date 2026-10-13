# Q6 warp × MTP seven-block confirmation and accepted-state investigation

This Orin AGX campaign extends the 2026-10-12 three-block Q6_K warp-dequant ×
MTP screen with seven randomized paired blocks on a held-out 2,048-token
incident-log prompt, 128 generated tokens and 8K context. It used the current
IQ1_M Flash-Next pack, the same-day candidate binary recorded in each result,
3,903 cache slots, fresh services, default MTP batching, read-only clocks and a
28 GiB systemd scope. The six-GiB host headroom and separate 3 GiB workspace
reserve remained in force. Raw per-cell data, capabilities, logs, workload and
schedule are under `run/`.

All 28 cells (four conditions × seven blocks) passed request-length, fresh
prefill, cache-slot and resource gates. Within each fixed MTP regime, warp
dequantization improved median total request time by 7.253% with MTP disabled
(paired bootstrap 95% interval −7.951% to −5.783%) and 6.148% with MTP window 4
(−7.442% to −4.827%). The request interaction estimate was +1.148%
(−0.204% to +2.313%). Every baseline/warp output pair matched exactly at fixed
MTP. These are timing results for this prompt and hardware only.

The two MTP regimes did not produce the same generated output in any block:
their output SHA prefixes were `7b7cd547444e` (MTP off) and `ec417a6f0a71`
(window 4). Therefore the factorial timing comparison does not qualify a joint
MTP/warp profile or support changing defaults. MTP offered 153 drafts and
accepted 79 in each window-4 cell.

To localize the mismatch, a direct API harness captured published IDs and
accepted-prefix state for 32 tokens from the identical prompt with MTP off and
windows 2/3/4. The same harness was repeated with default batching after an
initial run with explicit batch size 1; the window-4 divergence reproduced
unchanged. The default-batch window sweep results are in
`run/incident-window-sweep/results.json`. MTP windows 2/3/4 first had unequal
state at shared committed prefixes 5/7/8 respectively, while all three first
changed a published token at index 13. The mismatching state fields included
GDN and KV, with other main-state hashes diverging as the request continued.
The no-MTP and window-4 GDN dumps at prompt+8 were numerically compared before
discarding the 113 MiB dumps: 94.443% of float elements differed, global
relative L2 was 0.01908 and global RMS absolute delta was 0.00514. This is a
material accepted-prefix discrepancy, not merely a hash-format difference.

The sweep ran under the 28 GiB scope and retained at least 13.41 GiB whole-host
availability; minimum effective availability was 9.94 GiB. No OOM event
occurred. EMC frequency was inaccessible; CPU/GPU rates were sampled without
changing clocks. Energy is not process-attributed. State tracing can perturb
runtime timing, so no timings are taken from that harness.

Two diagnostic controls narrow the failure. First, repeating off/window 4 with
`STRATA_GDN_COMMIT_SPLIT=0` (the ordinary multi-row GDN commit kernel) produced
the same first output mismatch at token index 13 and the same shared-prefix
state mismatch at prefix 8. Its GDN dump comparison also had exactly 27,782,662
different floats (94.443%), relative L2 0.01908 and RMS absolute delta 0.00514;
the first differing layer was layer 2. The optimized split commit kernel is
therefore not the sole cause. Second, a 512-token suffix of the same formatted prompt also
diverged: state first differed at shared prefix 5 and output IDs at index 10.
This argues against a failure unique to 2K prefill length, but the suffix is a
diagnostic token shape, not a standalone quality prompt. These results are
retained under `run/incident-state-unsplit-commit*` and
`run/incident-state-short-context*`.

The existing CUDA `gdn_parity --selftest` also passes: the multi-token GDN
recurrence is bitwise equal to repeated single-token recurrence in 84 synthetic
cases, and accepted-prefix convolution history matches in 44 cases. That
supports the kernel-level recurrence contract for its fixtures but does not
exercise activations from this production model's multi-token verification
path. The mismatch therefore still needs a live activation/intermediate-level
comparison; no numerical tolerance or code workaround is adopted yet.

This is a workload-specific Phase 5 correctness failure that reopens the MTP
accepted-prefix gate for the 2,048-token incident workload. It does not negate
the separately passing short-prompt or other long-prompt transaction tests.
Investigate verifier commit arithmetic/state replay before using MTP results as
quality-qualified Phase 6 candidates. Warp-dequant remains opt-in; no MTP
window or combined profile is promoted. No model, build output, credential or
113 MiB state dump is stored in Git.

To reproduce the seven-block timing screen, use `factorial_screen.py` with the
four saved configs and `schedule.json`; its outputs and analyzer result are
retained under `run/`. The direct trace commands are the Python harnesses
`compare_incident_state.py` (off/window 4, repeated with default batching) and
`compare_incident_windows.py` (off/windows 2/3/4). State-trace and supervisor
records are retained under `run/incident-state-*` and
`run/incident-window-sweep*`.

## Layer-input localization follow-up

The later layer-input capture repeats the exact 512-token suffix with the same
current engine, fixed 32-token generation limit, and fresh no-MTP/window-4
services. The accepted-prefix trace again first differs at generated prefix 5;
the output first differs at token index 10. Window 4 offered 42 drafts and
accepted 18. Both requests completed without OOM events under the 28-GiB
supervisor; minimum host and effective admission availability were 13.21 GiB.
The comparison is correctness-only because capture/state tracing synchronizes
GPU work.

At the selected GDN capture points, absolute layer 2 (the third model layer,
GDN ordinal 2) first differs at position 515/token 3766. Its pre-GDN mixed
activation differs in all 2,560 values (relative L2 0.002102, maximum absolute
delta 0.004664); QKV, convolution input, gate, beta, z, and recurrent output
also differ. Absolute layer 1 (the second model layer, GDN ordinal 1) remains
bitwise equal at shared captured positions through 519; its first difference
is at position 520/token 11040 (all 2,560 mixed-activation values, relative L2
0.002666, maximum absolute delta 0.006456). This brackets the first observed
activation discrepancy between the layer-1 GDN capture and layer-2 GDN input
for the shared row at position 515. Later captures below separate more of the
operations along this path; no workaround or tolerance is adopted.

The capture format is opt-in (`STRATA_VERIFY_DUMP_GDN_LAYER` plus
`STRATA_VERIFY_DUMP_GDN_PATH`) and records bounded verifier rows in binary
`STGDIAG1` through `STGDIAG4` streams. The current v4 stream captures GDN
input/intermediate values, post-GDN projection, FFN input, and combined FFN
output. `analyze_gdn_diag.py` compares appended capture streams by position and
token. Persistent-state hashes remain authoritative for state parity. Large raw
float32 dumps were removed after extracting compact per-field summaries; logs
and supervisor telemetry remain. The CUDA binary passed the focused 10-test
verifier/GDN/speculation/PLE/graph regression. On maestro1, the exact updated
`src/core/verify.cpp` and header were copied into the isolated validation tree.
The [maestro1 build record](MAESTRO1_DIAGNOSTIC_BUILD.md) lists their hashes and
scope. The HIP-configured Release build compiled the updated
`strata_engine/src/core/verify.cpp.o` (331,392 bytes); a focused Ninja target
recheck reported no work. The full HIP application build was stopped while
compiling unrelated llama.cpp MMQ kernels, before the `strata_engine` archive
and application link, so no full HIP build is claimed. The separate SYCL
`strata` target reported no work; its independent `sycl/src/core/verify.cpp`
and `sycl/include/strata/core/verify.hpp` were unchanged. Neither x86 check
claims accelerator runtime behavior.

As a follow-up control, the same suffix and output limit were repeated with
`STRATA_DEC_BATCH=0`. MTP still offered/accepted 42/18 drafts; accepted-prefix
state first differed at prefix 5 and token IDs at index 10, exactly as with the
default batch setting. The layer-1 capture likewise first differed at
position 520/token 11040 with the same x relative-L2 delta (0.002666) and max
absolute delta (0.006456). This rules out the broad decode-batching switch as
the sole trigger for this failure, though it does not isolate every operation
that still processes a verifier window. The supervisor recorded 13.24 GiB
minimum host/effective availability and zero OOM kills. The run is
correctness-only; its retained results and telemetry are under
`run/incident-no-decode-batch*`.

The v4 capture adds the operations between the layer-1 and layer-2 GDN captures.
At position 515/token 3766, layer-1's GDN projection and following FFN input
still match bitwise, but the combined layer-1 FFN output differs in all 2,560
values (relative L2 0.004423, maximum absolute delta 0.000192). The layer-2
GDN input differs at that same position. This places the first observed
activation discrepancy in the layer-1 MoE execution/combination or its final
combine seam, before layer-2 attention; it does not identify which expert or
prove whether CPU/GPU rounding, route selection, or swap timing is responsible.

A paired control with `--adapt-swaps 0` removed the discrepancy on this exact
suffix. MTP off and window 4 then matched all generated token IDs, final state,
all shared accepted-prefix hashes, and every common captured layer-1 activation;
window 4 offered/accepted 45/17 drafts. The 28-GiB supervisor retained 13.248
GiB minimum host/effective availability with no OOM kills. Combined with the
default-swap repeat, this strongly implicates adaptive expert residency in the
failure on this prompt/configuration. It does not prove a bad expert copy or
generalize to other prompts, caches, or output profiles. No adaptation or MTP
default changed.

A second control kept adaptive tracking enabled but set `--adapt-every 100000`,
placing the swap interval well beyond this 32-token output. It also matched all
token IDs, final state, shared accepted-prefix hashes, and common captured
activations, with 45/17 drafts offered/accepted and 13.126 GiB minimum
host/effective availability. This corroborates that executing swaps, rather
than merely enabling tracking, triggers the observed difference in this
configuration. The default-swap, no-swap, and delayed-swap activation summaries
are in
`run/incident-gdn-ffn-output/activation-comparison.json` and
`run/incident-no-adapt/activation-comparison.json`, and
`run/incident-delayed-adapt/activation-comparison.json`; raw float tensors were
discarded.

## Full incident prompt delayed-swap control

To test whether the delayed-swap control extended beyond the 512-token suffix,
the original formatted 2,048-token incident prompt was run with fresh no-MTP and
window-4 services, 32 generated tokens, CPU prefill sharing disabled, and
`--adapt-every 100000`. The two outputs matched exactly. All 14 shared accepted
commit boundaries matched all recorded persistent-state hashes, and final main
state matched. Window 4 offered 39 drafts and accepted 21. In the second
independent run, all 38 shared layer-1 activation capture rows were bitwise
equal. This is one prompt, one output length, and one delayed-swap setting; it
does not qualify the default swap schedule or establish a general remedy.

The first run's state/output record and the repeated numeric activation result
are under `run/incident-delayed-adapt-2048/` and
`run/incident-delayed-adapt-2048-repeat2/`; supervisor telemetry is retained in
the corresponding `*-supervisor/` directories. Minimum host availability in
the first run was 13.45 GiB and minimum effective admission availability was
12.58 GiB; the repeat remained above the six-GiB floor. There were no OOM
kills. Raw activation tensors were removed after confirming bitwise equality.
The comparison harness is `compare_delayed_adapt_incident_prompt.py`; pass it
an unused output directory as its argument when reproducing the run.

## Adaptive-round localization and cadence probe

The opt-in server diagnostic `STRATA_TRACE_ADAPT=1` records the absolute
verifier position and round where a swap is scheduled, becomes pending, and is
applied. It also records the selected `(layer, incoming expert, outgoing
expert)` tuples. The new default-schedule comparison reproduced the incident:
MTP off and window 4 first differed in accepted state at the 8-token prefix and
in published output at token index 13. Layer 1's FFN output first differed at
position 2,051/token 3766 (all 2,560 values; relative L2 `0.004534`, max
absolute difference `0.000226`).

The first adaptive round ran at different absolute positions under the default
cadence of four verifier windows. MTP off scheduled round 4 at position 2,050,
queued 96 swaps after the commit to 2,051, then applied them before verifying
position 2,051. Window 4 scheduled its round 4 at position 2,055, queued swaps
after the commit to 2,056, and applied them before position 2,056. Thus the
first observed layer-1 activation difference occurs after the no-MTP route has
changed residency and before the MTP route has.

An opt-in cadence probe used `--adapt-every 4` for MTP off and `--adapt-every 2`
for window 4. This aligned the first apply boundary at position 2,051 and kept
all 32 published token IDs equal, but accepted state still diverged at prefix
8. At the aligned first swap, only 71 of the 96 `(layer,incoming,outgoing)`
choices matched (Jaccard `0.587`); at the next corresponding epoch, only 10 of
96 matched (Jaccard `0.055`). Layer 1's first-round choices differed as well.
The first activation difference remained at position 2,051/token 3766 (all
2,560 values; relative L2 `0.002788`, max absolute difference `0.000147`).
Changing the window-count cadence alone therefore does not restore persistent
state. The captured layer-1 router IDs are equal for the first four generated
positions, then differ at the position where the FFN activation first diverges.
Because route IDs themselves are downstream of changed activations, this does not
isolate whether the residency choices or speculative usage totals initiate the
difference. The routing trace was summarized with SHA-256 identities and the raw
tensor/binary captures were removed; see `run/adapt-cadence4-vs2-routing/`.

The evidence points to both the swap epoch and the expert set being sensitive
to MTP windows. The serving verifier adds all `n_tok*k` routed entries to the
adaptive usage totals before accepted-prefix length is known; rejected draft
rows therefore contribute to the next choice. This code-path explanation is
consistent with the measured choice differences, but an accepted-row-only
adaptive policy has not yet been implemented or qualified. No default or
adaptation setting was changed. Raw layer tensors were removed after analysis;
compact activation and swap-choice comparisons, routing summaries and event logs, and
supervisor telemetry are retained under `run/incident-default-adapt-2048-traced-v2*`,
`run/adapt-cadence4-vs2-choices*`, and `run/adapt-cadence4-vs2-routing*`.

The server-loop trace implementation is opt-in and changes no swap or dispatch
decision. Its CUDA focused CTest selection passed 10/10 and `strata --help`
passed. The HIP-configured GNU C++ translation unit also compiled on maestro1;
see [backend compile scope](MAESTRO1_ADAPT_TRACE_BUILD.md). No SYCL source was
changed because its program entry point is maintained separately.

## Accepted-row, accepted-token adaptive candidate

The first opt-in candidate stages routed-expert counts per verifier row, commits
only counts for rows that produce the successfully committed output prefix, and
schedules adaptive swaps by published-token count. A verifier window is shortened
when its maximum prefix would cross the next adaptive boundary. This keeps a
speculative window from using one residency set across a boundary that the MTP-off
control would observe between single-token windows. The option is limited to
blocking, single-request, single-GPU serve without suffix/lookup chaining; the
default adaptive path is unchanged.

For this Q2_0 shape, the per-window staging vector requests up to 196,608 bytes
(48 layers × 256 experts × 4 verifier rows × 4 bytes) and is reused by the
server's `Drive` object. This is a host heap request, not a separately measured
physical backing delta.

The first accepted-row-only trial without a window cap still diverged from
MTP-off at output token 13, with state first differing at prefix 13. The final
boundary-capped candidate was then run twice on the same 2,048-token incident
prompt for 32 outputs. In both pairs, MTP-off and MTP window 4 matched all 32
token IDs, final state and every one of 17 shared accepted-prefix fingerprints.
The Q2_0 MTP arm offered/accepted 31/15 drafts. Its first two 96-swap choices
matched the MTP-off choices, and both arms queued them at positions 2,051 and
2,055. The uncapped trial's failures and the paired run records are retained in
`run/accepted-usage-*`, `run/accepted-token-cadence-*`, and
`run/accepted-boundary-*`; a compact index is
[`accepted-usage-comparison.json`](accepted-usage-comparison.json).

Across the two boundary-capped pairs, minimum host availability was 13.34 GiB;
minimum effective availability was 13.13 GiB in the first pair and 13.34 GiB in
the repeat. Both remained above the six-GiB guard. MTP-off output and final state
also matched the earlier default-adaptation controls. These are correctness-only
runs with state tracing, not performance measurements. This does not qualify MTP
or the adaptive candidate beyond this prompt, cache, format and output length,
and it does not close the Phase 5 matrix. No default changed.

The current candidate build passed the 15-test Phase 3 memory/owner/PLE CTest
selection and the 124-test integration Python suite. A second CTest run of the
same selection also passed after the final boundary cap was added. HIP
translation units for `generate.cpp` and `expert_source.cpp` compiled and the
full `strata` target linked on maestro1 after syncing the stale remote
`session.cpp`; see [backend build scope](MAESTRO1_ACCEPTED_USAGE_BUILD.md). No
HIP runtime or SYCL build/runtime is claimed.

## Accepted-only verifier-window matrix

The boundary-capped candidate was compared before the request-lifetime fix below
on the same 2,048-token prompt
for 32 outputs with MTP off and windows 2, 3, and 4. All three MTP arms matched
all 32 published token IDs, final main state, and every state fingerprint at
shared accepted-prefix boundaries. The comparisons had 22, 20, and 17 shared
boundaries respectively. Drafts offered/accepted were 16/10, 24/12, and 31/15.
The 28-GiB supervisor passed with a six-GiB floor, a 13.37-GiB minimum host
availability, and no OOM events. Clocks remained dynamic; EMC sampling was
denied and energy was not measured. This extends correctness evidence across
the planned MTP windows for this prompt and runtime configuration, not across
other prompts, KV formats, termination paths, or performance/quality behavior.
The direct JSON contains all four traces and the cross-window comparisons;
the supervisor record contains host/cgroup/clock telemetry.

After the staging-lifetime correction, the four-arm comparison was repeated on
binary SHA256
`2403c73bfde5b942022266e1f77502e7b53b418a7d700c5bf5cd5a3826989b77`. The same
three exact output/state comparisons passed, with a 13.56-GiB minimum host
availability. Post-fix traces and supervisor telemetry are in
`run/accepted-window-matrix-fixed/` and
`run/accepted-window-matrix-fixed-supervisor/`.

The same rebuilt candidate was also checked on a distinct 2,048-token watershed
incident-analysis prompt at a 16K context reservation, again with 32 output
tokens and MTP off/windows 2/3/4. All three MTP arms matched every output token
and all shared accepted-prefix state checkpoints (21, 16, and 12 boundaries);
draft offered/accepted counts were 15/11, 22/16, and 29/20. The 28-GiB
supervisor passed with a 13.19-GiB minimum host availability and no OOM events.
This adds one held-out prompt/context correctness cell, not an independent
performance or task-quality result. The source workload is the retained
`2026-10-11-phase4-q6-warp-context16k-confirm7/workloads.json`; direct traces and
telemetry are in `run/accepted-window-heldout16k/` and
`run/accepted-window-heldout16k-supervisor/`.

## Q2_0 pack parity check

To cover the second local model configuration, the same four-arm matrix ran on
the 512-token prompt retained by the Q6 warp screen, using the Q2_0 pack and
native experts, FP16 KV, 3,000 expert-cache slots, and a 64K context reservation.
With 32 output tokens, windows 2/3/4 matched MTP-off token IDs and every shared
accepted-prefix state checkpoint (21, 19, and 17 boundaries). Draft
offered/accepted counts were 16/11, 24/13, and 31/15. The supervisor passed
with a 15.25-GiB minimum host availability and no OOM events. This is a
correctness-only Q2_0 cell, not quality or performance qualification.

The initial launch was rejected by the opt-in's explicit compatibility check
because the reused Q2_0 configuration enabled suffix drafting. It did not enter
model execution and is retained as a failed setup cell under
`run/accepted-window-q2-supervisor/`; the measured rerun explicitly set
`--suffix-draft 0` and is recorded under `run/accepted-window-q2-fixed/` and
`run/accepted-window-q2-fixed-supervisor/`.

The same 512-token prompt and Q2_0 model were then screened at 16 generated
tokens under INT8, Q4_0, and K8V4 KV. For each format, MTP windows 2/3/4
matched every output ID and every shared accepted-prefix checkpoint (11 shared
boundaries per arm). Draft offered/accepted counts were 8/5, 14/5, and 17/5
in each format. All 28-GiB supervisor runs passed without OOM events; minimum
host availability was 16.05 GiB (INT8), 16.49 GiB (Q4_0), and 16.30 GiB
(K8V4). Together with the 32-token FP16 run above, this completes the
accepted-only candidate's short-prompt parity screen across the four currently
supported KV formats on Q2_0. It does not cover a long prompt under each KV
format, task quality, or runtime performance. Raw comparisons and telemetry are
under `run/accepted-window-q2-{int8,q4_0,k8v4}*`.

The Q2_0 screen was then repeated on the distinct 2,048-token watershed prompt
at a 64K context reservation. FP16 KV used 32 output tokens; INT8, Q4_0, and
K8V4 used 16 each. For all four KV formats, windows 2/3/4 exactly matched
MTP-off output and every shared accepted-prefix state. Shared boundary counts
were 20/16/15 for FP16, 10/8/8 for INT8, 10/8/8 for Q4_0, and 12/10/10 for
K8V4. Every MTP arm offered and accepted drafts. The supervised runs passed
with minimum host availability 15.48, 16.23, 16.62, and 16.46 GiB respectively;
no OOM event occurred. This completes the correctness-only long-prompt × KV ×
MTP-window screen for these Q2_0 artifacts and cache setting. It does not
qualify quality or performance. Traces and telemetry are under
`run/accepted-window-q2-long-{fp16,int8,q4_0,k8v4}*`.

## Cancellation and same-service recovery

Enabling the candidate exposed a request-lifetime bug that the completed-request
matrix could not see. A streamed integer-list request canceled after one visible
delta committed four tokens, then the same service returned HTTP 400 on recovery:
the prior verifier's row-staging vector remained set to its old window size.
The accepted usage is now accumulated at commit and the staging vector is
cleared immediately afterward. This keeps staging scoped to one verifier
transaction. The first failing run is retained in
`run/accepted-cancel-recovery/`.

After rebuilding, the same test passed: one visible delta, four committed
tokens, exact state parity at `L=48` and `L=51` against two fresh references,
repeatable reference outputs, and same-service recovery returned exactly
`Hello Orin!`. The 28-GiB supervisor retained 13.22 GiB minimum host
availability, above the six-GiB floor, with no OOM events. This is one short
stream-cancellation cell with a 3,000-slot cache and MTP4; it does not qualify
long-prefill cancellation or other termination shapes. The failure, corrected
run, reference traces, and telemetry are retained under
`run/accepted-cancel-recovery*`.

After the fix, the selected CUDA memory/owner/PLE regression passed 15/15 and
the integration Python suite passed 124/124. The accepted-window matrix was
repeated on the same rebuilt binary. The fixed candidate's source SHA256, HIP
build evidence, and artifact hashes are appended to
`MAESTRO1_ACCEPTED_USAGE_BUILD.md`.
