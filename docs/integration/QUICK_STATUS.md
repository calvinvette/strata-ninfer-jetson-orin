# Quick status

Updated: 2026-10-23

This is a short orientation to the integration. The [plan](PLAN.md) defines
phase gates; the detailed [status](STATUS.md) is the evidence record, and the
[measurement protocol](BENCHMARKS.md) defines how to interpret results. The
[porting notes](PORTING_NOTES.md) preserve lessons for repeating this work with
Strata and Splash.

## Overall status

Phases 0–4 are complete for their documented scopes. Phase 7 is complete for
its bounded Orin qualification matrix. Phase 8 is complete for one bounded,
opt-in Q2_0 release profile; Phases 5 and 6 remain open for unresolved
accepted-state correctness and broader performance interactions. The latest
Orin CUDA regression suite passed 130 tests with two
optional IQ-fixture tests skipped; integration Python discovery passed 163/163,
and focused accepted-prefix, verifier, batch and graph tests passed. The latest
seven shared-source files were rebuilt from a fresh isolated snapshot for HIP
and SYCL on maestro1 with two jobs; both `strata --help` checks returned zero.
This is x86 compile/link and CLI-startup evidence only, not accelerator runtime
or Orin performance evidence. Build/source hashes are in the linked backend
record in [STATUS](STATUS.md). See the [Phase 8 closeout](PHASE8_CLOSEOUT.md)
for the exact release scope and exclusions.

## Performance observed

A current-source owner-transition diagnostic at layer 27 / generated position
515 found exact selected expert output and all-layer committed GDN state across
an adaptive CPU-to-CUDA owner change for expert 129. This is narrow correctness
evidence only; it does not close Phase 5 or establish broad owner parity. See
the [capture notes](../../bench/results/2026-10-22-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer27-current-source-generated-position515/README.md).

A current-binary Coder IQ1_M adaptive/delayed pair reproduced cross-configuration
state divergence at accepted position 532; 64-token recovery stayed exact within
each service. A focused capture found CPU/GPU ownership differences before the
first changed MoE input activation (layer 36 at short position 532; layer 41 at
long position 2067), while all long-request output tokens still matched. This
is localization evidence, not a causal or performance result. Phase 5 remains
open. [Report](../../bench/results/2026-10-23-phase5-coder-adaptive-divergence-532-2067/README.md).

These results are specific to the tested Orin build, model and workload. No
candidate setting has been promoted to a default.

| Experiment | Measured result | Scope |
| --- | --- | --- |
| Expert cache × context, Coder IQ1_M, held-out 7,501-token task, seven same-day blocks | 3,000 vs 1,500 MiB requested cache reduced median client latency 7.95% at 8K context (paired 95% interval 7.93%–15.11%) and 7.71% at 16K (7.23%–7.82%). Cache-by-context interaction was +1.12% (0.22%–8.58%). | MTP off, FP16 KV, exact 48-token answer; one long-task profile. [Report](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/README.md) |
| Expert cache, short Coder task, seven blocks | 3,000 vs 1,500 MiB reduced median client latency 12.83%; TTFT fell 13.47%, with prompt/decode throughput up 15.77%/10.24%. | Short task only; see [STATUS](STATUS.md). |
| MTP × prompt length × KV, Coder IQ1_M, seven blocks / 56 arms | On the 7,501-token task, MTP4 reduced decode throughput 9.17% with FP16 KV and 9.24% with INT8; client time rose 0.59% and 1.01%. Short-task effects were smaller and uncertain. | MTP4 was dominated on measured long-task latency and named-rail energy; no default changed. Other Phase 6 factors remain open. [Report](../../bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/README.md) |
| Prefill chunk × expert cache, Q2_0 near-limit retrieval, seven held-out blocks | Chunk 128 reduced median request time 59.54% at 3,000 slots and 59.74% at 3,500 slots; all 28 requests returned the exact 41-token answer after 7,506 prompt tokens. | Cache × chunk interaction interval included zero; no general default. [Report](../../bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/README.md) |

The [batch-MTP graph lifecycle diagnostic](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md)
admitted eight slots and captured 16 layouts under the default 64-layout cap,
so that initial run did not exercise eviction. A separate opt-in cap-1 test
completed eight concurrent requests and observed 14 LRU evictions and 11
recaptures across four repeated layout keys; all requests returned six tokens,
with 16.50 GiB minimum available RAM and zero cgroup memory events. The default
cap remains 64, confirmed by a no-override run whose six-token single-request
output matched serial MTP2. A supervised 80-request stress exercised 88 unique
layouts: the first eviction came at layout 64, and 26 evictions occurred in
total. All requests completed, minimum host availability was 11.12 GiB, and
784 supervisor samples showed zero cgroup pressure or OOM events. This is
lifecycle and memory evidence only, not a correctness or speed result. Outputs
in the original eight-prompt batch differed from
serial controls; a same-profile single-live follow-up matched serial MTP2,
while a two-request run still diverges at token 60 on slot 1 for MTP-enabled
and MTP-disabled batches. Full state capture corrected the earlier layer-6
pairing: at positions 71–72, each batch slot is closest to its corresponding
isolated serial prompt, but state arrays differ broadly despite equal short
outputs. At position 127, all 248,320 verifier logits differ and the top-two
ranking reverses. Batch-MTP remains unqualified; no throughput claim is made.

A new position-76 MTP2 comparison pairs rows by generated token. Prompt 0's
committed GDN state differs from its serial control in 26,965,859/29,417,472
values (relative L2 0.01823), first at model layer 4, despite an identical
64-token output. Prompt 1 did not produce a captured commit at that position.
The batch QSA hash hook stopped at state length 69, so it cannot rule out an
earlier QSA difference. This narrows the observed state onset for one row but
does not explain the two-live output mismatch or pass Phase 5. See the [state
follow-up](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

A 3,000 MiB cache-cap correctness diagnostic is now localized one layer
earlier: layer-10 experts 150 and 2 switch from VRAM to CPU on an otherwise
bit-identical activation and routing row. Independent same-input oracles
confirm the owner-specific outputs. The later layer-11 observation was
downstream of this change, so it is not a cache-only performance comparison.
Phase 5 remains open.

The current candidate also passed a 2026-10-22 bounded Phase 8 smoke: 7,498-token
8K-context retrieval plus same-service recovery, 130 CUDA CTests passed with two
optional fixture skips, and Python integration passed 163/163. This is
functional regression evidence, not a new timing confirmation. [Report](../../bench/results/2026-10-22-phase8-current-source-q2-profile-smoke/README.md).

A separate current-source MTP2 cancellation test matched all five committed
prefixes against two fresh references and recovered on the same service after
the client closed its stream. It strengthens one cancellation boundary set;
adaptive accepted-state drift and the two-live batch mismatch remain open.
[Report](../../bench/results/2026-10-22-phase5-coder-mtp2-cancel-state/README.md).

Direct raw GDN captures from a 256-token adaptive chain confirm state drift
before the first recovery-token mismatch: at position 515, 786,405 recurrent
values and 30,719 convolution values differ, while delayed control stays
bit-exact through positions 515, 530 and 640. Each raw record matches the
accepted-prefix service hash. Phase 5 remains open. [Report](../../bench/results/2026-10-22-phase5-coder-long-chain-raw-state-pair-pos767/README.md).

A separate two-live trace now connects one owner switch to persistent state:
at position 71, layer-1 expert 11 moves VRAM→CPU on an exact-matched activation,
and the first changed committed GDN state is model layer 2. Its weighted part
delta explains the combined MoE output to `3.23e-9` maximum residual; exact
CUDA/CPU owner oracles pass. Both requests still match their six output tokens.
At position 68, all 36 GDN states were bit-identical. This is a single short
correctness trace; Phase 5 remains open. [Details](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

A 3,000 MiB repeat still moves layer-1 expert 11 VRAM→CPU and changes the first
committed GDN state at layer 2. Its activation differs from the 1,500 MiB cell,
so the aggregate state delta cannot be used as a cache-size comparison. The
larger cap did not prevent the selected owner switch; Phase 5 remains open.

Correctness work has found a separate adaptive-recovery issue. In a 256-token
short–short–short Coder IQ1_M chain, adaptive recovery differed on 237/256
tokens, while delayed control was bit-exact at captured positions. At position
515, layer-21 expert 132 changes CPU→GPU ownership on the same input and route;
its owner-specific service rows match an independent oracle, but the CPU/GPU
rows differ in all 2,560 values (relative L2 0.016716). This explains one
contribution, not all later persistent-state drift. Current-source Coder MTP4
decode cancellation matched all 11 state fingerprints at four accepted-prefix
boundaries; early-prefill cancellation also matched all 11 recovery state
fingerprints. These qualify the tested points, not every cancellation boundary
or adaptive recovery. Opt-in cap-1 and default cap-64 batch graph
eviction/recapture now pass lifecycle stress coverage.
See the [owner transition](../../bench/results/2026-10-22-phase5-coder-longchain-owner-capture/README.md),
[raw state](../../bench/results/2026-10-22-phase5-coder-long-chain-raw-state-pair-pos767/README.md),
and [API cancellation](../../bench/results/2026-10-22-phase5-coder-api-cancellation-current-source/README.md)
records.

An MTP2 cancellation run also passed at five accepted-prefix lengths. Both
fresh exact-length controls matched every committed token and state
fingerprint; the canceled service returned `Hello Orin!` on recovery. Minimum
host/admission availability was 13.18/12.53 GiB with zero cgroup events.
This is a bounded cancellation cell only; adaptive long-chain drift and
two-live batch divergence remain open. [Details](../../bench/results/2026-10-22-phase5-coder-mtp2-cancel-state/README.md).

A fresh, supervised per-layer QSA trace now matches the serial MTP2 control at
accepted lengths 70, 72 and 74, then differs in all 12 QSA layers at lengths 76
and 77, starting at model layer 3. Both prompts still match serial for their
ten generated tokens. Minimum available host/admission memory was 16.55/15.10
GiB with no cgroup events. The split trace shows both indexer arrays and K/V
cache state change across all 12 layers from model layer 3 by length 76.
Per-token K/V/indexer and decoder-compute ablations retain the same divergence,
so neither batched path alone explains it. The cause and relation to later
output drift remain unknown. A concurrent duplicate-prompt control found both
batch slots' QSA hashes mutually matched but differed from serial,
while their ten-token outputs remained exact.
See the [batch-MTP report](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

Earlier QSA runs submitted the long request and one-token peer concurrently;
a harness name-check error meant they did not delay the peer after the first
output as intended. They still show QSA drift after the peer finishes. A
corrected MTP2 control submitted the peer after 48 solo-path tokens: QSA
hashes matched at common lengths 121/122, then all 12 indexer/KV hashes
changed from 124 through 163. Direct GDN captures were bit-exact at committed
positions 120/121 and differed across all 36 layers at 123 (relative L2 0.0142).
Output remained exact. The first state change is after handoff during batch-slot
work; the responsible operation and quality bound remain unknown.

Direct numeric captures at committed position 126 found GDN state drift in
all 36 layers for both MTP2 (relative L2 0.00973) and target-only (0.00841),
despite exact 96-token output parity. MTP2 is not required; numerical cause
and quality bound remain unknown.

A delayed target-only control matched GDN state through positions 116–118,
then first differed at 119/model layer 12 (relative L2 0.00780), with exact
output. MTP2 stayed exact at positions 120/121 and first differed at 123/model
layer 1. Per-token KV/indexer and decoder ablations retained MTP2's first QSA
mismatch at length 124, ruling out either batched path alone. State drift
persists; its source and quality bound remain unresolved.

A corrected opt-in layer-12 capture paired rows by explicit position/token and
recorded batch slot IDs. The delayed target-only run matched the serial 96-token
output exactly and matched all captured fields at position 118; at position 119,
layer-12 input `x` and every captured downstream field differed. The batch
scheduler averaged one row per window, so this run did not explain the separate
multirow mismatch. See the [capture report](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md).

A separate two-live target-only run averaged 1.96 rows across 96 windows and
reproduced slot 1's first output mismatch at token 60. At position 127 it
consumed the same token as its fresh serial control, while all captured layer-12
fields differed; input `x` relative L2 was 0.06058. The internal delta therefore
precedes the visible token change, but the model-wide origin remains unknown.
The selected positions and captured arrays repeated bit-for-bit in a second
supervised run; this is bounded to the same prompt pair and build.

At the earlier selected boundary, direct layer-12 committed-state capture found
slot 0 exact through position 70 and changed at 71 (relative L2 0.00379), while
slot 1 was already changed at position 68 (0.00822). Layer-12 input `x` changed
at the same selected positions. Slot 1's earlier onset remains unbounded; see
the linked capture report for paired state and activation metrics.

A six-token all-layer state capture then found the row mapping was reversed in
that run: physical slot 0 matched serial prompt 1, slot 1 matched prompt 0, with
36/36 GDN layers agreeing on each mapping. Slot 0 was exact at position 68 and
first changed at GDN layer 2 by position 71; slot 1 was already changed at
position 68, first at layer 5. Both six-token outputs matched their controls.
Slot-to-prompt assignment varied across runs, so these boundaries are kept
run-local and do not explain token 60.

A same-workload layer-1 MoE capture found exact inputs, GDN fields and shared
expert output for prompt 1 at position 71, while the combined MoE vector differs
in all 2,560 values (relative L2 `0.00086265`). The six generated tokens still
match serial. This narrows the selected boundary to routed expert output,
combination or related per-row state without identifying a specific expert or
operation. Minimum available RAM was 17.465 GiB, with zero cgroup memory events.
[Compact result](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/two-live-layer1-moe-output-summary.json).

A 96-token paired trace repeats the position-71 combined-output delta for
prompt 1 and reaches the known token-60 mismatch. By positions 118–127, both
requests already have changed layer-1 state, GDN fields, MoE inputs and shared
outputs. Minimum available RAM was 17.434 GiB; the added state capture makes
timing diagnostic only. [Selected-position results](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/two-live-layer1-moe-long-chain-summary.json).

An opt-in route/parts trace then showed prompt 1 keeps identical top-10 expert
IDs and weights at position 71, with nine expert outputs exact and only expert
11 changed. Weighting that expert's part delta reproduces the combined MoE
delta to a `3.24e-9` maximum residual. This pins the selected numerical delta
to expert 11's output path, without explaining its numerical cause. The six
output tokens still matched serial; minimum available RAM was 17.643 GiB.
[Compact result](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/two-live-layer1-expert11-summary.json).

## Near-term direction

The latest expert-11-first two-live capture mapped prompt rows through raw
routes and slot-tagged GDN state at positions 68/71. One row diverged by layer
5 at position 68; the other was exact then but diverged by layer 6 at position
71 after an exact layer-4 MoE output. The unmatched row also had changed layer-4
activation and router weights, so its expert output remains unattributed.
[Details](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/layer4-profile-e11-first-positions68-71/README.md).

A follow-up isolates the position-68 expert-248 owner transition. On the same
activation, the independent CPU/GPU oracle differs at relative L2 `0.0113` by
default and is bitwise equal with `STRATA_NATIVE_CPU_Q8_1_DOT=all`. The default
two-live service row changes only expert 248's part (combined output relative
L2 `0.0028174`); in the separate Q8_1-all service cell the same expert's
CPU→CUDA transition has exact parts and combined output. State stays exact for
one request through position 71; the other has only a tiny first difference
at layer 30 (relative L2 `5.84e-9`). Different route histories between selector
cells prevent a whole-model causal claim. Phase 5 remains open.
[Details](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/layer4-expert248-q8-all-owner-pair/README.md).

1. Continue resolving batch-MTP output divergence: capture earlier layer
   boundaries and logits around the reproducible multirow drift, then isolate
   the first recurrence or verifier operation that changes the row. Extend
   accepted-prefix direct-state and long-chain
   recovery coverage, widen cancellation boundaries beyond the passing Coder
   MTP4 decode/prefill points, and keep adaptive migration opt-in until its
   long-chain state contract is bounded.
2. Continue Phase 6 only on qualified candidates: finish supported interactions,
   held-out confirmation and response-model diagnostics, then report energy and
   Pareto tradeoffs with physical-memory, clock and uncertainty context.
3. Update detailed status and integration notes as evidence lands. Commit and
   push when each phase gate is actually complete; preserve the six-GiB host
   headroom and separate workspace reserve throughout.

Models stay under `~/models/`; build products, credentials and local agent
configuration stay out of Git. Do not combine host RAM and CUDA capacity into a
single memory figure.

A dispatch-owner follow-up maps the selected layer-1 position-71 Coder row exactly: expert 11 moves from primary VRAM in serial to CPU in batch, and its recorded CPU output matches the batch part within `5.0e-11` (serialization rounding). This associates the isolated expert delta with an owner change but leaves the numerical cause and later token-60 relationship unresolved. [Details](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md).


The same-input native expert oracle confirms the prompt-1 owner transition (serial GPU and batch CPU outputs each match their owner-specific oracle exactly). Prompt 0's serial CPU output and batch CPU dispatch 3505 both match the exact single-token CPU oracle, to JSON serialization precision (`5.0e-11`). The earlier reported 2.19 relative-L2 difference compared against prompt 1's oracle activation by mistake. Prompt 1's CPU/GPU difference remains real for that activation and needs broader numerical qualification.

A temporary expert-11-first residency profile made the paired layer-1 MoE
output exact and moved the first changed committed GDN state to layer 4. Layer 2
still switches expert 164 from VRAM to CPU with a same-input, oracle-confirmed
owner arithmetic difference. This narrows the correctness investigation only;
it is not performance evidence or a supported profile. The trace joiner now
rejects owner/verifier route mismatches. [Details](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

A new opt-in IQ3_S/Q2_0 CPU Q8_1 path matches CUDA bit-for-bit for two captured
layer-21 activations, but adaptive recovery still differs on 254/256 tokens in
the paired long-chain test. Router weights and committed state already differ
before the targeted expert output can explain the drift. Phase 5 remains open;
[details](../../bench/results/2026-10-22-phase5-coder-iq3s-q2_0-layer21-parity-intervention/README.md).

A separate two-live six-token check with opt-in Q8_1 parity matched both serial
outputs, including an exact CPU↔GPU expert-248 owner transition. One later GDN
state differed only at relative L2 `5.84e-9`; the other stayed exact. This
narrows one case and does not close Phase 5. [Details](../../bench/results/2026-10-22-phase5-coder-e11-first-q8all-two-live/README.md).

The new shared CPU selector also rebuilt for HIP and SYCL on maestro1, with both
service help checks and the HIP selector-contract check passing. This is x86
compile/startup evidence only. [Build record](../../bench/results/2026-10-23-phase5-maestro1-iq3s-q2-selector/README.md).

The seven-block Coder cache × context confirmation also has a new retrospective
rail-energy analysis: `VIN_SYS_5V0` per output token was 7.42% lower at 8K and
7.05% lower at 16K with the larger requested cache. These are background-
contaminated named-rail estimates, not process or whole-device energy, and do
not change the profile direction. [Details](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/rail-followup/README.md).

The separate short Coder task's seven-block cache confirmation shows an
11.19% lower `VIN_SYS_5V0` estimate per output token with the larger cache at
8K. These request-window rails include idle/background power and are not
whole-device energy. [Details](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-confirm7/rail-followup/README.md).

A held-out 256-token adaptive short-chain recovery test differed from the
initial output at 237 positions and had changed accepted-state hashes at every
prefix; the delayed control stayed exact. This extends the known mismatch but
does not bound it or locate its cause. [Details](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/open-response-short-chain-256pos/README.md).

A two-live target-only check with Q8_1 forced to `all` matched slot 0 for 96
tokens but slot 1 first differed at index 66. Minimum physical/admission
availability was 17.54 GiB. This single correctness cell does not identify the
cause or qualify performance; [details](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

The follow-up captured that row's logits at position 133: both arms used input
token 3008, but the top two reversed (2100 versus 5435). This locates the
changed output at verifier logits while leaving its upstream cause open.
An all-layer state capture found a tiny first recurrent-state delta at model
layer 10 (relative L2 `1.09e-7`), which grows by layer 12; the arithmetic cause
at that later position was unresolved. [Full capture report](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).
Repeated layer-10 traces show the first changed intermediate is the recurrence
output `y` at relative L2 `7.70e-8`; projected output returns to exact values.
State is exact through position 82; at position 83, layer-9 MoE expert 233
switches VRAM→CPU and its owner-specific output accounts for the first
captured state delta. Same-selector CPU/GPU oracle outputs match their
respective service parts exactly. Phase 5 remains open.


A 3,000 MiB requested expert cache kept layer-9 expert 233 on VRAM for both
serial and batch at the exact position-83 input. Its ten routed parts and MoE
output matched bit-for-bit; the 1,500 MiB cell had a CPU owner transition and
small delta. This is a narrow correctness intervention, not a full-sequence or
performance result. Phase 5 remains open.


The 3,000 MiB cache did not restore full two-live sequence parity: slot 0 matched
96 tokens, while slot 1 diverged at token 60 (versus 66 in the 1,500 MiB cell).
The targeted expert-233 output was exact with GPU residency, but that local fix
did not carry through the full sequence. Phase 5 remains open.


A repeated exact-input position-83 capture again found bit-identical expert
parts and combined MoE output at a 3,000 MiB cache, with expert 233 resident on
VRAM in both paths. The 96-token two-live mismatch persists.


The 3,000 MiB sequence investigation is still unsettled. One run found a layer-25
state delta at position 83, but repeated and combined captures at that position
were exact. Separate same-prefix captures at position 127 point to layer-24
state history and intermediate `h` when output first differs, but do not prove
causality. Phase 5 remains open.


The same-run position-112 capture is the strongest localization so far: layer 24
first differs in committed GDN state; its inputs and QKV are exact, and `h` is
the first changed stage. The state delta appears after sampled exact states at
positions 83 and 96, ahead of slot 1's first changed output at index 60. The
targeted CUDA parity tests pass but do not cover integrated scheduling. Phase 5
remains open.


A same-run onset sweep found layer-24 state/intermediates exact through position
104, with the first sampled difference at position 108: `h` changes while
`x`/QKV/gate/beta/z are exact; recurrent and convolution state then diverge.
Slot 1's output first changes at index 60 (position 127). The cause remains
unresolved.

A supervised repeat of the 104–108 layer-24 sweep changed state earlier than
the prior run: first at 105 with `x` changed, then `h` first at 107–108. The
prior run first changed at 108 with `h`. Output still diverged at index 60.
Verifier row IDs moved between runs; pairing was confirmed using captured input
tokens. The cause and stable onset remain unresolved, so this remains
correctness localization rather than a performance result.

The attempted layer-23 tensor comparison could not capture a two-live batch row:
the diagnostic supports one-row windows, while both requests were grouped. A
one-live request used the serial verifier path (header slot `-1`) and is not a
batch comparison. The QSA-to-layer-24 input boundary remains unlocalized; this
capture limitation is recorded as unsupported rather than a pass.
