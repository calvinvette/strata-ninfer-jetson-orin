# Q2_0 PLE attempt and Phase 3 checks — 2026-10-10

The pinned two-shard Q2_0 model was downloaded to
`~/models/strata-orin-validation/Q2_0/` from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`, revision
`ed59f92082b1e93c0e96d60a8b11aab089b52f09`. The Hub metadata records shard
identifiers `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720`
and `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
Model shards, Python environment and generated pack remain outside Git under
`~/models`.

`tools/iq_pack.py` generated a standalone pack at
`~/models/strata-orin-validation/q2-ple-pack` using NumPy 2.5.3 and the
repository's vendored `gguf-py`. The supervised build passed with a 6 GiB
physical-availability floor and 27.91 GiB minimum observed availability. The
generated pack records 1,079 tensors, of which 303 are served natively, and a
1.38 GiB arena.

The PLE block oracle was adapted from Strata upstream PR #568, commit
`dc22aa266c556c11bacf2b24c155e79d229cc0aa`, because the repository did not ship
the block captures its older test required. Its CUDA target builds locally.
Running `ple_parity` with the downloaded Q2_0 shard and generated pack fails
before numerical comparison: the oracle requires a 26,214,400-byte PLE value
span and expects custom separated PLE key codes/scales, but this Q2_0 pack has a
13,107,200-byte BF16 value tensor and serves its native Q2_0 PLE key directly
from the GGUF. This is a format incompatibility, not a numerical mismatch or a
pass. The standalone `ple_reader_selftest` does pass. A future PLE block test
needs to load/decode the Q2_0 key layout and accept the pack's BF16 value layout,
then validate its oracle against those exact source representations.

The supervised Phase 3 CTest selection passed all 10 tests:

```text
shared_memory_budget_test
published_prefix_test
vmm_test
expert_cache_segmented_test
pinned_fallback_test
pinned_shared_test
expert_cache_memory_test
expert_cache_memory_refusal
platform_memory_test
ple_reader_selftest
```

Minimum system availability was 29,992,017,920 bytes (27.94 GiB), above the
required 6 GiB floor. The PLE parity attempt is separately retained at
`ple-parity-retry/`; the successful Phase 3 test record is `phase3-ctest/`.
The pack-build attempts are also retained, including the first environment
failures and the successful run. None of these tests establishes a product
performance gain or a combined-runtime PLE result.

The updated PLE source and CMake registration also compile on maestro1 under
HIP; the main build passed under HIP and SYCL. See the [backend compile
record](../2026-10-10-ple-backend-build/README.md). maestro1 is compile-only
evidence and provides no Orin performance or runtime qualification.
