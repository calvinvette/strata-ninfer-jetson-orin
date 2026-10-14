# Native full CTest release regression — Orin — 2026-10-14

The current CUDA/ARM64 candidate was tested with the complete 118-test CTest
selection in a 28-GiB `systemd-run` scope and the six-GiB availability floor.
The first complete run passed 114 tests, skipped two optional IQ fixture tests,
and failed `expert_parity` and `pool_test`. Both failures are solely due to the
missing `pack/full/experts.bin` test fixture. The checkout's CMake test
definitions mark this file as a required input for those tests; no matching
pack exists under `~/models/`. No model was copied, and no failure is counted
as a pass.

A follow-up excluded only those two fixture-dependent tests. All 116 remaining
tests passed; the same two IQ fixture tests skipped. Minimum host and admission
availability was 19.548 GiB, well above the six-GiB floor. The full run's
minimum was 18.611 GiB. Both runs remained under the 28-GiB cgroup ceiling,
and sampled pressure/OOM counters stayed zero. These checks cover the current
native test build; they do not replace service-level model, capacity, or
quality results.

Commands from the repository root:

```sh
ctest --test-dir build/integration/candidate --output-on-failure -j1
ctest --test-dir build/integration/candidate --output-on-failure -j1 \
  -E '^(expert_parity|pool_test)$'
```

The complete and fixture-excluded raw outputs, runner samples and tegrastats
are retained alongside this report. `SHA256SUMS.txt` records the native engine
and run evidence. The Phase 8 maestro1 report separately covers full HIP and
SYCL compile/link checks; those builds are not runtime evidence.
