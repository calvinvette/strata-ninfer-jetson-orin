# Current-source Orin regression — 2026-10-17

The current CUDA/ARM64 candidate passed a supervised incremental build, the
fixture-available CTest suite and the integration Python suite on Orin1. The
source checkout was `38adabaa`; no engine, backend, CMake or test-source files
changed between the candidate binary's source commit `53d7c7a4` and this
checkout. The candidate executable SHA256 remained
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`.

The 28-GiB build scope completed successfully in 7.4 seconds and the CMake
build output shows the selected targets completed. Under a separate 28-GiB
scope, CTest reported 100% pass for all 118 selected tests in 289.5 seconds:
116 passed and the two optional IQ fixture tests were skipped. `expert_parity`
and `pool_test` were excluded because this checkout lacks
`pack/full/experts.bin`; those tests are not counted as passes. The 161-test
integration Python discovery suite passed under its own 28-GiB scope in 4.2
seconds.

| Scope | Samples | Minimum host / admission availability | `low`, `high`, `max`, `oom`, `oom_kill` |
| --- | ---: | ---: | ---: |
| Build | 8 | 24.49 / 24.49 GiB | 0 |
| CTest | 275 | 18.66 / 18.66 GiB | 0 |
| Python | 5 | 24.50 / 24.50 GiB | 0 |

Clocks were observed without control: CPU frequency samples ranged from 729.6
to 2,201.6 MHz and GPU samples from 306 to 1,300 MHz during CTest. EMC
readback was denied. Energy was not measured or process-attributed; raw
tegrastats samples are retained. No model was loaded and these tests do not
measure serving quality or performance.

Reproduce from the repository root on Orin1:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-17-phase8-current-source-regression/build-supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  cmake --build build/integration/candidate --parallel 2

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-17-phase8-current-source-regression/ctest-supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  ctest --test-dir build/integration/candidate --output-on-failure \
  --exclude-regex '^(expert_parity|pool_test)$'

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-17-phase8-current-source-regression/python-supervisor \
  --timeout 900 --interval 1 --sample-clocks -- \
  python3 -m unittest discover -s tools/integration -p 'test_*.py' -v
```

Each supervisor directory retains raw stdout/stderr, JSON memory samples,
tegrastats and the run result. This is native regression evidence for the
listed tests only. It does not close the Phase 8 serving-profile, default-path
release or rollback gates; Phase 8 remains open.
