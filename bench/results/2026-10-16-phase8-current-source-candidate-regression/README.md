# Current-source fixture-available Orin regression — 2026-10-16

This reran the current CUDA/ARM64 CTest tree after the opt-in CPU Q8_1 route was
added at commit `0464d128`. The source and test binary hashes are recorded in
`results.json`; the existing Strata service binary hash is also recorded. The
focused `native_expert_parity_` set includes the new candidate test.

An unfiltered 120-test attempt passed 116 tests, skipped the two configured IQ
fixture tests, and failed `expert_parity` and `pool_test` because
`pack/full/experts.bin` is absent from this checkout. The fixture-available
rerun excluded only those two tests: 116 passed, the same two IQ fixture tests
were skipped, and none failed. Those missing-pack tests are unavailable cells,
not passes. The run does not include model-serving or quality qualification.

The selected suite ran under `run_control.py` inside a user systemd scope capped
at 28 GiB, with one-second host/admission, cgroup and clock sampling. Across 272
samples, minimum host/admission availability was 19.56 GiB, above the six-GiB
floor. All leaf-scope `low`, `high`, `max`, `oom` and `oom_kill` event maxima
were zero. CPU and GPU frequencies were observed dynamically; EMC readback was
denied, and request-attributed energy was not measured.

Reproduce on Orin1 from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-16-phase8-current-source-candidate-regression/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  ctest --test-dir build/integration/candidate --output-on-failure \
  -E '^(expert_parity|pool_test)$'
```

CTest output, supervisor result, compressed one-second memory samples and
tegrastats are retained here. The two pack-dependent tests should be rerun when
the matching fixture is available. Phase 8 remains open for broader backend
runtime, supported-profile and release/rollback evidence.
