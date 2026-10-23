# Layer-40 expert-114 mirror and GDN-state follow-up — Orin — 2026-10-20

This randomized same-service pair extends the combined tested CPU Q8_1 selector
with `iq3_s/iq4_nl@layer=40`. It used the pinned Coder IQ1_M artifact from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, candidate binary SHA256
`e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`, and
seed `20261118`. Each arm sent three 512-token prompts requesting 12 outputs,
with prompt cache disabled and a 28-GiB memory supervisor.

At position 512 (token 760), layer-40 expert 114 (IQ3_S/IQ4_NL) moved CPU to
VRAM between adaptive initial and intermediate requests with identical
activation and route IDs. The captured activation SHA256 is
`0794d35d50d918c467445e82e1c8d3b8cc7c8a311e8ea4069d362db999f9b420`. Its
default standalone CPU/CUDA outputs differed in all 7,680 words at 1.33%
relative L2. The opt-in Q8_1 oracle made these outputs bit-identical. The
captured CPU service row matched the Q8_1 oracle to relative L2 `1.69e-9`.

Delayed control remained exact. In adaptive-cap8, all 12 output token IDs
matched across initial, intermediate and recovery requests, while accepted GDN
state hashes differed at every initial/recovery prefix. The first changed
position-512 activation for initial-to-intermediate moved from layer 41 to
layer 42 after adding the layer-40 mirror. Raw layer-40 GDN pre/post state
matched across the initial/intermediate transition and its post hash matched
service GDN ordinal 30. Intermediate-to-recovery raw pre-state already differed
and post-state changed 786,425/786,432 recurrent and 20,480/30,720 convolution
values. Thus this mirror resolves the selected owner-row arithmetic and
prompt-tail state through one transition, but does not fix the broader
accepted-prefix drift.

Both supervised arms passed with minimum host/admission availability above
14.13 GiB and zero cgroup memory events. Clocks remained dynamic; no performance
claim is made. The campaign manifest, raw routes, state, CPU rows, verifier
parts, logs and comparisons are retained here. Phase 5 remains open.

## Verifier-parts capture semantics cross-check

`verify-moe-parts.bin` is copied from `parts_out` after the verifier has copied
CPU-pool rows from its mapped buffer and added the GPU-hit rows. It therefore
contains the actual mixed-owner expert parts consumed by the weighted MoE
combine; it is not a CUDA-only oracle. The separate `cpu-moe-outputs.jsonl`
capture records CPU pool rows before that assembly and prints FP32 values with
nine significant digits.

The [cross-check](adaptive-cap8/result/cpu-parts-crosscheck.json) joins the
three direct CPU rows at dispatch 88 to their routed rows in `verify-moe-parts.bin`.
All three match within the JSON serialization precision (maximum absolute
difference `4.999e-10`, relative L2 at most `1.715e-9`). This confirms that the
verifier-parts capture includes the same CPU rows, while direct CPU captures
remain useful for comparison against an independent same-input oracle.
Reproduce it with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position512-layer40-expert114-mirror-state-pair/compare_cpu_parts_capture.py \
  --result bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position512-layer40-expert114-mirror-state-pair/adaptive-cap8/result \
  --output /tmp/cpu-parts-crosscheck.json
```
