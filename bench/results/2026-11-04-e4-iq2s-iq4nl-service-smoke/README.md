# IQ2_S/IQ4_NL NInfer adapter operator and service smoke

Date: 2026-11-04. Hardware: Jetson Orin AGX, SM87, CUDA 12.6. This is the
first functional check of the opt-in mixed-codec adapter. It is not an
end-to-end performance or model-quality qualification.

## Operator check

The parity harness used Coder IQ1_M layer 2, expert 174, and the first
2,560-value row of the retained layer-2 service activation at
`/tmp/e0-iq2s-iq4nl-ggml-reference/layer-2-expert-174-activation.f32`.
The three-row capture was not copied into Git. The exact GGUF expert blob was
1,971,200 bytes. The NInfer-derived grouped CUDA route dispatched once. Gate
and up outputs matched Strata exactly; the intermediate hidden Q8_1 payload
matched all 720 bytes. Final output had relative L2 `8.76624254e-8`, relative
L1 `6.07030271e-8`, max absolute difference `7.4505806e-9`, and zero invalid or
unwritten values. The small final delta comes from reduction arithmetic.

The harness checks that its NInfer workspace request equals Strata's grouped
scratch size before allocating. Every CUDA allocation and transfer is checked.
The rebuilt parity executable SHA256 is
`89e4ec2e94dc7f820667ae7c9c4de4758a80036c86cf0aadc6ae7e5b66e1bb56`.

## Runtime smoke

An opt-in `--expert-backend ninfer` request loaded the Coder IQ1_M model using
the model-matched pack and both GGUF shards. Its profile made the 256 layer-2
experts resident. The nonstrict request completed and the service log showed a
resident IQ2_S/IQ4_NL grouped dispatch at layer 2. Unsupported codecs used the
existing Strata fallback. This is one generated token and proves route
selection/execution only; it does not assess answer quality or throughput.
The 12 memory samples recorded a 21.72 GiB minimum available-memory floor,
well above the 6 GiB admission floor. The observed cgroup OOM-kill counter was
1 at both start and end; it did not increase during this run.

The strict-mode request intentionally returned failure at layer 0 because its
pair is IQ3_XXS/IQ4_NL, which remains unsupported. Seven memory samples showed
21.20 GiB minimum available RAM. This confirms explicit rejection rather than
silently treating the whole mixed model as supported.

## Limits and reproduction

Only Coder IQ1_M layer 2/expert 174 was numerically checked against Strata.
The IQ2_S/IQ4_NL pair appears at 15 layers in both Coder IQ1_M and original
ISTA-DASLab IQ3_S inventories, but the new adapter has not been exercised on
all those layers or on the IQ3_S model. Six other mixed codec pairs remain
unsupported. No matched request performance, quality suite, prefill-shape
matrix, staged-expert route, HIP or SYCL build is claimed. NInfer remains
opt-in; Strata remains the default backend.

The raw service logs and memory samples are in this directory's
`control-spec2/` and `control-strict-reject/` subdirectories. The one-row
activation extraction used for the operator run was temporary. Reproduction
commands from the worktree root:

```sh
python3 -c 'p="/tmp/e0-iq2s-iq4nl-ggml-reference/layer-2-expert-174-activation.f32"; b=open(p,"rb").read(); open("/tmp/e0-layer2-expert174-row0.f32","wb").write(b[:2560*4])'
cmake --build build/integration/e0-cuda-build --target ninfer_iq_expert_parity strata -j1
build/integration/e0-cuda-build/ninfer_iq_expert_parity \
  ~/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  2 174 /tmp/e0-layer2-expert174-row0.f32
```

The C++ adapter attributes its grouped schedule to the pinned NInfer sparse
MoE decode source and its codecs to GGML; Strata retains routing, weighting,
shared expert and residual semantics. See [import map](../../../docs/integration/IMPORT_MAP.md)
and [E4 model coverage](../2026-10-25-phase-e4-model-codec-coverage/README.md).
