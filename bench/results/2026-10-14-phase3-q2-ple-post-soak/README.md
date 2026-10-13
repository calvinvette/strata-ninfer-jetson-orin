# Q2_0 PLE regression refresh after sustained run — Orin — 2026-10-13

The current CUDA candidate passed a fresh artifact-aware Q2_0 PLE self-check,
the selected Phase 3 accounting/ownership/graph CTests, and integration Python
discovery. The Q2_0 weights and PLE pack were already present in
`/home/calvin/models/strata-orin-validation/`; no model was downloaded or copied
into the repository.

| Check | Result | Minimum host availability |
| --- | --- | ---: |
| Artifact-aware `ple_parity --selftest` | 7/7 numerical stages; 3 tokens; worst relative L1 `1.148e-7` | 24.427 GiB |
| Selected Phase 3 CTests | 15/15 passed, serial | 24.418 GiB |
| Integration Python discovery | 124/124 passed | 24.516 GiB |

Each command ran in a separate `systemd-run --user --scope` with a 28-GiB
cgroup ceiling and the runner's 6-GiB host/effective availability floor.
Clock sampling was read-only; EMC frequency access was denied, energy was not
process-attributed, and no clocks or services were changed. Raw commands,
stdout/stderr, supervisor samples and tegrastats are retained alongside each
result. See `SHA256SUMS.txt` for binary and workload identities.

The exact commands were:

```sh
build/integration/candidate/ple_parity --selftest \
  --pack /home/calvin/models/strata-orin-validation/q2-ple-pack \
  --gguf /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf

ctest --test-dir build/integration/candidate --output-on-failure -j1 \
  -R '^(shared_memory_budget_test|conversation_cache_test|conversation_memory_test|vmm_test|native_dense_ple_key_test|expert_cache_per_layer_test|expert_cache_segmented_test|ple_parity|expert_cache_memory_test|expert_cache_memory_refusal|platform_memory_test|session_loop_scratch_trace_test|ple_reader_selftest|conv_cache_test|coupled_draft_test)$'

python3 -m unittest discover -s tools/integration -p 'test_*.py'
```

This refresh confirms the selected contracts on the current candidate. It does
not expand Phase 3's Q2_0 scope, price private CUDA Graph backing, establish a
general capacity threshold, or qualify another model/backend.
