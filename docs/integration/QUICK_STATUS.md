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
accepted-state correctness and broader performance interactions. The full
Orin CUDA regression suite passed 130 tests with two optional IQ-fixture tests
skipped; Python integration discovery now passes 170/170. The latest focused
accepted-window, GDN and graph CTest selection passed 5/5. The latest
seven shared-source files were rebuilt from a fresh isolated snapshot for HIP
and SYCL on maestro1 with two jobs; both `strata --help` checks returned zero.
This is x86 compile/link and CLI-startup evidence only, not accelerator runtime
or Orin performance evidence. Build/source hashes are in the linked backend
record in [STATUS](STATUS.md). See the [Phase 8 closeout](PHASE8_CLOSEOUT.md)
for the exact release scope and exclusions.

A fresh full-tree rebuild also passed for HIP (345 targets) and SYCL (201)
from current shared sources on maestro1 with one job. Both `strata --help`
checks passed; a direct SYCL CPU-runtime snapshot test passed 3,901 checks.
This adds x86 build and CPU-runtime evidence only; accelerator runtime was not
tested. [Build record](../../bench/results/2026-10-23-phase8-maestro1-current-source-backend-build/README.md).

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

A supervised 72-token two-live target-only repeat matched slot 0's serial output
and first differed at slot 1 token 66. Four captured accepted-prefix states at
slot handoff matched serial exactly, but the remaining batched decode emitted
no prefix trace. A later full-state capture matched slot 0's 72 output tokens
but found a terminal GDN delta from layer 5 (whole-state relative L2
`2.24e-7`); a per-prefix hash scan found earlier divergence at batch position
75 for slot 0 and 84 for slot 1. Slot 1's terminal state was not paired after
its output diverged. A direct capture at slot 1 position 84 found layer 10
recurrent-state drift (`1.88e-7` relative L2), with `y` the first changed
stage field and later captured fields exact. The incoming state was already
different there; another run found drift at position 83, so the onset varies
between runs and its cause remains unresolved. These are correctness
localization results, not performance evidence. [Details](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

These results are specific to the tested Orin build, model and workload. No
candidate setting has been promoted to a default.

| Experiment | Measured result | Scope |
| --- | --- | --- |
| Expert cache × context, Coder IQ1_M, held-out 7,501-token task, seven same-day blocks | 3,000 vs 1,500 requested expert-cache slots reduced median client latency 7.95% at 8K context (paired 95% interval 7.93%–15.11%) and 7.71% at 16K (7.23%–7.82%). Cache-by-context interaction was +1.12% (0.22%–8.58%). | MTP off, FP16 KV, exact 48-token answer; one long-task profile. [Report](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/README.md) |
| Expert cache, short Coder task, seven blocks | 3,000 vs 1,500 requested slots reduced median client latency 12.83%; TTFT fell 13.47%, with prompt/decode throughput up 15.77%/10.24%. | Short task only; see [STATUS](STATUS.md). |
| MTP × prompt length × KV, Coder IQ1_M, seven blocks / 56 arms | On the 7,501-token task, MTP4 reduced decode throughput 9.17% with FP16 KV and 9.24% with INT8; client time rose 0.59% and 1.01%. Short-task effects were smaller and uncertain. | MTP4 was dominated on measured long-task latency and named-rail energy; no default changed. Other Phase 6 factors remain open. [Report](../../bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/README.md) |
| Prefill chunk × expert cache, Q2_0 near-limit retrieval, seven held-out blocks | Chunk 128 reduced median request time 59.54% at 3,000 slots and 59.74% at 3,500 slots; all 28 requests returned the exact 41-token answer after 7,506 prompt tokens. | Cache × chunk interaction interval included zero; no general default. [Report](../../bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/README.md) |
| Named-rail energy for the same Q2_0 cache × prefill campaign | Chunk 128 lowered `VIN_SYS_5V0` median energy per total token 59.43% at 3,000 slots and 59.41% at 3,500; cache × prefill interaction interval included zero. | Retrospective request-window rail integration, includes idle/background activity; not process-attributed or whole-device energy. [Analysis](../../bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/rail-followup/README.md) |
| Coder two-live residency profile, three paired screening blocks | Moving layer-9 expert 233 to first rank restored exact 96-token output parity for both live rows on the original pair. Median paired batch throughput changed −1.40% (three-block bootstrap 95% interval −2.17% to +16.66%). | A held-out pair still diverged on slot 1 at token 78 under both base and candidate profiles. No performance promotion or general correctness claim. [Report](../../bench/results/2026-10-23-phase5-coder-layer9-expert233-residency-intervention/README.md) |

The four-cell descriptive Pareto view keeps all profiles nondominated across
latency, decode, observed host availability, named-rail energy, and logical
file reads. Higher cache and larger prefill chunk trade lower latency/energy
for slightly lower observed host availability; physical disk I/O is not
attributed. This does not promote a default.

A three-request same-engine MTP test required and observed three rejected
drafts in the middle request, then matched MTP-off output and all main-model
state fingerprints through a further recovery request. All shared accepted
prefix boundaries matched across the three requests for one 512-token Coder
prompt. This is narrow transaction evidence; long-chain adaptive drift and
multi-live state/output parity remain open. [Report](../../bench/results/2026-10-23-phase5-coder-mtp-rejection-recovery/README.md).

A near-limit 7,498-token Coder prompt extended this to a rejection in the
initial request followed by two same-engine continuations. MTP4 rejected 9/15
drafts; all shared state boundaries and all three outputs matched MTP-off.
This single prompt does not bound adaptive migration or multi-live decoding.
[Report](../../bench/results/2026-10-23-phase5-coder-mtp-long-rejection-recovery/README.md).

A short-prompt and a 7,501-token MTP3 follow-up both matched MTP-off outputs
and all shared main-model state fingerprints across three same-engine requests.
MTP3 rejected drafts before recovery in both cells; the near-limit run retained
13.283 GiB minimum physical/admission availability. These add two transaction
cases, not an adaptive-chain or multi-live bound.
[Short](../../bench/results/2026-10-23-phase5-coder-mtp3-rejection-recovery/README.md),
[near-limit](../../bench/results/2026-10-23-phase5-coder-mtp3-long-rejection-recovery/README.md).

The matching current-build accepted-window, GDN recurrent/parity and captured
graph CTests passed 5/5 under the 28 GiB supervisor, with 23.73 GiB minimum
host availability and no cgroup memory events.

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

A 3,000-slot cache correctness diagnostic is now localized one layer
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

A 3,000-slot repeat still moves layer-1 expert 11 VRAM→CPU and changes the first
committed GDN state at layer 2. Its activation differs from the 1,500-slot cell,
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


A 3,000-slot expert-cache request kept layer-9 expert 233 on VRAM for both
serial and batch at the exact position-83 input. Its ten routed parts and MoE
output matched bit-for-bit; the 1,500-slot cell had a CPU owner transition and
small delta. This is a narrow correctness intervention, not a full-sequence or
performance result. Phase 5 remains open.


The 3,000-slot request did not restore full two-live sequence parity: slot 0 matched
96 tokens, while slot 1 diverged at token 60 (versus 66 in the 1,500-slot cell).
The targeted expert-233 output was exact with GPU residency, but that local fix
did not carry through the full sequence. Phase 5 remains open.


A repeated exact-input position-83 capture again found bit-identical expert
parts and combined MoE output at a 3,000-slot request; expert 233 remained resident on
VRAM in both paths. The 96-token two-live mismatch persists.


The 3,000-slot sequence investigation is still unsettled. One run found a layer-25
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

A repeated positions-80–84 state sweep found a larger slot-0 mismatch: it
returned all 72 serial output IDs, but its layer-10 state differed from position
80 (relative L2 `5.83e-3`). A same-run all-layer capture found the first changed
GDN state at layer 5 (recurrent relative L2 `5.41e-5`); slot 1 was exact at
position 80. The repeated sweep reproduced the same metrics, so multi-live
persistent-state parity remains unresolved even when output tokens match.
An additional layer-5 sweep sampled positions 78–80 and found slot-0 recurrent
state already differed at position 78 (`9.55e-5` relative L2); at position 80,
the convolution section matched again while recurrent state remained changed.
[Details](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

A same-run capture localized an early slot-0 perturbation: layer-4 expert 218
moved VRAM→CPU with exact inputs/routes, and the independent oracle matched each
service output to its corresponding GPU/CPU result. The following layer-5 stage
first changed at `x` for the same token/position; layer-5 state was exact at the
prior sampled position. This strongly supports owner-dependent arithmetic as
the source entering layer 5, though downstream propagation remains unproven.
[Details](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

Raising the requested expert-cache slot count to 3,000 left the same layer-4 expert 218
VRAM→CPU owner change and reproduced the same layer-5 `x`/state delta for the
same activation. This cache increase does not resolve the measured cell.
[Details](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

Moving expert 218 to rank 0 in a temporary profile kept it on VRAM for serial and batch at the exact same position-77 activation; its parts, combined MoE output, and layer-5 stage/state were then bit-identical. This repairs that local state perturbation, but not the separate slot-1 sequence mismatch (first difference at 66). At positions 76/77 slot 0 first differs later at model layer 32; layer-30 MoE output is exact while layer-31 MoE input already differs. Phase 5 remains open. [Intervention analysis](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/expert218-intervention-analysis.json).

A per-layer GDN hash trace under the expert-218-first profile found prompt 0 first differing at prefix 70 (ordinal 30) and prompt 1 at prefix 82 (ordinal 8), while output slot 1 still first differed at token 66. A direct position-82 state capture instead found prompt 0 first differing at model layer 32; later prompt-1 traces show tiny layer-10 `y`/state deltas with exact layer-9 MoE data. Internal batch row assignment varies between runs, and state onset varies, so the cause is still open. [Analysis](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/expert218-intervention-analysis.json).

A paired 72-token screen at one and eight expert workers produced the same
pattern: slot 0 matched and slot 1 first diverged at output index 60. Worker
count did not shift the mismatch in this cell, but its underlying cause remains
unresolved. Minimum admission availability was 14.17/14.16 GiB with zero
cgroup events. [Report](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

A narrow layer-22 expert-rank swap made the sampled layer-22 MoE and following
boundary exact, and slot 1's full 96-token output matched. Its recurrent state
still differed by layer 9 at terminal position 162. At position 105, layer-39
MoE and its boundary were exact; the first changed sampled stage was layer-40
GDN `h` (relative L2 `8.700e-5`). This narrows one sampled path but does not
distinguish pre-existing recurrent state from row-context recurrence arithmetic.
The opt-in multirow boundary capture passes the focused Orin parity tests;
maestro1 backend rebuild is pending while its root filesystem remains 99% full.
Phase 5 remains open. [Trace notes](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

A same-profile position-104 follow-up found the layer-39 pre-branch residual
and routes exact, but the branch output changed (relative L2 `3.6151e-5`); only
expert 50's part changed as it moved GPU→CPU. On that captured activation, an
independent oracle matched the serial service part to GPU and the batch part to
CPU exactly. Layer-40 input `x` and committed recurrent state were already
different at position 104. This supports an earlier owner-dependent
contribution in this sampled run; the first source is position-dependent and
the general two-live state drift remains unresolved.

A new current-source Coder IQ1_M prefill-chunk × expert-cache screen completed
three randomized blocks: chunk 128 reduced client total time 67.4%/69.6% at
requested caches 1,500/3,000 slots for a 7,501-token task. The median
cache-by-chunk time interaction was −9.8%, with minimum physical/admission
availability 14.19/14.14 GiB and zero cgroup events. This is descriptive
screening evidence without confidence intervals; the distinct seven-block
held-out confirmation is reported separately below. [Screen report](../../bench/results/2026-10-23-phase6-coder-prefill-cache-screen3/README.md).

A seven-block held-out Coder IQ1_M confirmation is complete: all 28 measured
cells returned the exact 46-token answer for the distinct 7,501-token archive,
with zero cgroup memory events and at least 14.19 GiB physical/admission
availability. Chunk 128 lowered client total time 67.71% (95% paired-block
interval 67.55%–67.95%) at 1,500 requested cache slots and 68.72%
(68.56%–68.85%) at 3,000; the cache-by-chunk interaction was −3.13%
(−5.43% to −1.93%). Decode-throughput intervals included zero. This is scoped
to Coder IQ1_M, FP16 KV, MTP off, 8K and this archive task; no default is
promoted, and broader Phase 6 interactions and energy/Pareto scope remain open.
[Full report](../../bench/results/2026-10-23-phase6-coder-prefill-cache-confirm7/README.md).
Retrospective `VIN_SYS_5V0` energy per output token was 66.27%/67.15% lower
with chunk 128 at the two cache settings, but the named rail includes idle and
background activity and is not process-attributed or whole-device energy.
[Rail analysis](../../bench/results/2026-10-23-phase6-coder-prefill-cache-confirm7/rail-followup/README.md).


A new three-block current-source MTP window screen (off/2/3/4) on one short
Coder IQ1_M retrieval prompt passed all 12 cells with paired output parity.
MTP3 showed +5.24% median decode throughput; MTP4 was effectively flat. MTP2
had a large -57.96% outlier, so no MTP2 timing conclusion is supported. This
is screening only, not a default or broad quality/state claim.
[Report](../../bench/results/2026-10-23-phase6-coder-mtp-window-screen3-current/README.md).

A seven-block MTP-off/MTP3 replication on the same 512-token prompt gave +4.34%
median decode throughput (paired bootstrap 95% interval +3.86% to +5.57%) with
response-content parity in all pairs. This is same-prompt replication, not
held-out confirmation, and the no-trace campaign does not test persistent
state. [Report](../../bench/results/2026-10-23-phase6-coder-mtp3-window-paired7-same-prompt/README.md).

A near-limit MTP3 screen showed a workload-length interaction: across three
paired blocks, MTP3 decode throughput was 6.01% lower than MTP-off on the
7,501-token request (95% interval 6.08%–5.56% lower), while it was 4.34% higher
on the 512-token prompt. Total request time on the near-limit prompt rose only
0.67% because prefill dominated. This is screening evidence for these workloads,
not a default decision. [Report](../../bench/results/2026-10-23-phase6-coder-mtp3-window-long-screen3/README.md).

A seven-block held-out retrieval confirmation returned the exact expected
answer in all 14 MTP-off/MTP3 cells. MTP3 decode throughput improved 10.25%
median (95% interval +8.98% to +10.49%), though two MTP3 cells had severe
prefill/TTFT outliers; stable end-to-end latency is not established. [Report](../../bench/results/2026-10-23-phase6-coder-mtp3-heldout-retrieval-confirm7/README.md).

An MTP3 accepted-prefix probe matched MTP-off token IDs and all persistent-state
fingerprints at 31 shared commit boundaries over a 64-token chain (33/60 drafts
accepted). This is a bounded transaction check; adaptive long-chain and
multi-live correctness remain open. [Report](../../bench/results/2026-10-23-phase5-coder-mtp3-accepted-prefix-64/README.md).
