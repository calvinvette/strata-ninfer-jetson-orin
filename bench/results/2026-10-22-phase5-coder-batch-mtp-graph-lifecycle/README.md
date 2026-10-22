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

The ARM64/CUDA
candidate rebuilt with two jobs and the five focused accepted-window, batch
parity and graph tests passed. maestro1's filesystem had zero free bytes when
the HIP/SYCL rebuild was attempted, so those builds remain pending; no changes
were made to its existing artifacts. `build_maestro1.sh` and `sync_build_maestro1.sh` preserve the source-sync and
rebuild commands for after space is available.

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
