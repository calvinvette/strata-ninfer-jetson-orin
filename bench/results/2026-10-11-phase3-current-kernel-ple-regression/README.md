# Current-kernel Q2_0 PLE and Phase 3 regression — Orin — 2026-10-11

After adding the opt-in Q6_K CUDA dequant schedule, the current candidate
passed the artifact-aware Q2_0 PLE oracle and a serial 19-test ownership,
memory, transfer and graph CTest selection. The seven PLE stages passed for
three tokens; worst relative L1 error was `1.148e-7`, with no non-finite
values. CTest passed 19/19. Minimum host `MemAvailable` was 27.21 GiB during
PLE and 27.38 GiB during CTest, both above the six-GiB floor. The integration
Python suite passed 103/103.

The PLE test used the real Q2_0 dense pack and GGUF shard 2/table data, with
synthetic hidden state and convolution history. The CTest selection includes
shared-memory budget, conversation/cache accounting, VMM, PLE, allocation
refusal, platform-memory, captured-graph owner, transfer and convolution-cache
checks. This confirms those contracts on the binary containing the kernel
candidate; it is not whole-model quality or graph-pool pricing evidence.

The candidate route remains unchanged unless
`STRATA_Q6K_WARP_DEQUANT=1` is explicitly set. The PLE and CTest commands ran
without that variable. Models remain under `~/models/` and were not copied
into Git. Raw stdout, stderr, supervisor telemetry and artifact identities are
retained in this directory.

Reproduce:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/NEW/ple/supervisor --timeout 240 -- \
  build/integration/candidate/ple_parity --selftest \
  --pack /home/calvin/models/strata-orin-validation/pack \
  --gguf /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf

python3 tools/integration/run_control.py \
  --output bench/results/NEW/owner-graph/supervisor --timeout 240 -- \
  ctest --test-dir build/integration/candidate --output-on-failure -j1 \
  -R '^(shared_memory_budget_test|conversation_cache_test|conversation_memory_test|vmm_test|expert_cache_per_layer_test|expert_cache_segmented_test|native_dense_ple_key_test|expert_cache_memory_test|expert_cache_memory_refusal|ple_parity|ple_reader_test|conversation_transfer_test|conversation_split_failure_test|conversation_snapshot_test|conversation_validation_test|platform_memory_test|captured_graph_trace_test|conv_cache_test|conversation_file_test|expert_profile_save_test)$'

python3 -m unittest discover -s tools/integration -p 'test_*.py'
```
