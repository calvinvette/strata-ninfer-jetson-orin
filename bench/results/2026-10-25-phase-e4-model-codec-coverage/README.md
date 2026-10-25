# E4 model, codec and grouped-shape coverage

Date: 2026-10-25. Source: current `feat/ninfer-expert-e0` worktree on Orin AGX
(SM87, CUDA 12.6). This is a bounded capability inventory and functional
operator check. It does not qualify 64/128-token service prefill, mixed codecs,
other backends, or end-to-end performance.

## Result

| Artifact | Routed expert inventory | NInfer Q2_0 adapter coverage | Status |
| --- | --- | --- | --- |
| ISTA-DASLab Coder Q2_0, `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0` | 48 layers; gate/up/down Q2_0, 2560/640; metadata reports 512 experts, top-10 | Q2_0/Q2_0 on CUDA; resident, staged and direct-mapped prototype paths exercised in E2/E3 | Bounded functional support; performance rejected against Strata |
| ISTA-DASLab Coder IQ1_M | 48 layers; expert count 256, top-10; gate/up: IQ2_S 20 layers, IQ3_S 10, IQ3_XXS 17, IQ4_XS 1; down: Q2_0 9, IQ4_NL 39 | No complete layer codec tuple supported | Partial/unsupported in strict NInfer mode; Strata fallback remains |
| ISTA-DASLab original IQ3_S | 48 layers; expert count 512, top-10; gate/up: IQ2_S 20 layers, IQ3_S 10, IQ3_XXS 17, IQ4_XS 1; down: Q2_0 9, IQ4_NL 39 | No complete layer codec tuple supported | Partial/unsupported in strict NInfer mode; Strata fallback remains |

The mixed-codec counts above are tensor counts across 48 layers for each of
`gate_exps`, `up_exps` (same distribution), and `down_exps`. The nine Q2_0
down tensors in each mixed artifact do not make any complete expert route
eligible: gate/up use other codecs at those layers. Tensor codec and model
expert-count differences are artifact-specific; the Q2_0 contract must not be
generalized to IQ1_M or IQ3_S.

## Grouped prefill-shaped functional check

The `ninfer_q2_expert_parity` harness ran against real Q2_0 weights at layer 0,
expert 32 and a captured layer-0 activation fixture. The same source file also
runs the one-token resident operator screen. Results from the corrected fixture
pairing:

- NInfer-derived D3/D4 vs the independent FP64 reference: relative L2
  `2.13101098e-7`, max absolute error `1.45426081e-8`, zero unwritten values;
  PASS (limits `5e-5`, `1e-5`).
- Grouped one-token route vs Strata Q2_0/Q8_1: relative L1
  `9.68860029e-8`, zero unwritten values, one NInfer dispatch; PASS.
- Three input tokens, three expert groups, nine output entries, nontrivial token
  and destination permutations: grouped relative L1 `9.59275152e-8`, zero
  unwritten values, one NInfer dispatch; PASS. This exercises the current
  grouped pointer/mapping interface and multiple 8-entry SwiGLU quantizer
  chunks. Activations for tokens 1 and 2 are deterministic transformations of
  the captured activation, so this is a shape/functional check, not a held-out
  runtime prompt distribution.
- Full top-10 grouped cases pass at 64 tokens / 640 entries and 128 tokens /
  1,280 entries against Strata's grouped Q2_0/Q8_1 implementation. Relative L1
  was `9.32514352e-8` and `9.32202759e-8`, with zero unwritten outputs and one
  NInfer dispatch in each case. All 10 experts per token use actual weights
  from layer 0; activation rows are deterministic transformations of the
  captured row. Input quantization was chunked at the helper's eight-token
  limit. These are functional operator boundary checks, not serving latency
  measurements or a natural prompt activation distribution.
- One-token operator timeline: Strata median `24.642 us` (range `24.550–24.665`);
  NInfer-derived median `86.090 us` (range `85.329–156.094`), or `3.494x`
  slower. This is a diagnostic GPU operator comparison, not service latency.

A first invocation paired the layer-0/expert-32 reference with an unrelated
layer-9/expert-233 activation and failed as expected. It is excluded as an
invalid fixture pairing; the test was rerun with the documented layer-0,
expert-32 activation and passed. The failed invocation did not modify code or
model artifacts. The corrected parity output is saved in [`parity.log`](parity.log);
the Python oracle checks passed 4/4 in [`python-tests.log`](python-tests.log).
The initial parity executable SHA256 is
`a83da2593bfe3b3e13d4de6e5fdb9003c58c7eb9acece533f4931edd9278778d`;
the rebuilt executable with 64/128-token checks has SHA256
`8302adccc5f0bb2ca63293a6923d416753bd929cfc9da0f2ac65721cb2d1def4`. The
full passing output is in [`prefill-boundary-parity.log`](prefill-boundary-parity.log).
The [initial failed harness call](prefill-boundary-first-attempt.log) documents
the eight-token helper limit and correction. The run
sampled RAM at 5.6/30.7 GiB peak, GPU utilization at 92–98%, and SoC temperature
around 49 °C; see [`prefill-boundary-tegrastats.log`](prefill-boundary-tegrastats.log).
GPU clock-rate readback was unavailable.
This timing was repeated with `tegrastats` sampled every 100 ms; it returned
Strata `24.478 us` (24.409–24.506) and NInfer `85.680 us` (85.473–136.539),
ratio `3.500x`. During the run RAM use was 4.9/30.7 GiB, GPU utilization was
92–98% in active samples, SoC temperature was 48–49 °C, and reported GPU/SoC
power ranged from 5.6 to 23.2 W. `nvidia-smi` does not expose Orin clocks here,
and no GPU clock rate readback was available; CPU clock samples ranged from
729 MHz to 2.2 GHz. The raw trace is in [`tegrastats.log`](tegrastats.log),
and this clock-observed rerun's parity/timing output is in
[`parity-clocked.log`](parity-clocked.log). The wide candidate range is retained
and further limits precision of this small operator screen.

## Reproduction and evidence

Header inventories use `tools/integration/inventory_tensors.py`, which reads
GGUF metadata/tensor descriptors and does not copy or read tensor payloads.
The full JSON records are in [`inventory/`](inventory/). The model files remain
outside Git under `~/models/strata-orin-validation/`.

```sh
python3 tools/integration/inventory_tensors.py \
  --shard ~/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --output /tmp/coder-iq1m-inventory.json
python3 tools/integration/inventory_tensors.py \
  --shard ~/models/strata-orin-validation/ISTA-DASLab-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S/IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf \
  --output /tmp/iq3s-inventory.json
cmake --build build/integration/e0-cuda-build --target ninfer_q2_expert_parity -j2
build/integration/e0-cuda-build/ninfer_q2_expert_parity \
  ~/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf \
  0 32 bench/results/2026-10-15-phase5-activation-error-decomposition/weights-and-outputs/layer-0-expert-32-activation.f32 \
  /tmp/e2-q2-reference.f64 /tmp/e4-q2-expert32-output.f32
```

The inventory scope is header/codec geometry only, not element-level numerical
qualification. Q2_0 route parity reuses the E2 real-weight FP64 fixture and is
cross-variant activation evidence, not Q2_0-model-native activation evidence.
The E2/E3 reports hold the service and staged/direct mapping details. This E4
result closes only the bounded Q2_0 grouped-shape check and explicit partial
coverage decision; 64/128-token performance, codec expansion, strict rejection
against each mixed model, and HIP/SYCL builds remain open.
