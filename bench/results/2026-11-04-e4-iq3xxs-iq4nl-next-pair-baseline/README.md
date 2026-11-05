# Next mixed-codec target baseline: IQ3_XXS / IQ4_NL

Date: 2026-11-04. Hardware: Jetson Orin AGX, SM87, CUDA 12.6. This pins a
real Coder IQ1_M input and Strata reference before extending the experimental
NInfer-derived adapter to the next most common mixed tuple.

Coder IQ1_M and original ISTA-DASLab IQ3_S each contain 14 layers with
IQ3_XXS gate/up and IQ4_NL down tensors. Layer 0 is the first such Coder layer
and is also the first unsupported layer reported by strict NInfer mode. The
actual Coder layer-0/expert-70 operator was checked using two captured service
activation rows. The 2,176,000-byte expert blob decoded successfully; native
GPU dequantization matched GGML `to_float` for 4,915,200 values. Strata's
existing CUDA operator was width-invariant between one and two rows. Its
current Q8_1 GPU output differed from the CPU route by relative L1 1.52%
(5,120/5,120 output words), while the independent harness completed with zero
failures. This is a reference baseline only; it does not exercise the new
NInfer-derived backend.

The two-row activation fixture is the already retained Coder service capture
at `bench/results/2026-10-19-phase5-coder-q8-1-real-windows/layer0-dispatch0-nt2-activations.f32`.
It remains model-derived evidence and is not duplicated here. Existing
Strata-only behavior and the opt-in diagnostic history are documented in the
[IQ3_XXS Q8_1 mirror report](../2026-10-19-phase5-coder-layer0-iq3xxs-q8_1-mirror/README.md).

Reproduce from the worktree root:

```sh
build/integration/e0-cuda-build/native_expert_parity \
  ~/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --expert 70 --activation-f32 \
  bench/results/2026-10-19-phase5-coder-q8-1-real-windows/layer0-dispatch0-nt2-activations.f32 \
  --activation-rows 2 --token-width 2 0
```

## Experimental NInfer-derived adapter result

The CUDA adapter now supports this exact 2560/640 tuple. On the same layer-0,
expert-70 weights and first captured activation row, it dispatched once;
gate/up values matched Strata exactly, all 720 hidden Q8_1 bytes matched, and
the final output relative L2 was `8.92e-8` (max absolute `1.49e-8`). See
[`ninfer-parity.log`](ninfer-parity.log). This is one real expert/activation
operator check, not all-layer or whole-model correctness.

A nonstrict full-model service smoke completed one output token and logged the
new NInfer-derived IQ3_XXS/IQ4_NL dispatch at layer 0. It also logged fallback
at layer 1 (IQ2_S/Q2_0) and NInfer IQ2_S/IQ4_NL dispatch at layer 2. The
minimum sampled available RAM was 20.87 GiB; the pre-existing cgroup OOM-kill
counter remained one. This confirms dispatch in a real request, not answer
quality, throughput or full Coder support. Raw logs and memory samples are in
[`service-smoke/`](service-smoke/); service output was token `4` for the manual
token-ID prompt `1,2,3`.

A strict-mode follow-up entered the IQ3_XXS/IQ4_NL route at layer 0, then
returned the expected error at layer 1 for unsupported IQ2_S/Q2_0. This shows
the new tuple is admitted by strict selection and the next tuple is explicitly
rejected. Minimum sampled available RAM was 21.16 GiB, with no increase in the
pre-existing OOM-kill counter. See [`service-strict-reject/`](service-strict-reject/).

The adapter decodes the GGUF IQ3_XXS blocks directly and keeps the shared
IQ4_NL down kernel. It must not pass these bytes to NInfer's packed Q4/Q5
operators. Strict whole-model support, held-out quality, grouped prefill,
performance, ISTA IQ3_S runtime coverage, HIP and SYCL remain open. The
intermediate failed parity runs during sign-layout debugging are not included
as passing evidence; the final implementation was recompiled and the recorded
oracle run passed.

The service runs used a temporary `STRP` profile ranking all 256 layer-0
experts first, then all remaining layer/expert pairs. Models and that profile
stay outside Git. The service `result.json` files preserve exact flags, exit
status and memory-floor data.
