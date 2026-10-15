# Current-source Orin regression retest — 2026-10-15

This Phase 8 verification rebuilt the Orin CUDA/ARM64 tree with two jobs under
a 28-GiB cgroup limit, then reran the fixture-available CTest selection and the
integration Python suite under separate supervisors. The source tree's latest
source commit is `c55e84756e5497e1e1fd9805e815db5859dfa959` (route-capture
instrumentation); the Strata binary SHA-256 is
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`.

The memory-bounded build passed. CTest passed all 117 selected tests in 249.2
seconds. Two optional IQ fixture tests skipped because their fixtures are
absent; `expert_parity` and `pool_test` were explicitly excluded because
`pack/full/experts.bin` is not available. The verbose integration Python suite
passed 144/144 tests. Minimum host/admission availability was 24.47/24.47 GiB
for the build, 19.07/19.07 GiB for CTest and 24.49/24.49 GiB for Python tests.
All sampled cgroup `low`, `high`, `max`, `oom` and `oom_kill` counters were
zero. GPU clocks were observed without control; EMC readback was unavailable.

A preliminary CTest and Python invocation ran before the memory-bounded rebuild.
A subsequent build dry-run exposed pending targets, so those preliminary test
outputs are retained but excluded from the conclusion. The build was completed,
and the 117-test CTest selection plus verbose 144-test Python suite were rerun
afterward and passed.

The exclusions mean these results do not cover the two pack-dependent expert
and pool tests or the absent optional IQ fixtures. This is native Orin regression
evidence for the current checkout, separate from the retained maestro1 backend
compile/help checks and its lack of usable HIP/SYCL runtime platforms.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase8-current-source-retest/build-supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  cmake --build build/integration/candidate --parallel 2

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase8-current-source-retest/supervisor-verified \
  --timeout 1200 --interval 1 --sample-clocks -- \
  ctest --test-dir build/integration/candidate --output-on-failure \
  --exclude-regex '^(expert_parity|pool_test)$'

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase8-current-source-retest/python-supervisor-verified \
  --timeout 600 --interval 1 --sample-clocks -- \
  python3 -m unittest discover -s tools/integration -p 'test_*.py' -v
```

All supervisor JSONL memory samples are retained gzip-compressed. Raw stdout,
stderr and tegrastats are retained for the preliminary and verified runs.
`SHA256SUMS.txt` covers the saved evidence.
