# Q2_0 PLE regression refresh — Orin — 2026-10-14

The current checkout passed the artifact-aware PLE oracle, the selected Phase 3
accounting/ownership/PLE CTests, and integration Python discovery. The Q2_0
weights and PLE pack were already in `/home/calvin/models/strata-orin-validation/`;
no model was downloaded or copied into Git.

| Check | Result | Minimum host availability |
| --- | --- | ---: |
| `ple_parity --selftest` | 7/7 numerical stages for three tokens; worst relative L1 `1.148e-7` | 28.06 GiB |
| Selected Phase 3 CTests | 15/15 passed serially | 27.86 GiB |
| Integration Python discovery | 134/134 passed | 28.02 GiB |

Each command ran under `tools/integration/run_control.py` with its six-GiB
host-availability floor and read-only tegrastats sampling. This refresh did not
have a per-command 28-GiB cgroup ceiling; observed cgroup counters and OOM
events are retained in each `memory.jsonl` and `result.json`. Minimum host
availability remained above 27.8 GiB. No clocks or services were changed.

Commands:

```sh
python3 tools/integration/run_control.py --output ple-run -- \
  build/integration/candidate/ple_parity --selftest \
  --pack /home/calvin/models/strata-orin-validation/q2-ple-pack \
  --gguf /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf

python3 tools/integration/run_control.py --output ctest-run -- \
  ctest --test-dir build/integration/candidate --output-on-failure -j1 \
  -R '^(shared_memory_budget_test|conversation_cache_test|conversation_memory_test|vmm_test|native_dense_ple_key_test|expert_cache_per_layer_test|expert_cache_segmented_test|ple_parity|expert_cache_memory_test|expert_cache_memory_refusal|platform_memory_test|session_loop_scratch_trace_test|ple_reader_selftest|conv_cache_test|coupled_draft_test)$'

python3 tools/integration/run_control.py --output python-run -- \
  python3 -m unittest discover -s tools/integration -p 'test_*.py'
```

This reconfirms the already closed Phase 3 Q2_0 scope. It does not add new
admission-pressure evidence, expand model/backend coverage, price private CUDA
Graph backing, establish a general capacity threshold, or resolve the
graph-disabled native-control exclusion. See the [Phase 3 closeout](../../../docs/integration/PHASE3_CLOSEOUT.md).
