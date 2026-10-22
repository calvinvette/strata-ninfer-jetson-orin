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

## Resources and validation

Minimum available physical RAM and minimum admission availability were both
19,112,697,856 bytes (17.80 GiB). The six-GiB physical headroom was retained;
all sampled cgroup memory event counters, including OOM, remained zero. Dynamic
GPU observations ranged during the run; EMC readback was denied. Energy was not
attributed to the request, and no performance conclusion is drawn.

The current-source CUDA candidate built `strata` and `verify_batch_parity`.
Focused CTests passed 3/3: `verify_batch_parity`,
`captured_graph_trace_test`, and `graph_registry_lifecycle_test`. On maestro1,
the configured HIP build recompiled and linked `strata` successfully, then its
CLI help check passed. The configured SYCL target reported no work because this
CUDA verifier translation unit is not part of that target; the existing SYCL
binary's CLI help check passed. Neither backend was run on an accelerator.

The local and maestro1 source hashes match:

```text
include/strata/core/verify.hpp  6f7a80315b8fa51aa38e66c667712e89bcf96db6fb36bea118e7d07a49b85a50
src/core/verify.cpp             2398e915a99b0d72420818884b6938c55cd201ead4fd1d770222a4c89ae71fe3
```

maestro1 HIP binary SHA256: `594ec3031ad9c3e93ffd6481d981844de47c4b975b8c9c3aa6ffe69c6e3cb8d9`.
The backend checks were compile/startup evidence only and do not qualify
accelerator runtime.

The harnesses and parsers are retained as `capture_target_only_gdn_layer.py`,
`two_live_multrow_layer12.py`, `compare_layer_capture.py`, and
`compare_gdn_commit_state.py`. Raw `*.stgdiag`/`*.stgcmt` data, run logs, and
supervisor telemetry remain local and are intentionally excluded from Git.
