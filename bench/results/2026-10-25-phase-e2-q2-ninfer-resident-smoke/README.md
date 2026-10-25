# E2 Q2_0 resident NInfer-derived execution smoke

Date: 2026-10-25  
Host: Jetson AGX Orin, aarch64, CUDA 12.6, SM87  
Branch: `feat/ninfer-expert-e0`

## Scope

This is implementation and correctness evidence for the first opt-in resident
expert route. It is not a performance qualification. The adapter handles only
Flash-Next Q2_0/Q2_0 expert tensors with hidden/intermediate widths 2560/640.
Strata remains responsible for model loading, routing, cache residency, route
weights, shared experts, residuals, scheduling and persistent state. The normal
`strata` backend remains the default. `--expert-backend ninfer` selects the new
CUDA route, and `--expert-backend-strict` rejects unsupported layouts rather
than silently falling back.

## Source and binary identity

- New CUDA source: `src/kernels/cuda/ninfer_q2_expert.cu`.
- NInfer reference commit: `b07248f2528125aeda7550055580204541f1714c`.
- The source comment maps the D3 gate/up and SiLU schedule to
  `reference/ninfer/src/ops/sparse_moe/decode/sparse_moe_decode_kernels.cu`
  (`dot_two_rows`, `sparse_moe_d3_path_tiled_kernel`) and the D4 down projection
  to (`dot_fp32_rows`, `sparse_moe_d4_token_kernel`). The Q2_0 decoder and
  Strata-specific interface are newly adapted. NInfer's Q4/Q5/Q6/W8 codecs and
  complete shared-expert/residual epilogue are not copied. License: Apache-2.0;
  the reference license remains at `reference/ninfer/LICENSE`.
- Build directory: `build/integration/e0-cuda-build`; Release target built on the
  Orin with two parallel jobs.
- `strata` SHA256 at this checkpoint:
  `527d7833ac398b82368c37b1001ed1adfdd245730b28482a90fef28851161be8`.
- `ninfer_q2_expert_parity` SHA256:
  `b10279c08d3cf90f3f0be6a166df5d0bea1cf8d0e3111d47d4be032254458f3a`.

## Operator checks

The actual Coder Q2_0 GGUF at
`~/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf`
was used without copying model data into Git. For layer 0, expert 32 and a
2,560-value captured activation, the independent FP64 scalar oracle output hash
was `86630939911b8899265cc806fefc448ce462f32958c13a150af84936fc604c9a`.
The activation is a captured Coder IQ1_M vector from the same model family, not
a Q2_0 model-native activation. The adapted single-expert GPU D3/D4 path had
relative L2 error `2.13101098e-7`, maximum absolute error `1.45426081e-8`, and
no unwritten/non-finite values against the declared FP64 limits (`5e-5`, `1e-5`).

The grouped resident path was compared with Strata's existing Q2_0/Q8_1 grouped
route for one resident entry. Relative L1 difference was `9.68860029e-8`, with
no unwritten/non-finite output. The harness observed exactly one NInfer grouped
host dispatch invocation and synchronized/read back the resulting GPU output.
This counter establishes the host enqueue call in the harness; it is not a
per-entry device-side counter. The passing output comparison demonstrates that
the queued kernels completed and wrote the tested row.

The independent Python codec/oracle unit tests pass 4/4. A previous real-payload
check sampled 32,768 Q2_0 values across eight tensors against pinned ggml and
matched bit-for-bit (see E1 contract and closeout).

## Strict service smoke and default control

A temporary local service used the documented 8K FP16 KV profile, MTP off and
3,000 resident expert slots. Under strict NInfer mode, the prompt `1+1` returned
assistant text `2` (HTTP 200; 70 prompt tokens, 40 generated tokens). The engine
logged a queued NInfer Q2_0 resident dispatch and 12,269/19,200 decode cache
hits (63.9%). The response passed basic completion checks, but no independent
answer-quality suite or sustained-service test was run.

A separate default-Strata service run returned the same text with the same token
counts and logged 6,578/19,200 cache hits (34.3%). Its engine prompt/decode rates
were 8.2/4.9 tok/s; the NInfer screen reported 19.6/9.1 tok/s. These are single,
non-randomized screening observations with different cache-hit ratios and prior
request histories. They are **not a valid paired comparison** and must not be
used to claim a performance improvement. No kernel-only timing, launch count,
register/shared-memory report or same-residency on/off ablation was collected.

The first strict service request initially failed because Strata's existing
Q8_1 SwiGLU quantizer accepts at most eight columns per call. The adapter was
changed to invoke that helper in bounded groups of at most eight; the rebuilt
strict service then completed the smoke request. This failure and correction are
retained as implementation evidence.

## Qualification limits and next work

- Implemented route is CUDA-only and supports only Q2_0/Q2_0 at 2560/640.
  HIP/SYCL builds and GPU execution were not qualified; maestro1 currently lacks
  the required compilers and has insufficient free disk for a build.
- The service invocation proves the opt-in strict Q2_0 route can serve a request,
  but does not yet prove every dispatched expert entry used it. Add device-side
  route/entry accounting or equivalent trace evidence before closing coverage.
- Re-run strict service checks with Q2_0 model-native captured activations and
  broaden edge cases (empty/partial groups, multiple groups, graph reuse and
  strict rejection of unsupported tensors).
- Complete same-day randomized paired backend-off/on measurements with matched
  resident expert IDs and bytes. Measure operator latency and complete requests,
  then follow the full E6 protocol before making any speed claim.
- The first attempt exposed the existing helper's eight-column limit; the fixed
  code now chunks calls, but maximum-capacity scratch and graph-capture behavior
  need dedicated qualification.
