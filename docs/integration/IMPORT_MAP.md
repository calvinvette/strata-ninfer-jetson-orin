# Import and adaptation map

The [manifest](../../reference/ninfer-import.json) is authoritative for imported
paths, hashes, exclusions and source origin. The reference keeps the connected
source/test/tool tree so headers, fixtures and relative imports remain available.
It is not linked by Strata's CMake build and has not been rebuilt in this checkout.

| Material | NInfer reference | Strata destination / use | Gate |
| --- | --- | --- | --- |
| Native build and capability selection | [CMakeLists](../../reference/ninfer/CMakeLists.txt), [Jetson guide](../../reference/ninfer/docs/jetson-orin.md), `src/core/device.cu` | Existing root build, setup and device discovery; standalone reference build only | ARM64/SM87 flag audit and native execution; no desktop toolkit replacement |
| Operator contracts and oracles | [public internal contracts](../../reference/ninfer/include/ninfer/ops), [operator tests](../../reference/ninfer/tests/ops), `tools/reference/`, `tools/parity/` | Strata `include/strata/kernels/`, `src/kernels/`, actual model fixtures | Matching formula, represented types and independent oracle |
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
