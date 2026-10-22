# Current-source Orin build and regression — 2026-10-22

The ARM64/CUDA 12.6 Release candidate under `build/integration/candidate` rebuilt successfully with two parallel jobs. Its `strata` SHA256 is `081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`; `native_expert_parity` is `bd7f8f01f91bdd367a70a375e837e919dacb5e1ec246c1f01c328556532ba660`. The base repository revision was `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`, with an active worktree diff; its tracked diff digest and status are retained here.

The focused Phase 5 CTest selection passed 29/29, covering accepted usage/windows, verifier and GDN parity, KV formats, graph trace/lifecycle, Q8_1 scalar/NEON contracts, and native-expert Q8_1 dot/window paths. Python integration discovery passed 163/163.

The initial full configured CTest run completed 132 tests: 128 passed, two optional IQ fixture tests skipped, and `expert_parity` plus `pool_test` could not open absent `pack/full/experts.bin`. The exact initial failure log is retained in `LastTest.log.gz` and `LastTestsFailed.log.gz`. The available Coder pack under `~/models/strata-orin-validation/pack/` is a native mixed-format IQ1_M artifact, not the full S2 blob expected by these tests; it was not substituted.

No product inference, end-to-end performance, HIP/SYCL runtime, or model-quality claim follows from this regression run. The two IQ fixture skips are separate from the missing `pack/full/experts.bin` failures. This is current-source regression evidence only; Phase 5 remains open because adaptive accepted-prefix state drift has no validated correction or bounded contract.

Reproduction commands:

```sh
cmake --build build/integration/candidate --parallel 2
python3 -m unittest discover -s tools/integration -p 'test_*.py'
STRATA_TEST_EXPERTS_BIN="$HOME/models/strata-orin-validation/generated-fixtures/q2_0-s2-layer0/experts.bin" \
  ctest --test-dir build/integration/candidate --output-on-failure
```

The two pack-backed CTests were first run against a temporary one-layer S2 fixture derived by `tools/pack_layer.py` from the first shard of the actual local Q2_0 model (`69820c02…` SHA256; full source and fixture hashes are in `fixture-source-sha256.txt`). One layer contains all 512 layer-0 expert blobs in the exact expected 1,382,400-byte S2 layout; both CTests access only layer 0 and adjacent experts. The generated 675-MiB arena remains under `~/models/strata-orin-validation/generated-fixtures/q2_0-s2-layer0/`. Their test-only default path now accepts `STRATA_TEST_EXPERTS_BIN`; when unset, the existing default remains unchanged, and CLI `--file` still overrides it.

The complete configured CTest suite was rerun with that variable set to the external fixture: 130 passed, two optional IQ-fixture tests skipped, and no failures. This includes passing `expert_parity` and `pool_test`. The full log is `full-ctest-with-external-s2-fixture.log.gz`; the 48-layer arena-load test remains unrun. Python integration discovery passed 163/163. `SHA256SUMS` covers the report artifacts. This is regression evidence only; Phase 5 accepted-state drift remains unresolved.
