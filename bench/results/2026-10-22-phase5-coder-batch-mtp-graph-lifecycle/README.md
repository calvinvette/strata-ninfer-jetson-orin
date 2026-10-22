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
- `backend-builds-maestro1/`: exact-source HIP/SYCL build and help logs;
  compile evidence only.
- `run-retry/`, `run/`, and earlier supervisor directories preserve failed or
  superseded harness attempts; they are not used for the result above.

The harness is `tools/integration/batch_mtp_graph_lifecycle.py`. The test is
not a phase gate pass. Phase 5 remains open. Near-term work is to add opt-in
per-slot terminal state diagnostics, compare one-live and concurrent runs with
identical arguments, isolate the first divergent shared-window operation, then
exercise actual graph-pool eviction and recapture.
