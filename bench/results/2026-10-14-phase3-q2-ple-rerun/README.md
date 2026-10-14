# Q2_0 PLE and Phase 3 regression refresh — Orin — 2026-10-14

The current candidate passed the artifact-aware Q2_0 PLE self-test, selected
Phase 3 accounting/ownership/PLE CTests, and integration Python discovery.
The Q2_0 model and PLE artifacts were already in
`/home/calvin/models/strata-orin-validation/`; nothing was downloaded or copied
into Git.

| Check | Result | Minimum host availability |
| --- | --- | ---: |
| `ple_parity --selftest` | 7/7 numerical stages, 3 tokens; worst relative L1 `1.148e-7` | 24.404 GiB |
| Selected Phase 3 CTests | 15/15 passed, serial | 24.504 GiB |
| Integration Python discovery | 134/134 passed | 24.492 GiB |

Each command ran in a separate `systemd-run --user --scope` with a 28-GiB
cgroup ceiling and the runner's six-GiB host/effective-availability floor.
Clock sampling was read-only; EMC frequency access was denied, energy was not
process-attributed, and no clocks or services were changed. Raw command output,
supervisor samples and tegrastats are retained next to each result. See
`SHA256SUMS.txt` for the tested binary and run artifact identities.

Commands:

```sh
build/integration/candidate/ple_parity --selftest \
  --pack /home/calvin/models/strata-orin-validation/q2-ple-pack \
  --gguf /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf

ctest --test-dir build/integration/candidate --output-on-failure -j1 \
  -R '^(shared_memory_budget_test|conversation_cache_test|conversation_memory_test|vmm_test|native_dense_ple_key_test|expert_cache_per_layer_test|expert_cache_segmented_test|ple_parity|expert_cache_memory_test|expert_cache_memory_refusal|platform_memory_test|session_loop_scratch_trace_test|ple_reader_selftest|conv_cache_test|coupled_draft_test)$'

python3 -m unittest discover -s tools/integration -p 'test_*.py'
```

This refresh reconfirms the already closed Phase 3 Q2_0 scope. It does not
expand model/backend coverage, price private CUDA Graph backing, establish a
general capacity threshold, or resolve the graph-disabled native-control
exclusion.
