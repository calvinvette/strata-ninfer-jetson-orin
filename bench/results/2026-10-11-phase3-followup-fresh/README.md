# Fresh Q2_0 PLE and Phase 3 owner/graph regression — Orin — 2026-10-11

The current `build/integration/candidate/ple_parity` binary passed the
artifact-aware Q2_0 `--selftest` under `tools/integration/run_control.py` with
the normal six-GiB physical-availability floor. All seven PLE stages passed
for three tokens; Q2_0 key blocks reassembled byte-identically, and the native
projection matched the independent decoded path. Worst relative L1 error was
`1.148e-7`, with no non-finite values. The real PLE table and layer-1 weights
come from the Q2_0 shard; hidden state and convolution history are synthetic.
This is an operator contract check, not a whole-model quality or performance
result. The exact model and pack paths are under `~/models/` and no model files
were copied into the repository.

The current candidate then passed the serial 19-test owner/graph regression:
shared memory budgets, conversation and cache accounting, VMM, native PLE,
artifact-aware PLE, cache refusal, platform memory, captured-graph ownership,
and conversation/conv-cache contracts. CTest reported 19/19 passed in 5.06 s.
Minimum host `MemAvailable` was 26,326,528,000 bytes (24.52 GiB), above the
required six-GiB floor. This is software-contract evidence; it does not price
model graph-pool bytes or establish broad active-pressure behavior.

The first PLE attempt passed the Q2_0 shard 1 to `--gguf`, which requires shard
2 containing `per_layer_token_embd.weight`; it exited 2 at preflight with
24.64 GiB available. That failed invocation is retained in `ple/supervisor/`.
The corrected shard-2 run passed and is retained in
`ple/supervisor-corrected/`. Regression CTest output and supervisor telemetry
are in `owner-graph/supervisor/`.

The integration Python unit suite also passed all 103 tests (`python3 -m
unittest discover -s tools/integration -p 'test_*.py'`, 5.64 s).

Commands:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/NEW/ple/supervisor-corrected --timeout 240 -- \
  build/integration/candidate/ple_parity --selftest \
  --pack /home/calvin/models/strata-orin-validation/pack \
  --gguf /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf

python3 tools/integration/run_control.py \
  --output bench/results/NEW/owner-graph/supervisor --timeout 240 -- \
  ctest --test-dir build/integration/candidate --output-on-failure -j1 \
  -R '^(shared_memory_budget_test|conversation_cache_test|conversation_memory_test|vmm_test|expert_cache_per_layer_test|expert_cache_segmented_test|native_dense_ple_key_test|expert_cache_memory_test|expert_cache_memory_refusal|ple_parity|ple_reader_test|conversation_transfer_test|conversation_split_failure_test|conversation_snapshot_test|conversation_validation_test|platform_memory_test|captured_graph_trace_test|conv_cache_test|conversation_file_test|expert_profile_save_test)$'
```

No runtime defaults or backend source files changed.
