# IQ2_S/Q2_0 mixed resident expert route

Date: 2026-11-05. Hardware: Jetson Orin AGX, SM87, CUDA 12.6. This is a
CUDA-only, opt-in extension of the experimental mixed-codec selector. It reuses
the existing grouped Q2_0 down projection and adds the IQ2_S gate/up plus
Q8_1 hidden activation path for the exact 2560/640 Flash-Next geometry.

## Real-weight operator check

Coder IQ1_M layer 1/expert 5 was loaded from the actual first model shard. The
adapter dispatched once. Gate and up values matched the existing Strata
operator bitwise, all 720 hidden Q8_1 bytes matched, and the final 2,560-value
output was bit-identical (relative L1/L2 and max absolute error all zero).
The captured activation was a row from a Coder service capture at another
layer, so this validates the operator on real target weights but is not a
same-layer activation check. It does not prove whole-model output or state
parity. Raw operator output: [`parity.log`](parity.log).

## Strict service dispatch

A strict NInfer one-token Coder IQ1_M request used a temporary STRP profile with
layer 1 first and 256 resident expert slots. The log confirms grouped NInfer
dispatch at layer 1, followed by an expected strict rejection at layer 12 for
IQ3_XXS/Q2_0, the next unsupported encountered pair. The request therefore
exercises dispatch but does not return a generated token. The minimum sampled
available physical memory was 21.58 GiB, above the required 6 GiB host floor;
the cgroup OOM-kill counter remained at its preexisting value of one. Raw
supervisor and engine evidence is in [`service-strict/`](service-strict/).

## Build and reproduction

The CUDA targets `strata`, `strata-gguf` and `ninfer_iq_expert_parity` built
with one job in `build/integration/e0-cuda-build`. The parity executable hash
was `ec73ff7a8db602ff75c794dfeaa595f5bf08ad0955bdd7cd69236c43d6e68f6d` and
the service binary hash was `c75232191d0f38b4ed1834aa05c71cedc1bf315b9ad6e09e032cf61b1db15436`.

```sh
build/integration/e0-cuda-build/ninfer_iq_expert_parity \
  ~/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  1 5 /tmp/e0-coder-iq3s-activation-row0.f32
```

The activation file, model files, STRP profile and build products remain
outside Git. The selector now has four mixed tuples and covers 43/48 layers
in the two inventoried mixed artifacts. IQ3_XXS/Q2_0 (three layers),
IQ3_S/Q2_0 (one) and IQ4_XS/IQ4_NL (one) remain unsupported. No performance
advantage, broad quality result, or HIP/SYCL runtime result is claimed.
