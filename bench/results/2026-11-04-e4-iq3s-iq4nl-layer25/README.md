# IQ3_S/IQ4_NL NInfer expert route

Date: 2026-11-04. Hardware: Jetson Orin AGX, SM87, CUDA 12.6. This report
records the third experimental mixed-codec tuple in the opt-in adapter.

## Operator check

The parity harness read actual ISTA-DASLab IQ3_S model weights at layer 17,
expert 183 (2,329,600-byte grouped expert blob). To avoid copying model data,
the activation input was row 0 from an already retained Coder IQ1_M layer-25
service capture. This is a cross-variant real activation, not an activation
captured from the ISTA artifact. The grouped IQ3_S/IQ4_NL candidate dispatched
once; gate/up values and all 720 hidden Q8_1 bytes matched Strata exactly.
Final output relative L2 was `9.01338933e-8`, relative L1 `6.35638274e-8`, and
maximum absolute difference `7.4505806e-9`; no output values were invalid or
unwritten. The exact harness result is in [`ista-operator-parity.log`](ista-operator-parity.log).

The existing `native_expert_parity` oracle independently accumulated the
projection reference in FP64 using GGML `to_float` weights. GPU dequantization
matched GGML bit-for-bit across 4,915,200 values. For this activation, the
Strata CPU and CUDA expert outputs were 1.36% and 1.09% relative-L1 from that
FP64 reference, respectively, and differed from each other by 1.63% relative
L1. The CUDA reference and IQ3_S implementation share GGML's canonical tables,
so this validates the adapter against Strata and FP64 arithmetic but is not an
independent IQ3_S codebook oracle. See [`native-oracle.log`](native-oracle.log).

## Service checks

An opt-in nonstrict request on the actual two-shard ISTA-DASLab IQ3_S model
used its matching `iq3-s-pack`. A temporary profile ranked all 512 layer-17
experts first, and `--expert-cache 512` made that layer resident. The service
reported GPU resident expert execution and logged the NInfer IQ3_S/IQ4_NL
dispatch at layer 17. It completed one output token (`4`) for manual token IDs
`1,2,3`; this confirms dispatch, not answer quality or throughput. Minimum
sampled available RAM was 19.81 GiB, above the 6 GiB floor. The cgroup OOM-kill
counter remained at its pre-existing value of one. Raw evidence is in
[`ista-service-smoke/`](ista-service-smoke/).

A second request on the actual Coder IQ1_M artifact used a temporary profile
with all layer-17 experts resident and disabled CPU prefill sharing. It also
logged the IQ3_S/IQ4_NL path at layer 17. Minimum available RAM was 21.19 GiB.
This corroborates Coder-family route selection; raw files are in
[`service-smoke-resident-layer17/`](service-smoke-resident-layer17/).

## Scope and reproduction

IQ3_S/IQ4_NL occurs in nine layers of both mixed artifacts. The runtime path
supports the exact 2560/640 geometry. These checks do not cover every layer,
strict full-model execution, long-form quality, grouped prefill shapes,
performance, HIP or SYCL. NInfer remains opt-in and Strata remains default.
The helper accepts 256- and 512-expert artifacts; profiles and models remain
outside Git.

```sh
build/integration/e0-cuda-build/ninfer_iq_expert_parity \
  ~/models/strata-orin-validation/ISTA-DASLab-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S/IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf \
  17 183 /tmp/e0-coder-iq3s-activation-row0.f32
```

The activation file is row 0 of the retained Coder capture at
`bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-owner-position505-506/operator-checks/expert183/layer-25-expert-183-activation.f32`.
The service JSON records complete commands, return codes and memory floors.
