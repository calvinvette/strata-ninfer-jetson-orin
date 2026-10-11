# Focused Phase 3 memory and PLE tests — Orin — 2026-10-11

The current candidate's focused ten-test CTest set passed under the six-GiB
physical availability supervisor in 24.36 seconds. The set covers segmented
VMM, native dense PLE keys, expert-cache segmented/memory/refusal paths,
platform memory admission, pinned fallback/shared behavior, and the PLE oracle
and reader. Minimum sampled `MemAvailable` was 26,453,626,880 bytes (24.64 GiB).
All ten tests passed; the raw CTest output and supervisor telemetry are retained
in `supervisor/`.

Command:

```sh
ctest --test-dir build/integration/candidate --output-on-failure \
  -R '^(vmm_test|native_dense_ple_key_test|expert_cache_segmented_test|ple_parity|expert_cache_memory_test|expert_cache_memory_refusal|platform_memory_test|pinned_fallback_test|pinned_shared_test|ple_reader_selftest)$' -j1
```

This confirms selected unit and owner contracts. It does not establish complete
physical allocation attribution, graph executable/driver memory, or pressure
behavior beyond the separately recorded admission experiments.
