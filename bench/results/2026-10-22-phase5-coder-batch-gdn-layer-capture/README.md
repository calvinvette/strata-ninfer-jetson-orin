# Coder layer-12 GDN capture for delayed target-only batch mode

This diagnostic pairs the target-only serial verifier with the batch scheduler
around the previously observed delayed-admission state change. It adds opt-in
per-row positions and slot IDs to the activation record so a batch row is joined
to the correct serial token. It does not qualify serving performance or locate
the first changed operation in the full model.

## Run

- Date and device: 2026-10-22, Jetson AGX Orin, ARM64/CUDA build.
- Model: `Qwen3.8-Flash-Next-Coder-GGUF-IQ1_M`, both GGUF shards under
  `~/models/strata-orin-validation/Coder-GGUF/IQ1_M/`, with the local expert
  pack and profile from the harness configuration.
- Greedy target-only generation, 96 tokens, batch capacity 2. Slot 1 is admitted
  after slot 0 has emitted 48 tokens and requests one token. Captured layer 12
  at positions 118, 119 and 120.
- Supervised by `tools/integration/run_control.py --sample-clocks`; the exact
  invocation is in the local supervisor metadata. No model or raw activation
  dump is stored in Git.

The serial and batch slot-0 outputs were exactly equal for all 96 tokens; slot 1
returned one token. The capture contains three serial rows and three batch rows.
Position 118/token 11393 is bit-identical. At position 119/token 16, the first
captured field `x` differs in 2,560/2,560 values (relative L2 0.001664, maximum
absolute difference 0.003426); QKV and all later captured fields also differ.
At position 120/token 13, all captured fields differ as well. Batch rows carry
slot 0 and positions 118–120, matching the scheduler arguments. This supports
the prior selected-position observation that state is exact through 118 and
differs at 119, while adding layer-12 activation detail. It does not establish
that `x` is the model-wide first changed operation; earlier layer outputs were
not captured in this run.

The batch scheduler reported four windows averaging 1.00 rows. Therefore this
run did not capture a multirow verifier window and cannot explain the separate
two-live-request mismatch. It remains a delayed-admission batch-mode diagnostic.
The prior batch-MTP and two-live target-only tests remain the relevant multirow
evidence.

## Two-live multirow follow-up

A second supervised run used two simultaneous target-only Coder requests with
the existing `--batch 2` reproducer settings, but captured independent fresh
serial controls and batch slot rows at positions 120–132. The batch output
again matched slot 0 and first differed from the slot-1 serial control at
generated token index 60. The engine processed 96 windows at an average 1.96
rows per window, confirming that this run includes actual multirow verifier
work. Both batch slots map to their matching fresh serial prompt in the
captured pre-mismatch rows.

At position 127, physical slot 1 consumed token 11 in both batch and serial.
All ten captured layer-12 fields differed before the output token at index 60
diverged. The first listed field, layer-12 input `x`, differed in all 2,560
values (relative L2 0.06058, maximum absolute difference 0.16310); `gdn_out`
relative L2 was 0.04090. At position 120, the same slot/token pairing already
had a changed `x` (relative L2 0.01563), so this selected capture does not bound
the onset. The earlier accepted-state sweep found drift much earlier, at
position 69 for this row. These layer-12 values show that the hidden numerical
state is already different before the known output mismatch, but do not locate
the first changed model operation or prove which field causes the argmax
change.

The three supervised arms retained at least 17.53 GiB available physical RAM;
all 104 sampled cgroup records had zero `low`, `high`, `max`, `oom`, and
`oom_kill` events. The six-GiB host headroom remained in effect. Dynamic clocks
were observed without intervention, EMC readback was denied, and energy was
not attributed to requests. No performance claim is made. The compact paired
field report is `two-live-layer12-summary.json`; raw activations and full run
telemetry remain local.

A repeat restricted to positions 125–127 reproduced the same slot-1 token-60
output mismatch and the same 1.96-row average. For both batch slots, consumed
tokens and every captured layer-12 array at positions 125, 126 and 127 were
bit-identical between the two runs. The repeated run retained 17.52 GiB minimum
available RAM and zero nonzero sampled cgroup memory events. This confirms
repeatability for the selected prompt pair and current build, not across other
prompts or configurations. See `two-live-layer12-repeat-check.json`.

An early-boundary follow-up also captured the directly committed GDN state at
layer 12 for positions 68–72. Slot 0's state matched its fresh serial control
through position 70, then differed at position 71 (796,604/817,152 values,
relative L2 0.003790); its layer-12 input `x` was exact at 70 and changed at 71
(relative L2 0.009436). Slot 1's state already differed at the first selected
position 68 (796,640/817,152 values, relative L2 0.008221), and its `x` also
differed there (relative L2 0.02354). The slot-1 onset is therefore earlier
than or at 68, outside this capture. Both rows' consumed tokens match their
serial controls at these positions, and slot 1's first output mismatch remains
token 60. The overlapping layer-12 activation rows repeated bit-for-bit against
the activation-only early-boundary run. These are layer-12 state/activation
comparisons; they do not establish the first changed state across all model
layers or identify a responsible operation. The supervised run retained 17.49
GiB minimum available RAM and zero nonzero sampled cgroup memory events. See
`two-live-early-boundary-summary.json`.

## Short all-layer committed-state boundary

A separate six-token two-live run captured all 36 GDN committed states at
positions 68 and 71, with the same layer-12 activation trace. Both requests
returned six tokens matching their fresh serial controls; this run stops before
the known output mismatch at token 60. Mapping each physical batch row to the
serial control by its complete set of GDN state deltas gave a unanimous 36/36
layer vote. In this run, physical slot 0 maps to serial prompt 1 and slot 1 to
serial prompt 0, illustrating why the numeric slot cannot serve as request
identity.

For slot 0 / prompt 1, all 36 committed layer states were bit-exact at position
68; by position 71 the first changed GDN layer was model layer 2 (relative L2
0.000707, with two exact layers remaining). Its layer-12 input `x` differed at
position 71 (relative L2 0.01067). For slot 1 / prompt 0, only four committed
GDN layers were exact at position 68, and the first changed layer was model
layer 5; at position 71 the first changed layer was model layer 4. Its layer-12
input `x` differed at position 68 (relative L2 0.01538) and position 71
(0.01278). Since the batch-to-prompt slot assignment differed from the longer
run, these boundaries are reported for this run's own nearest-state mapping.
They do not by themselves explain the later token-60 mismatch.

The six-token run processed six windows averaging 1.33 rows. It retained 17.46
GiB minimum available physical RAM with zero nonzero sampled cgroup events. The
all-layer `.stgcmt` files are local-only; the compact per-layer analysis is
`two-live-all-layer-state-68-71-summary.json`. This run's profiling capture
adds substantial commit-copy work and is correctness evidence only.

## Layer-1 MoE output boundary

A follow-up used the same six-token two-live workload and sampled layer 1 at
positions 68 and 71. The opt-in `STRATA_VERIFY_DUMP_MOE_OUTPUT_BATCH=1` format
records the shared-expert vector and combined MoE output with each verifier
row's position, physical slot, and consumed token. The full set of 36 committed
GDN states mapped slot 0 to prompt 0 and slot 1 to prompt 1 in this run.

At position 68, all captured layer-1 fields matched both controls for the
mapped rows. At position 71, slot 0/prompt 0 remained exact. For slot 1/prompt
1, `x`, GDN intermediates/output, and MoE input `ffn_x` remained exact; the
shared-expert output was also exact. The combined MoE result (`ffn_y`) differed
in all 2,560 values, with relative L2 `0.00086265` and maximum absolute
difference `0.00004228`. The same result appears in the dedicated shared and
combined output capture. All six generated tokens still matched their fresh
serial controls; this run stops before the known token-60 mismatch.

This localizes a small numerical change to routed expert output/combination or
related per-row state at this boundary. It does not identify the expert or
operation that introduced it. The batch processed six windows averaging 1.33
rows and retained 17.465 GiB minimum available physical RAM; sampled cgroup
memory event counters stayed zero. Energy was not attributable to requests and
EMC readback was denied. This is correctness evidence, not a performance
measurement. The compact result is `two-live-layer1-moe-output-summary.json`;
raw captures remain local.

A longer follow-up captured layer-1 activations, committed layer-1 state and
shared/combined MoE output at positions 68, 71 and 118–127 while two requests
ran for 96 tokens. Fresh serial controls and the layer-1 state at each selected
position mapped physical slot 0 to prompt 1 and slot 1 to prompt 0. Prompt 1's
layer-1 state was exact at position 71, but `ffn_y` and the combined MoE output
already differed there (relative L2 `0.00086265`); its MoE input and shared
output matched. At positions 118–127, both requests had changed layer-1 state,
GDN fields and MoE inputs; shared and combined MoE outputs also differed. The
96-token output mismatch for prompt 1 remained at generated token index 60.
These captures show that the small position-71 combine-boundary difference
precedes larger later deltas, but do not establish that it causes the token
mismatch or identify an expert. The run processed 96 windows averaging 1.96
rows, retained 17.434 GiB minimum available physical RAM, and had zero
nonzero sampled cgroup event counters. Because state capture adds work, its
window timing is not performance evidence. See
`two-live-layer1-moe-long-chain-summary.json`; raw captures remain local.

## Route and expert-output isolation

The next six-token trace adds opt-in batch captures for route IDs/weights and
the ten per-expert output vectors at layer 1. At position 71 for prompt 1, the
batch row uses the exact serial route IDs and weights. Nine expert output
vectors are bit-identical; rank 8, expert 11, differs in all 2,560 values
(relative L2 `0.01336`, max absolute `0.0008242`). Its router weight is
`0.051304`. The weighted expert-11 delta reproduces the combined MoE output
delta: the residual is at most `3.24e-9` per value and `0.00484%` of the
observed delta in L2. This isolates the selected combined-output change to
expert 11's output path for this row and configuration. It does not explain why
expert 11 differs or establish a causal link to the later token-60 mismatch.

Both generated continuations match their serial controls for all six tokens.
The batch averaged 1.33 rows/window and retained 17.643 GiB minimum available
physical RAM; sampled cgroup event counters stayed zero. Energy was not
attributed and EMC readback was denied. The route/parts capture is correctness
instrumentation, not performance evidence. The compact result is
`two-live-layer1-expert11-summary.json`; raw `.parts`, route, activation, state
and output files remain local. `compare_moe_route_parts_batch.py` replays the
route, per-expert, weighted-output and combined-output comparison from those
files plus the same-run slot mapping.

## Resources and validation

Minimum available physical RAM and minimum admission availability were both
19,112,697,856 bytes (17.80 GiB). The six-GiB physical headroom was retained;
all sampled cgroup memory event counters, including OOM, remained zero. Dynamic
GPU observations ranged during the run; EMC readback was denied. Energy was not
attributed to the request, and no performance conclusion is drawn.

The current-source CUDA candidate built `strata` and `verify_batch_parity`.
Focused CTests passed 3/3: `verify_batch_parity`,
`captured_graph_trace_test`, and `graph_registry_lifecycle_test`. Maestro1
rebuilt and linked the configured HIP targets with one build job; its SYCL
target reported no work because the CUDA verifier translation unit is not in
that target. Both configured binaries passed their CLI help checks. The source
files used for the backend build match the local tree:

```text
include/strata/core/verify.hpp  75595d43c82ad36764f275a945cc30a45d8b072929dd3937c0599dd1de7cf7c3
src/core/verify.cpp             9d6a41162b930197045155d66da0cfdd80d8e10b796f2b8b8e879f45ffe44d5f
src/program/generate.cpp        de1258c0fc439883c424562b58201d8d486e34a9a8cefbaffa22ae12390d16ba
```

The HIP and SYCL binary hashes were
`4e98c335be392c385e0aeeac74dcf1cf747159814a72d88e7e585a67377b2cd5` (HIP) and
`9233e5ad6b07e83180a8fc4b542c0d7e47e92c6d3e870ec9efa5232b07acb985` (SYCL).
These are compile/startup checks only; neither backend had accelerator-runtime
coverage.

The harnesses and parsers are retained as `capture_target_only_gdn_layer.py`,
`two_live_multrow_layer12.py`, `compare_layer_capture.py`,
`compare_gdn_commit_state.py`, `compare_moe_output_v2.py`, and
`compare_moe_route_parts_batch.py`, and `compare_moe_dispatch_owner.py`. The MoE comparators use same-run slot
mapping from committed-state comparisons. Raw
`*.stgdiag`/`*.stgcmt`/`*.stmoe`/`*.parts` data, route logs, run logs, and
supervisor telemetry remain local and are intentionally excluded from Git.

## Dispatch-owner follow-up

An opt-in dispatch-owner trace was joined to the mapped serial rows by exact
layer-1 activation. At position 71, prompt 1 / physical slot 1 uses the same
expert IDs as serial, but rank 8 (expert 11) changes from primary VRAM in the
serial control to CPU in the batch dispatch (dispatch 3601). The captured CPU
owner output for that exact dispatch agrees with the batch expert-part vector
to maximum absolute difference `5.0e-11` (JSON decimal serialization rounding).
This associates the previously isolated part delta with a CPU/GPU owner change;
it does not prove a causal link to the later token-60 mismatch. On the exact
prompt-1 activation, the serial GPU part matches the independent GPU oracle
bit-for-bit and the batch CPU part matches the CPU oracle bit-for-bit. The
CPU/GPU oracle outputs differ in all 2,560 values (relative L2 `0.01335`),
confirming the selected owner-dependent output change for this row.

A prompt-0 follow-up used the complete one-token CPU result from
`native_expert_parity` with an activation whose SHA256 is
`c505ebecc573356933ae046779205b31af31242d1b60d0eac328ab12f78a2ac5`. Both the
serial CPU output and batch dispatch 3505 match all 2,560 oracle values after
float parsing; the largest remaining difference (`5.0e-11`) is JSON decimal
serialization. The earlier reported relative-L2 difference of about `2.19`
came from accidentally comparing prompt 0 against an oracle artifact carrying
prompt 1's activation hash. The prompt-0 CPU oracle discrepancy is resolved as
a comparison-selection error. This does not explain prompt 1's genuine CPU/GPU
owner-dependent output difference. The selected layer-1 expert-11 blob in
`experts.bin` matches the source GGUF tensors byte-for-byte (SHA256
`6310f659...bd7b85ae`), ruling out a wrong packed blob for this expert.
The compact per-row results are in `two-live-layer1-expert11-oracle-summary.json`;
large activations and oracle dumps remain local. The other sampled prompt/position rows do not show
this owner change. The large CPU-output traces and owner JSONL files remain
local and are excluded from Git. The opt-in capture switch and exact row join
are reproducible with `two_live_multrow_layer12.py --capture-moe-owners` and
`compare_moe_dispatch_owner.py`; see `two-live-layer1-owner-summary.json`.
