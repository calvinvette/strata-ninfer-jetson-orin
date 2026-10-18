# Current-source Orin native regression — 2026-10-18

The current Orin ARM64/CUDA candidate passed an incremental build, the fixture-available native CTest suite and the integration Python suite. The build completed under `MemoryMax=28G` in 3.2 seconds with two build jobs. CTest ran 118 tests: all 116 runnable tests passed and the two optional IQ parity fixture tests were skipped. `expert_parity` and `pool_test` were excluded explicitly because this checkout has no `pack/full/experts.bin`; they are not counted as passes. The integration suite ran 161 tests and passed.

The tested service is `build/integration/candidate/strata`, SHA256 `dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`. It was built from the engine source at commit `c1eb609d73f6ef4a1f596a6d7984e8e9522208dd`; the current checkout is `72cc6cf5129ace8c4f771cc19d0018ec08449a05`. No engine, include, CMake, or test source changed after the candidate source commit. This is native regression evidence, not model-serving quality, HIP/SYCL, or performance evidence.

| Scope | Runtime | Minimum host / admission availability | Memory events |
| --- | ---: | ---: | --- |
| Incremental build | 3.2 s | 24.60 / 24.60 GiB | zero |
| CTest | 257.9 s | 19.73 / 19.73 GiB | zero |
| Integration Python | 7.5 s | 24.55 / 24.55 GiB | zero |

All three commands ran in separate `MemoryMax=28G` scopes with read-only clock sampling. GPU and CPU clocks remained dynamic; EMC readback was denied. Energy was not measured or attributed. Each supervisor directory retains stdout/stderr, JSON memory samples, tegrastats and the supervisor result. CTest's two optional fixture tests are marked skipped by CTest; the two excluded pack-dependent tests require the absent `pack/full/experts.bin`.

Reproduce from the repository root on Orin:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-18-phase8-current-source-regression/build-supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  cmake --build build/integration/candidate --parallel 2

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-18-phase8-current-source-regression/ctest-supervisor \
  --timeout 2400 --interval 1 --sample-clocks -- \
  ctest --test-dir build/integration/candidate --output-on-failure \
  --exclude-regex '^(expert_parity|pool_test)$'

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-18-phase8-current-source-regression/python-supervisor \
  --timeout 1200 --interval 1 --sample-clocks -- \
  python3 -m unittest discover -s tools/integration -p 'test_*.py' -v
```

This refreshes current native regression evidence. Phase 8 remains open for the supported-profile and rollback package and any cross-backend builds required by future shared-source changes; it does not close Phases 5 or 6.
