# Batch-MTP graph lifecycle and output diagnostic

Date: 2026-10-22. Hardware: Jetson AGX Orin, ARM64, CUDA 12.6, current
worktree candidate build. This is a Phase 5 correctness diagnostic, not a
performance qualification.

## Question and result

The run enabled `--batch 8 --batch-mtp` with Coder IQ1_M and MTP, then
compared eight deterministic chat-template prompts against serial controls.
All eight batch slots were admitted and batch MTP remained enabled. Batch output
matched serial target-only output on only 2/8 prompts (slots 0 and 4), and
matched the serial MTP2 arm on only 1/8 (slot 0). Against the target-only
comparison it first diverged at generated token indices 30, 59, 42, 34, 67,
and 72 for slots 1, 2, 3, 5, 6, and 7; against serial MTP2 it also diverged
at index 33 for slot 4 and index 27 for slot 7. Matching terminal text for
some requests should not be interpreted as persistent-state parity.

A follow-up used the same MTP2/context/cache profile and prompt with one live
request admitted to an eight-slot batch-MTP server. Its full 96-token greedy
output matched serial MTP2 exactly. This narrows the observed output divergence
to behavior that requires multiple live requests or a difference in their
interleaving; it does not yet identify which shared-window/slot-rotation path
is responsible. The supervised follow-up passed with 16.05 GiB minimum
available physical RAM and zero scoped cgroup OOM events. State parity was not
tested in this follow-up.

A two-live-request follow-up used the same profile with `--batch 2`. Slot 0
matched serial MTP2 for all 96 tokens; slot 1 first diverged at token index 60.
The failure therefore reproduces with the smallest tested concurrency, while
the one-live request in an eight-slot server matches. The verifier log shows
both slots sharing a four-row window (`1,1,0,0`) before later windows; this is
consistent with a shared-window or per-slot interaction, but does not identify
the causal operation. Minimum available physical RAM was 16.67 GiB, with zero
scoped cgroup OOM events. This remains a failed functional diagnostic, not a
performance result. Per-slot terminal persistent state was not captured.

A matched two-live-request target-only batch control (MTP removed, otherwise
same prompt, context, cache and batch size) also diverged from its serial
target-only arm at token 60 on slot 1; slot 0 remained exact. At that token,
serial MTP2 and target-only chose different tokens, and the batch MTP and batch
target-only arms also chose different tokens. Thus ordinary multirow batch
numerics already differ from serial, while batch-MTP additionally fails to
match its same-shape target-only batch control for slot 1. The matched target
batch run retained 17.41 GiB minimum available physical RAM and had zero scoped
cgroup OOM events. The evidence narrows the Phase 5 issue to target row/batch
numerics and MTP verification interaction; it does not yet establish which
logit, state tensor, or operation causes the argmax change.

The follow-up direct-state capture now localizes the target-only row drift.
For prompt 0, the batch slot captured at the 68-cell prompt boundary was
bit-identical to that prompt's serial committed GDN state across all 36 layers
(29,417,472 floats). At committed position 127, the corresponding batch slot
and serial prompt-0 state differed in 28,597,392 values, with relative L2
`0.010440` and maximum absolute difference `0.607868`; one layer remained
exact. This puts the state divergence after prompt admission and before the
observed token-60 output divergence. Request-to-physical-slot assignment can
vary between separate concurrent runs, so the state comparison is paired by
prompt and observed output, not by assuming a stable slot number. The current
capture covers the target-only arm; an equivalent MTP2 boundary-to-divergence
capture and finer first-divergence tracing remain open.

Full GDN dumps (about 112 MiB each) are retained in the local experiment
workspace for audit and are intentionally excluded from Git. The compact
state comparison and raw-logit analysis are recorded in `state-and-logit-analysis.json`.

The instrumented ARM64/CUDA candidate rebuilt with two jobs. Focused CTest
coverage passed 5/5: accepted usage/window, verifier batch parity, captured
graph trace, and graph lifecycle. maestro1 rebuilt the same shared source for
HIP and SYCL; both binaries linked and both `--help` checks returned 0. The
logs and binary hashes are in `backend-builds-maestro1/`. This is x86 build
evidence only; neither backend was executed on an accelerator.

The target-only serial arm had exactly one terminal persistent-state fingerprint
per request, and each fingerprint agreed with the independently computed
committed length and consumed-token tail. The batch engine emitted handoff
fingerprints but no per-slot terminal fingerprints. Therefore persistent-state
parity for batch MTP cannot be assessed with current instrumentation. The
harness correctly records this as a failed check rather than inferring state
from output text.

The verifier captured 16 distinct batch graph layouts with a configured pool
limit of 64. No layout repeated and no eviction/recapture occurred; the test did
not reach the lifecycle behavior it was intended to stress. A follow-up must
produce more than 64 distinct layouts and observe a reused layout after
invalidation/eviction before graph-pool resize behavior can be qualified.

The next [per-layer GDN hash sweep](gdn-hash-sweep-analysis.json) compared
committed states from batch positions 68–127 with fresh serial controls. In
target-only mode, one batch row matched its serial state exactly at positions
70 and 71; at position 72, GDN state ordinals 5–35 first differed (31/36
layers). The other target-only row matched its fresh serial control at
position 68, then first differed at position 69 in ordinals 4–35 (32/36).
In MTP2 mode, the mapped row matched at positions 68, 70, 72 and 74, then
first differed at 76 in ordinals 2–35 (34/36). Its peer had no exact common
committed-length hash in this sweep, so no onset is assigned. The target-only
row that first differed at position 72 still produced identical 96-token text;
the other row's first text mismatch remained token 60. Thus text equality can
hide earlier recurrent-state drift. The MTP2 result is likewise a state
diagnostic, not a speed result.

For this sweep the first target-only serial process was used for prompt 0, and
a separate fresh serial process supplied prompt 1. Reusing the same serial
process for both prompts changed prompt 1's state and output (its text first
differed from the fresh control at token 62), so those same-process data are
retained but excluded from the state pairing. This request-to-request serial
variation needs a separate cache/session investigation. The batch supervisor
reported 16.47 GiB minimum available RAM; the isolated prompt-1 serial control
reported 17.24 GiB. Both had zero sampled cgroup memory events. Clocks varied,
EMC readback was denied, and energy was not request-attributed.

A fresh target-only run captured raw committed GDN arrays at prompt position 67
and generated positions 71–72 for every available GDN layer. Each request
emitted the same six tokens as its isolated serial control. The capture showed
that two prompt-boundary states can be recorded against physical slot 0 before
the requests occupy batch slots, so the earlier layer-6-only comparison that
treated a slot as one prompt across the run was invalid. Comparing each later
batch state against both isolated prompt controls avoids that assumption. At
position 71, slot 0 was closer to serial prompt 0 (relative L2 0.00940 versus
0.20284 to prompt 1), and slot 1 was closer to prompt 1 (0.02314 versus 0.20366).
At position 72 the same assignments held: slot 0 was closer to prompt 0 (0.01079
versus 0.17960), and slot 1 was closer to prompt 1 (0.01942 versus 0.18092).
Both selected positions cover all 36 GDN layers. The position-72 states were
not bit-identical: 25,014,017/29,417,472 and 27,772,427/29,417,472 floats
changed, respectively. This resolves the apparent large layer-6 delta as a
bad prompt pairing, while confirming broad committed-state differences despite
identical short outputs. It does not explain the longer token-60 divergence or
establish a cause. Raw arrays remain local-only; the all-layer capture retained
17.69 GiB minimum available RAM, with zero sampled cgroup OOM events. Clocks
varied, EMC readback was denied, and energy was not request-attributed.


A follow-up adds the opt-in `STRATA_BATCH_MTP_GRAPH_LIMIT` override, valid from
1 to 64; batch MTP still defaults to 64. The cap-1 stress run submitted eight
requests concurrently to two batch slots (six output tokens each). It completed
16 batch windows, logged 15 layout captures across four layout keys, and
observed 14 LRU evictions followed by 11 recaptures of previously evicted
layouts. All eight requests returned six tokens. The run passed supervision
with 16.50 GiB minimum available RAM and zero cgroup memory events. This
qualifies eviction and recapture behavior for the forced cap-1 test path only;
it does not qualify the default 64-layout cap or performance. A separate no-override single-live-request check confirmed the effective
batch-MTP graph limit remains 64 and its six generated tokens matched the
serial MTP2 control exactly. The supervised run retained 16.97 GiB minimum
available RAM with zero cgroup OOM events. The configured full CUDA CTest suite
then passed 130/132 tests with the two optional IQ-fixture tests skipped; the
first run's only failure was `pool_test` missing its external S2 fixture, and
that test passed when the local fixture was supplied through
`STRATA_TEST_EXPERTS_BIN`.

The ARM64/CUDA candidate rebuilt with two jobs and the five focused
accepted-window, batch-parity and graph tests passed. The first maestro1 build
attempt was blocked by a full root filesystem. After scratch space became
available, the current `verify.hpp`, `verify.cpp` and `generate.cpp` sources
were synced and the HIP build completed with one job; the `strata` binary and
its `--help` check passed. The SYCL build tree reported no work because its
verifier and generator use the separate `source/sycl` overlay; its existing
binary's `--help` check passed in the configured oneAPI environment. These are
x86 compile/CLI checks, not accelerator runtime evidence. Source hashes, logs
and binary hashes are in `backend-builds-maestro1-graph-limit/`.

## Configuration and limits

Model identity: `Qwen3.8-Flash-Next-Coder-GGUF-IQ1_M`, split across the two
IQ1_M GGUF files under `~/models/strata-orin-validation/Coder-GGUF/IQ1_M/`,
with the local expert pack, tokenizer, and MTP runtime paths recorded in
`config.json`. No model was downloaded or copied into the repository. The
batch diagnostic used 8 slots, greedy decoding, up to 96 generated tokens,
context 1,024, expert cache 1,500 MiB, MTP depth 2, and prompt cache 6. Adaptive
accepted-only swaps were removed because the engine explicitly rejects that
combination with batch MTP.

The serial MTP2 run used this reduced profile. The independent target-only arm
removed MTP and inherited context 8,192 / expert cache 3,000 MiB from the source
configuration. All prompts were under 70 tokens, but the profile difference
means the target-only output comparison is diagnostic rather than a fully
matched performance or configuration control. There is no latency or speedup
claim here. The batch-vs-serial-MTP output mismatch is within the same reduced
profile and is the primary correctness finding.

The batch supervisor observed minimum available physical RAM of 14.77 GiB and
minimum admission availability of 11.39 GiB; the serial target-only control
observed 14.23 GiB for both. Scoped cgroup `low`, `high`, `max`, `oom`, and
`oom_kill` event counters were all zero in both arms. The six-GiB host headroom
was preserved. Clocks varied during the runs, EMC readback was denied, and
energy was not attributed to individual requests.

## Preserved evidence

- `config.json`: paths and base source configuration.
- `run-chat/`: serial MTP2 and batch-MTP engine logs and harness result.
- `run-target-only-final/`: target-only engine log and token comparison data.
- `supervisor-chat/`, `supervisor-target-only-final2/`: memory samples,
  tegrastats and supervisor summaries.
- `single_active_slot.py`, `run-single-active-slot/`, and
  `supervisor-single-active-slot/`: same-profile one-live-request isolation
  follow-up and its telemetry.
- `two_active_slots.py`, `run-two-active-slots/`, and
  `supervisor-two-active-slots/`: two-request reproducer and telemetry.
- `two_active_slots_target_batch.py`, `run-two-active-target-slots/`, and
  `supervisor-two-active-target-slots/`: matched two-request target-only batch
  control with MTP disabled.
- `analysis.json`: offline output, state-coverage, graph-layout and memory
  summary. Rebuild it with `python3 analyze_batch_mtp_graph_lifecycle.py`.
- `run-position-127-logits-all-slots/` and
  `state-and-logit-analysis.json`: full verifier-row comparisons and paired
  committed-state deltas. Full GDN binary captures are local-only.
- `capture_batch_gdn_hash_sweep.py`,
  `capture_isolated_prompt1_gdn_hashes.py`,
  `analyze_batch_gdn_hash_sweep.py`, `run-gdn-hash-sweep/`,
  `run-isolated-prompt1-gdn/`, and their supervisor directories: compact
  per-layer position sweep and its fresh serial second-prompt control. Hash
  files retain all batch positions; the analysis lists first exact mapping and
  first later divergence per mapped slot.
- `graph_lifecycle_lowcap.py`, `analyze_graph_lifecycle_lowcap.py`,
  `graph-lifecycle-lowcap-analysis.json`, and
  `run-graph-lifecycle-recapture/`: cap-1 eviction/recapture exercise and
  structural analysis. `build_maestro1.sh` records the pending backend build.
- `capture_alllayer_targetonly_commit_state.py`,
  `analyze_alllayer_targetonly_commit_state.cpp`,
  `run-alllayer-targetonly-commit-state/`, and
  `supervisor-alllayer-targetonly-commit-state/`: selected raw all-layer state
  comparison and memory/clock telemetry. The `.stgcmt` array dumps are
  local-only.
- `backend-builds-maestro1/`: exact-source HIP/SYCL build and help logs;
  compile evidence only.
- `run-retry/`, `run/`, and earlier supervisor directories preserve failed or
  superseded harness attempts; they are not used for the result above.

The harness is `tools/integration/batch_mtp_graph_lifecycle.py`. The test is
not a phase gate pass. Phase 5 remains open. Near-term work is to add opt-in
per-slot terminal state diagnostics, compare one-live and concurrent runs with
identical arguments, isolate the first divergent shared-window operation, then
exercise actual graph-pool eviction and recapture.

### Position-76 MTP2 committed-state follow-up (2026-10-22)

A supervised two-live MTP2 capture paired the batch row with isolated serial
controls by the generated token at position 76, not by physical slot number.
For prompt 0 (token 12654), all 36 GDN layer records were present. The batch
state differs from serial in 26,965,859/29,417,472 floats (relative L2
0.0182307); model layers 0–3 are exact, and the first changed state is GDN
model layer 4, where 817,139/817,152 floats differ (relative L2 0.00410183,
maximum absolute difference 0.0227253). Its 64-token output still matches the
serial MTP2 output. Prompt 1 (token 3069) has no captured accepted commit at
position 76, so that comparison is incomplete. The accepted-prefix log hook
also emitted QSA layer hashes only through state length 69 for the batch arm;
the serial arm reached length 77. It therefore cannot establish whether QSA
state had diverged before the layer-4 GDN difference. The raw batch `.stgcmt`
and serial `.gdn` arrays remain local-only; the comparator and capture harness
are retained for reproducibility. This localizes a state difference but does
not identify its cause or pass the Phase 5 gate.

### Per-layer QSA state follow-up (2026-10-22)

A second supervised run rebuilt the opt-in batch QSA hash hook into the current
Orin CUDA binary and repeated the two-live MTP2 capture with exact-profile
isolated serial controls. For prompt 1, per-QSA hashes match at committed
lengths 70, 72 and 74. At length 76 (token 3069) and length 77 (token 264), all
12 QSA states differ; the first differing state is QSA ordinal 0, model layer
3. Prompt 0 also differs across all 12 QSA states at length 77 (token 709).
The ten generated tokens for each prompt still match its serial control. Some
intermediate batch prefix lengths have no serial row with the same accepted
length and token, so no comparison is assigned there. Minimum host/admission
availability was 16.55/15.10 GiB, with zero cgroup memory events. These
instrumented hashes locate an earlier QSA state difference than the captured
GDN difference, but do not identify the operation that causes it or establish
that it causes the output divergence. The opt-in trace copies state to host and
is not a performance measurement. Raw per-request logs and hash streams remain
local-only; the capture and analyzer scripts are retained here.

### QSA indexer versus KV follow-up (2026-10-22)

The next instrumented capture split each per-layer QSA fingerprint into its
indexer arrays and K/V cache arrays while preserving the original aggregate
hash. The new serial aggregate hashes were identical to the previous capture.
Both indexer and K/V hashes matched their serial controls at accepted lengths
70, 72 and 74. At lengths 76 and 77, each component differed in all 12 QSA
layers, first at model layer 3; both prompts still generated the same ten token
IDs as their serial controls. The capture passed supervision at 16.53 GiB
minimum available host/admission memory with zero cgroup events. The divergence
therefore reaches both QSA indexer and attention-cache state by length 76, but
this does not distinguish an upstream input difference from two independent
state-update errors. The component hashes and raw logs remain local-only.

### Per-token append and decoder ablations (2026-10-22)

Two supervised same-profile repeats disabled one batched path at a time. With
`STRATA_NO_BATCH_KV_STEP=1`, which uses per-token QSA K/V and indexer appends,
all component hashes still matched serial at lengths 70, 72 and 74, then both
indexer and K/V state differed across all 12 QSA layers at lengths 76 and 77.
With `STRATA_DEC_BATCH=0`, which uses per-token decoder projections and
updates, the same hash boundary and layer pattern reproduced. Both prompts
produced the same ten token IDs as their serial controls in both ablations.
Minimum host/admission availability was 16.73/16.40 GiB for the append
ablation and 16.59/16.59 GiB for the decoder ablation; both had zero cgroup
memory events. These negative controls rule out either batched append/update
or batched decoder compute as the sole cause in this reproducer. The ablations
were correctness diagnostics, not randomized timing comparisons.

### Concurrent duplicate-prompt control (2026-10-22)

To check slot isolation, both concurrent batch requests used prompt 0 with the
same MTP2 profile. At state length 77/token 709, their committed QSA hashes
were identical across all 12 indexer and K/V layer groups. Each batch row's
hashes nevertheless differed from both fresh serial controls in all 12 groups.
Both request outputs matched the serial ten-token sequence exactly. Minimum
host/admission availability was 16.61/16.37 GiB over 93 samples, with zero
cgroup memory events. The duplicate rows therefore stay mutually consistent,
while batch QSA state still drifts from serial despite identical text; this
does not identify the differing operation or establish longer-chain behavior.

For this final diagnostic source, maestro1 rebuilt HIP from the identical
`src/program/generate.cpp` SHA256 `9f136bb977fe118fd1f25b5c3312828577b4b301a47d3929fddbe9cb50d06e5f`;
the HIP binary SHA256 is `904c1a32d9427de12aa635b238dd58f386902022e5218fa9a7551a2f0df7b8b5`,
and its binary `--help` exited 0. The SYCL
build uses a separate migrated file at `source/sycl/src/program/generate.cpp`;
the QSA hook does not modify that source, and its build reported no work. A
current SYCL binary startup check on maestro1 aborted with “No device of
requested type available,” so no new SYCL startup pass is claimed here.

The component-hash revision was also rebuilt on maestro1 for HIP from source
SHA256 `de1258c0fc439883c424562b58201d8d486e34a9a8cefbaffa22ae12390d16ba`;
the HIP binary SHA256 is
`59fd1a42a4ecbd63ba478cf10af26ba1eee51850955444093d81961f57cf8c63`, and its
help check exited 0. The SYCL overlay remained unchanged and no-work; its
current startup limitation above remains.


### One-live batch-slot QSA trace after admission (2026-10-22)

A supervised follow-up kept slot 0 in the batch-MTP route after a one-token
competitor was admitted and finished. Slot 0 generated 96 tokens and slot 1
generated one; both outputs matched their serial MTP2 controls exactly. The
batch slot's QSA indexer and K/V hashes matched serial at accepted state
lengths 70, 72 and 74, then differed in all 12 layers at lengths 76 and 78,
first at QSA ordinal 0/model layer 3. Minimum available physical host memory
was 16.77 GiB and minimum admission availability was 13.50 GiB over 112
samples; cgroup low/high/max/OOM/OOM-kill counters remained zero. This shows
the persistent-state difference does not require two simultaneously active
verifier rows. It does not distinguish the solo-to-batch transition from
batch-slot execution, identify the changed operation, or establish output
impact beyond this exact 96-token sample. Raw traces remain local-only; the
concise analyzer output is retained with the local capture.


### Extended one-live batch-slot trace (2026-10-22)

The same supervised one-live-after-admission control was extended through 96
generated tokens (QSA hashes requested through position 164). Both the 96-token
slot-0 output and the one-token competitor exactly matched their serial MTP2
controls. Early batch state samples had odd accepted lengths while the serial
MTP2 run recorded even lengths, so those points have no exact-length serial
control and are not compared. At every common captured state length from 91
through 163 (41 paired samples), aggregate, indexer and K/V hashes differed
across all 12 QSA layers, beginning at model layer 3. Thus state divergence
persists over this sampled range while output remains token-exact; this does
not bound numeric error, establish a user-visible quality effect, or identify
the originating transition/operation. The supervisor passed with 16.76 GiB
minimum host and admission availability over 115 samples and zero sampled
cgroup memory events. Energy was not measured. Full traces remain local-only.

### One-live GDN numeric capture (2026-10-22)

A supervised serial-versus-one-live-after-admission MTP2 run captured every
GDN layer at the common committed boundary 126. The long request's 96 generated
tokens matched serial exactly; the one-token competitor completed after
admission. All 36 GDN layers differed: 28,576,901/29,417,472 float values,
relative L2 0.00972594, maximum absolute difference 0.373845, first changed
model layer 1. The first attempt requested position 127, which this MTP2 commit
schedule did not emit; that capture produced no state records and is retained
locally as an unpaired/unsupported position. Position 126 was selected from the
observed common commit sequence and yielded complete 36-layer records. This
confirms numeric GDN drift in the one-live batch slot but does not bound its
quality effect or identify the initiating operation. The successful supervisor
passed with 16.69 GiB minimum host/admission availability across 71 samples and
zero cgroup events. Dynamic clocks were observed, EMC readback was unavailable,
and energy was not measured. Raw 226 MiB state files remain local-only.

The capture harness is `capture_mtp2_one_live_gdn_state.py`; the compact
comparator is `compare_mtp2_one_live_gdn_commit.cpp`. The tested binary SHA256
was `832068fd31b9e1dff9f835fb318e7c7c5c7f481026e9398111256345ac20ab45`.

The same one-live admission control was then repeated with MTP disabled, using
target-only decode and the same prompt, context, expert cache and capture
position. The long output again matched its serial control for all 96 tokens,
but the GDN commit differed in all 36 layers at position 126: 28,576,928 of
29,417,472 values changed, relative L2 0.00841253, maximum absolute difference
0.46446, first changed model layer 1. The supervisor passed with 17.80 GiB
minimum host/admission availability across 75 samples and zero cgroup events.
This shows MTP2 is not required for one-live batch-path GDN drift. The similar
state deltas suggest the shared batch-row path or solo-to-batch transition,
but the current controls do not separate those causes. These are correctness
diagnostics, not performance measurements.


### Delayed batch admission with an exact 48-token solo prefix (2026-10-22)

Review found that the earlier QSA harness compared the batch arm's label
`batch-mtp2` to the exact string `batch`; its one-live and reverse-arrival
branches therefore did not activate. The earlier one-live captures submitted
both requests concurrently. They remain valid evidence that slot 0 continued
after the one-token slot 1 completed, but do not establish a delayed arrival
after slot 0's first token. The target-only numeric GDN capture used a separate
harness and did wait for slot 0's first token.

The QSA harness now selects its admission gate from the actual `--batch`
arguments. In the corrected MTP2 run, slot 0 generated 48 tokens on the solo
path before slot 1 was submitted. Both requests completed with exact serial
MTP2 token parity (96 and one token). At the first common comparable QSA states
after handoff, lengths 121 and 122, all 12 aggregate/indexer/KV hashes matched
serial. The first common divergence was at length 124; all 12 indexer and K/V
states differed, first at model layer 3. All 21 subsequent comparable samples
through length 163 retained that full-layer hash difference. The supervisor
passed with 16.92 GiB minimum host/admission availability over 138 samples and
zero cgroup events. This places the first sampled divergence after an exact
solo prefix and two exact post-transition states, during subsequent batch-slot
execution; it does not identify the operation or quantify the numeric error.
Energy was not measured. The raw traces remain local-only.

The matching all-layer GDN capture used the same corrected 48-token delayed
admission and kept slot 0 in the batch path with `STRATA_PARALLEL_SOLO=0`. At
committed positions 120 and 121, all 36 GDN layers were bit-identical to serial.
At position 123, all 36 layers differed: 28,228,404/29,417,472 floats, relative
L2 0.0142116, maximum absolute difference 0.518419, first changed model layer
1. This aligns the GDN onset with the first QSA mismatch at accepted length
124. Output remained exact at 96 tokens; minimum available host/admission
memory was 16.78 GiB over 65 samples, with zero cgroup events. The first
multi-position GDN attempt did not hold the batch slot after its peer exited
and only captured position 121; it is incomplete for positions 120/123 and is
not used in the comparison. The complete raw files (about 674 MiB combined)
remain local-only. The analyzer groups repeated STGCMT1 records by exact
position, token and capture occurrence.

### Queued-admission GDN stage check at position 119 (2026-10-22)

A follow-up used a queue-aware harness gate: after the caller consumed slot 0's
48th output token, it queued the one-token request and resumed slot 0 only after
the service registered that request as waiting for engine control. This avoids
holding the shared engine-control loop while waiting for a peer response. The
engine log shows that two already-in-flight solo tokens completed before
`STOP` took effect: the solo request ended after 50 output tokens, and slot 0
then entered the batch path with a 118-token prefix. Thus “48” is the caller-side
queue trigger; the engine-confirmed solo prefix is 50 generated tokens.

At the common committed position 119 (token 16), the serial and batch GDN stage
capture at model layer 10 was bit-identical in every recorded field (`x`,
`qkv`, `h`, gates, beta, `z`, `y`, GDN output and FFN intermediates). At layer
12, input `x` already differed in all 2,560 values (relative L2 0.00166446,
maximum absolute difference 0.00342625); downstream fields also differed.
Both layer-specific runs emitted exactly the same 96 slot-0 tokens as serial,
and the one-token competitor completed. The layer-10 exact / layer-12 changed
pair localizes where the observed difference first appears to the interval
between these captures, which includes model layer 11; it does not isolate that
layer's operation or prove a quality effect. Each supervisor passed with
17.78/17.82 GiB minimum physical availability, no cgroup memory events, dynamic
clocks, unavailable EMC readback, and no energy measurement. Reproduction
scripts and compact analyzer output are retained; raw STGDIAG5 dumps and full
logs remain local-only. A separate earlier strict gate waited for the peer's
output before resuming slot 0 and stalled because the first generator retained
engine control; it was stopped and is excluded.

Reproduce either layer with the matching `--layer` value, changing `OUT` to a
new directory for each invocation:

```sh
OUT=/tmp/strata-targetonly-layer10
python tools/integration/run_control.py --output "$OUT-supervisor" --timeout 360 --sample-clocks \
  python bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/capture_targetonly_gdn_layer12_stages.py \
  --layer 10 --output "$OUT"
python bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/analyze_targetonly_gdn_layer12_stages.py \
  --layer 10 --run "$OUT"
```

The tested executable SHA256 was `6a7c91f2127de4cbeb780c2d602c053c61592a7b97c6b73b222c559bc2acb5cc`.

An attempted STBNDY1 residual-boundary follow-up at the same position is
unsupported by the current hook: its writer explicitly skips `batch_rec_`
rows. The supervised run passed and produced one serial record but no batch
record, so there is no paired boundary comparison and no result is inferred
from that file. Supporting this capture in the batch-recursion path would
require a separate verifier change and backend rebuilds.

### Delayed-admission mode and batched-path controls (2026-10-22)

A target-only run with the same 48-token solo prefix and retained batch slot
captured positions 116–120. GDN state matched serial at positions 116–118, then
first differed at position 119/model layer 12 (21,504,738/29,417,472 values,
relative L2 0.00779578, maximum absolute difference 0.380125). At position 120,
the same first layer remained changed. Both outputs matched for all 96 tokens.
The run retained 17.93 GiB minimum host/admission availability over 133 samples
and zero cgroup events. In the MTP2 schedule, GDN was still exact at positions
120/121 and first differed at 123/model layer 1. Thus the generic target-only
batch path drifts without MTP, while MTP2 changes the first sampled layer and
position; neither state movement changed this sample's emitted tokens.

Two MTP2 negative controls repeated the delayed 48-token schedule through
position 164. `STRATA_NO_BATCH_KV_STEP=1` (per-token K/V and indexer appends)
and `STRATA_DEC_BATCH=0` (per-token decoder projections/updates) both remained
exact at QSA lengths 121/122, then differed across all 12 aggregate/indexer/KV
hashes at length 124 and every later paired sample through 163. Both slot-0
outputs matched all 96 serial tokens. Minimum host availability was 16.88 GiB
for the append control and 16.86 GiB for the decoder control; sampled cgroup
events were zero in both. Neither batched append nor batched decoder compute
alone accounts for the delayed MTP2 onset. These are state diagnostics, not
performance comparisons; energy was not measured.

### Batch-aware residual and MoE localization (2026-10-22)

The opt-in residual-boundary hook now writes `STBNDY2` records for both serial
and one-row batch-recursive runs. The version-2 header preserves the physical
batch slot (`-1` for serial); capture remains limited to target-only `T=1`
rows. With the same delayed-admission target-only schedule at position 119,
the captured layer-10 residual, branch, injection, and pre-read fields were
bit-identical. At layer 11, the batch row first differed in the captured
post-layer boundary: its branch output changed in 2,560/2,560 values (relative
L2 0.00443926, max absolute 0.000294242), while the batch-aware MoE capture
showed identical input activation, route IDs/weights, and shared-expert
output. Three routed experts
(205, 110, 90) moved from primary VRAM in serial to CPU in batch; only those
rank parts changed, and their weighted deltas explained the combined-output
delta to max residual 5.7e-9. Slot 0 still emitted the same 96 tokens as the
serial control, while the queued peer emitted one token. Minimum physical and
admission availability was 17.79 GiB with zero sampled cgroup events. These
captures localize a numerical difference to owner-dependent expert arithmetic
for this prompt and schedule; they do not establish a user-visible quality
effect or a performance effect.

A 3,000 MiB expert-cache-cap follow-up also passed supervision and preserved
the same output tokens, but is not a valid cache-only comparison: its captured
MoE input already differed (relative L2 0.00323), route weights changed, and
the shared-expert output changed. Treat this cell as an unclean diagnostic,
not evidence that increasing cache changes expert ownership or fixes the
observed difference. Full capture arrays and process logs remain local-only;
the parsers, compact analyses and reproduction harness are retained here.

### Owner-specific expert oracle (2026-10-22)

For the exact layer-11 position-119 activation, the service's serial outputs
for experts 205, 110 and 90 matched `native_expert_parity` CUDA outputs
bit-for-bit. The delayed batch outputs for those same experts matched the
native CPU outputs bit-for-bit. The two operator outputs differed in all
2,560 values for each expert (relative L1 0.849–1.380%; relative L2
0.844–1.398%). Their gate/up weights are IQ2_S and down weights IQ4_NL. Both
operator paths passed the parity tool's separate float expert-reference
checks using GGML `to_float` decoded weights. This confirms the owner-specific
arithmetic path for these expert parts, not a model-quality effect. The
supervised operator-oracle run retained 25.62 GiB minimum physical/admission
availability and zero cgroup events. It completed in 2.1 seconds; clocks were
dynamic, EMC readback was denied, and energy was not measured. The compact
comparison is `targetonly-layer11-moe-owner-oracle-analysis.json`; full
activation, output arrays and process logs are local-only.

### Committed-state consequence at position 119 (2026-10-22)

The same delayed target-only serial/batch pair also captured all committed GDN
layers at position 119/token 16. The nine captured GDN states through model
layer 10 were bit-identical; layer 12 was the first changed state after the
layer-11 MoE owner-path delta. At layer 12, 785,549/786,432 recurrent values
and 10,240/30,720 convolution values changed; combined, 795,789/817,152
values differ (relative L2 0.00170369, maximum absolute 0.0149361). Every one
of the 27 later GDN layer states also differed. Slot 0 still emitted its
serial-matching 96 tokens and the queued peer emitted one. Minimum
physical/admission availability was 17.66 GiB across 63 supervisor samples,
with zero cgroup events. This is direct committed-state evidence for one
delayed target-only sequence, not a long-chain or quality bound. The compact
analysis is `targetonly-layer11-all-gdn-commit-state-analysis.json`; the raw
paired state captures remain local-only.
