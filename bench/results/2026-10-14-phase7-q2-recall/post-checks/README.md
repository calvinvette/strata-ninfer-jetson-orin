# Post-ladder regression checks — Orin — 2026-10-14

After the Q2_0 8K/16K/32K retrieval runs, the current CUDA candidate passed a
fresh artifact-aware PLE self-check, the selected Phase 3 CTests, and all
integration Python tests. The model shards and Q2_0 PLE pack remained under
`~/models/strata-orin-validation/`; no model was copied into the repository.

| Check | Result | Minimum host availability |
| --- | --- | ---: |
| Artifact-aware Q2_0 `ple_parity --selftest` | 7 numerical stages passed for 3 tokens; worst relative L1 `1.148e-7` | 24.388 GiB |
| Selected accounting/ownership/PLE CTests | 15/15 passed serially | 24.509 GiB |
| Integration Python discovery | 132/132 passed | Not systemd-supervised; no model or GPU workload |

PLE and CTest each ran in a separate 28-GiB systemd scope with the six-GiB
host/effective availability floor. Sampled cgroup OOM-kill counters were zero.
Clock sampling was read-only; EMC frequency access was denied and energy was
not process-attributed. The binary identity is in the parent
[`SHA256SUMS.txt`](../SHA256SUMS.txt).

The exact commands were:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase7-q2-recall/post-checks/ple-supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  build/integration/candidate/ple_parity --selftest \
  --pack /home/calvin/models/strata-orin-validation/q2-ple-pack \
  --gguf /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase7-q2-recall/post-checks/ctest-supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  ctest --test-dir build/integration/candidate --output-on-failure -j1 \
  -R '^(shared_memory_budget_test|conversation_cache_test|conversation_memory_test|vmm_test|native_dense_ple_key_test|expert_cache_per_layer_test|expert_cache_segmented_test|ple_parity|expert_cache_memory_test|expert_cache_memory_refusal|platform_memory_test|session_loop_scratch_trace_test|ple_reader_selftest|conv_cache_test|coupled_draft_test)$'

python3 -m unittest discover -s tools/integration -p 'test_*.py'
```

Raw command output and supervisor records are retained in the two result
subdirectories.
