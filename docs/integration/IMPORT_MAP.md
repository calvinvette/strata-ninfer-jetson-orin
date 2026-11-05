# Import and adaptation map

The [manifest](../../reference/ninfer-import.json) is authoritative for imported
paths, hashes, exclusions and source origin. The reference keeps the connected
source/test/tool tree so headers, fixtures and relative imports remain available.
It is not linked by Strata's CMake build and has not been rebuilt in this checkout.

| Material | NInfer reference | Strata destination / use | Gate |
| --- | --- | --- | --- |
| Native build and capability selection | [CMakeLists](../../reference/ninfer/CMakeLists.txt), [Jetson guide](../../reference/ninfer/docs/jetson-orin.md), `src/core/device.cu` | Existing root build, setup and device discovery; standalone reference build only | ARM64/SM87 flag audit and native execution; no desktop toolkit replacement |
| Operator contracts and oracles | [public internal contracts](../../reference/ninfer/include/ninfer/ops), [operator tests](../../reference/ninfer/tests/ops), `tools/reference/`, `tools/parity/` | Strata `include/strata/kernels/`, `src/kernels/`, actual model fixtures | Matching formula, represented types and independent oracle |
| Resident Q2_0 expert compute | [sparse-MoE decode schedule](../../reference/ninfer/src/ops/sparse_moe/decode/sparse_moe_decode_kernels.cu), pinned NInfer revision `b07248f2528125aeda7550055580204541f1714c` | Adapted CUDA path in `src/kernels/cuda/ninfer_q2_expert.cu`, selected from `src/core/verify.cpp` | Apache-2.0 reference attribution is in source; Q2_0/Q2_0 and 2560/640 only; exact answer/token/state parity through a 240,286-token retrieval prompt under a 262,144-token cap; performance gate fails; opt-in only |
| Resident IQ2_S/IQ4_NL expert compute | Same pinned sparse-MoE D3/D4 grouped schedule; codec traversal follows GGML IQ2_S/IQ4_NL implementation and codebooks | New CUDA adapter in `src/kernels/cuda/ninfer_iq_expert.cu`, selected from `src/core/verify.cpp` for exact 2560/640 tuple | One actual Coder IQ1_M layer-2 expert/activation operator check and nonstrict service dispatch smoke pass; strict whole-model use remains unsupported. CUDA-only and opt-in. Source file records Apache-2.0 NInfer schedule attribution and GGML MIT codec provenance; not a direct use of NInfer packed weights. |
| Resident IQ3_XXS/IQ4_NL expert compute | Same pinned sparse-MoE D3/D4 grouped schedule; IQ3_XXS/Q8_1 dot follows GGML packed-grid/sign contract | Added to the CUDA adapter in `src/kernels/cuda/ninfer_iq_expert.cu`, selected from `src/core/verify.cpp` for exact 2560/640 tuple | One actual Coder IQ1_M layer-0 expert/activation operator check and nonstrict service dispatch smoke pass; layer 1 falls back for IQ2_S/Q2_0. Whole-model mixed support remains incomplete; CUDA-only and opt-in. |
| Resident IQ3_S/IQ4_NL expert compute | Same pinned sparse-MoE D3/D4 grouped schedule; IQ3_S/Q8_1 dot follows GGML packed grid, high bits, signs and group scales | Added to the CUDA adapter in `src/kernels/cuda/ninfer_iq_expert.cu`, selected from `src/core/verify.cpp` for exact 2560/640 tuple | One operator check on actual ISTA weights with cross-variant Coder activation; nonstrict dispatch smoke on actual IQ3_S service with 512 layer experts resident. Whole-model support remains incomplete; CUDA-only and opt-in. |
| Resident IQ2_S/Q2_0 expert compute | NInfer grouped D3 schedule with GGML IQ2_S dot; reuses the existing grouped Q2_0 D4 implementation | Added as a mixed tuple in `src/kernels/cuda/ninfer_iq_expert.cu` with the shared down helper in `src/kernels/cuda/ninfer_q2_expert.cu`; selected from `src/core/verify.cpp` for exact 2560/640 tuple | One actual Coder IQ1_M layer-1 expert operator check and strict service dispatch pass; activation was captured from another layer. CUDA-only and opt-in. |
| Resident IQ3_XXS/Q2_0 and IQ3_S/Q2_0 expert compute | GGML IQ3_XXS/IQ3_S gate-up dots with the shared grouped Q2_0 D4 projection | Added to `src/kernels/cuda/ninfer_iq_expert.cu`, selected from `src/core/verify.cpp` for exact 2560/640 tuples | One Coder real-weight operator check each with cross-layer captured activations; strict service dispatch checks pass. CUDA-only, opt-in; model quality/performance not qualified. |
| Resident IQ4_XS/IQ4_NL expert compute | GGML IQ4_XS 6-bit sub-block scales and IQ4_NL codebook with the grouped D3/D4 schedule | Added to `src/kernels/cuda/ninfer_iq_expert.cu`, selected from `src/core/verify.cpp` for exact 2560/640 tuple | One Coder real-weight operator check with cross-layer captured activation; strict one-token traversals pass on Coder and actual ISTA artifact. CUDA-only, opt-in; quality/performance not qualified. |
| Sparse-MoE codec boundary | [NInfer QType definitions](../../reference/ninfer/src/core/tensor.h), [sparse-MoE contract](../../reference/ninfer/include/ninfer/ops/sparse_moe.h), [decode kernels](../../reference/ninfer/src/ops/sparse_moe/decode/sparse_moe_decode_kernels.cu) | Seven exact Flash-Next GGUF codec pairs now have CUDA adapters; NInfer's packed weights remain unconsumed | Reference operator admits packed Q4G64/Q5G64, Q4G64/Q6G64, and W8G32/W8G32 routed profiles. Flash-Next GGUF codecs are not byte-compatible; adapters decode the original layouts. Other codecs/geometries need their own contracts and real-payload checks. |
| Q4/Q5 attention scheduling | [projection source](../../reference/ninfer/src/ops/attn_input_proj/q4_q5), [test](../../reference/ninfer/tests/ops/test_attn_input_proj.cpp) | Candidate projection optimization after quantization/layout mapping | Test actual shapes and small-T dispatch; measure end-to-end |
| Cooperative GDN projection | [GDN plan](../../reference/ninfer/src/ops/gdn_gating_proj/bf16/bf16_gdn_gating_proj_plan.cpp), `tests/ops/test_gdn_gating_proj.cpp` | Strata GDN/prefill path if equivalent | Actual-device residency, fallback, numerical and state qualification |
| Arena/graph ownership | [arena](../../reference/ninfer/src/core/arena.cu), [graph](../../reference/ninfer/src/core/decode_graph.cpp), `tests/test_arena.cpp`, `tests/test_decode_graph.cpp` | Strata allocation and graph owners | Sequential ownership, address stability, resize and teardown |
| Scheduling/resources | [runtime](../../reference/ninfer/src/runtime), [resource contract](../../reference/ninfer/docs/maintainer/resource-scheduling-and-context-cache.md), `tests/test_resource_manager.cpp` | Adapt admission/unique-resource semantics to Strata's existing owners | Shared LPDDR, cgroups, peak transitions, active-request guarantee |
| KV and continuation | [paged KV](../../reference/ninfer/src/core/paged_kv_cache.cpp), [family runtime](../../reference/ninfer/src/targets/qwen3_6/impl/runtime), `tests/targets/qwen3_6/` | Existing Strata KV/context storage after ownership audit | Typed layouts, exact prefix identity, COW/refcounts and complete state |
| Speculation and ReplaySSM | [replay contract](../../reference/ninfer/docs/maintainer/replayssm-gdn.md), `src/core/gdn_replay_records.*`, `src/ops/launcher/mtp_round.cu`, `tests/ops/test_mtp_round.cpp` | Strata MTP, GDN and conv commit/rollback | Accepted-prefix state checks; no model-family assumption |
| Matrix and reporting | [matrix tool](../../reference/ninfer/tools/bench/run_ninfer_bench_matrix.py), `tools/bench/ttft/`, [benchmark source](../../reference/ninfer/bench) | New campaign adapter plus existing Strata API/context tools | Exact flags/schema, actual token counts, medians and failed cells |
| Host-pressure telemetry | [guard](../../reference/ninfer/tools/bench/run_with_host_pressure.py) | Adapt with Strata headroom, precheck, bounded termination and cgroup checks | Process cleanup and partial-result tests before unattended use |
| Historical findings | [ledger](../../reference/ninfer/NINFER_JETSON_ORIN_PORT_EXPERIMENTS.md), [status](../../reference/ninfer/NINFER_JETSON_ORIN_PORT_STATUS.md), [raw reports](../../evidence/ninfer-orin/README.md) | Hypothesis selection, rejection ledger and separate historical cohorts | Preserve model, clocks, format and raw-report scope |

## Keep the negative results

- R64C128S2 improved the measured Q4/Q5 attention operator from 21.648 to
  13.570 ms at T=1024. Its paired whole-engine historical PP result changed
  235.01 to 242.28 tokens/s; TG was 10.976 versus 10.981. The scales of these
  gains differ. Source: the copied experiment ledger, Phase 8 table.
- C64/C96 SwiGLU tiles, several GDN tiles, `ca` loads, individual scales and
  ping-pong fragments did not beat their measured controls. Keep reasons instead
  of reintroducing them as presumed Orin improvements.
- The best MTP window changed with model and prompt/output workload. Short
  35B-A3B preferred draft-2; its long workload preferred draft-4. Do not copy a
  single global MTP setting from another model.
- A 40,960-token NInfer capacity attempt stopped at a 1.2 GiB guard. That is a
  pressure boundary, not a successful inference point. Strata's 256K ingestion
  evidence uses another model/cache policy and does not negate this limit.
- Async allocation passed an allocation-class test but did not establish an
  end-to-end or graph-lifetime advantage; explicit allocation stayed selected.

## Snapshot handling

NInfer's original `AGENTS.md` is preserved as `UPSTREAM_AGENT_GUIDANCE.md` for
provenance, not as current instructions. It contains historical desktop/product
assumptions. Root `AGENTS.md` and this integration plan govern the new project.
Three large frequency-ranking data files and local editor/agent settings are
excluded; frequency-training tools need those fixtures from the source port.
No models, build products, environments or profiler binaries were copied.

Retain existing copyright headers and adjacent licenses. When promoting or
modifying a source file, add its source revision/path and an adaptation notice in
the file or a neighboring provenance record. Do not relabel imported Apache code
as MIT-only. Update the import manifest only for an intentional new reference
snapshot; adaptations belong in the active Strata tree with their own history.
