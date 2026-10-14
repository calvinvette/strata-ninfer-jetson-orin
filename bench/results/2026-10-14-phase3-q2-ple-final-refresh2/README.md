# Q2_0 PLE and Phase 3 regression refresh — Orin — 2026-10-14

A fresh refresh reconfirmed the completed Phase 3 Q2_0 scope on the current
checkout. The model shards and PLE pack were already under
`/home/calvin/models/strata-orin-validation/`; no model was downloaded or
copied into Git. Every check ran in its own `systemd-run --user --scope` with a
28-GiB cgroup ceiling, read-only clock sampling, the runner's six-GiB physical
availability floor, and raw tegrastats capture.

| Check | Result | Minimum host/effective availability |
| --- | --- | ---: |
| Artifact-aware Q2_0 `ple_parity --selftest` | 7/7 numerical stages, 3 tokens, worst relative L1 `1.148e-7` | 24.426 GiB |
| Selected Phase 3 accounting/ownership/PLE CTests | 15/15 passed serially | 24.462 GiB |
| Integration Python discovery | 134/134 passed | 24.507 GiB |

The exact commands were:

```sh
build/integration/candidate/ple_parity --selftest \
  --pack /home/calvin/models/strata-orin-validation/q2-ple-pack \
  --gguf /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf

ctest --test-dir build/integration/candidate --output-on-failure -j1 \
  -R '^(shared_memory_budget_test|conversation_cache_test|conversation_memory_test|vmm_test|native_dense_ple_key_test|expert_cache_per_layer_test|expert_cache_segmented_test|ple_parity|expert_cache_memory_test|expert_cache_memory_refusal|platform_memory_test|session_loop_scratch_trace_test|ple_reader_selftest|conv_cache_test|coupled_draft_test)$'

python3 -m unittest discover -s tools/integration -p 'test_*.py'
```

All three commands returned zero. Sampled cgroup pressure and OOM events were
zero. CPU/GPU clocks varied dynamically; EMC clock access was denied and board
energy was not process-attributed. Raw commands, stdout/stderr, telemetry,
tegrastats and supervisor result JSON are retained in this directory. The
candidate binaries are identified in `SHA256SUMS.txt`.

This is regression evidence for the already closed Phase 3 Q2_0 scope. It does
not price private CUDA Graph backing, qualify a native graph-disabled route,
establish a general capacity boundary, or qualify another model/backend.
