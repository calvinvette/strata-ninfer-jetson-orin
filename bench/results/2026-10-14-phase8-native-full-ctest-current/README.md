# Current-source native CTest release regression — Orin — 2026-10-14

The CUDA/ARM64 candidate built from the current source tree was tested with
the complete 118-test CTest selection, then with only the two missing-fixture
tests excluded. Both sequential runs used a 28-GiB cgroup ceiling and the
six-GiB physical-host-availability floor. The source tree at test time was
commit `e2ff8659`; the `strata` executable SHA256 was
`abef7698554590b3e28036844da207c0c58c291167204bee9dff248d80304b32`.

| Run | Result | Minimum host / admission availability | Elapsed |
| --- | --- | ---: | ---: |
| Full 118 tests | 114 passed, 2 optional IQ skips, 2 failed | 19.875 GiB | 254.27 s |
| Excluding only `expert_parity` and `pool_test` | 116 passed, 2 optional IQ skips | 19.049 GiB | 263.85 s |

The two failures are `expert_parity` and `pool_test`; each requires
`pack/full/experts.bin`, which is absent from this checkout and the local model
inventory. The only available resident-expert files belong to differently
formatted model packs, so they were not substituted into the legacy fixture
path. No model or build product was copied into Git. Both runs stayed above the
six-GiB floor, below the cgroup ceiling, and sampled zero cgroup pressure,
limit or OOM events. CTest ran serially; the longer fused-IQ prefill parity test
passed in each selection.

The fixture-excluded result is the available native regression set for this
binary. The retained full run keeps the two failures visible rather than
counting them as skips or passes. These tests do not replace the Q2_0 service,
memory-admission or task-quality evidence in the Phase 5–7 reports. HIP/SYCL
compile/link evidence is separate and recorded in the [current-source
MoE/backend report](../2026-10-14-phase5-moe-activation-capture/README.md).

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output full-supervisor --timeout 2400 --interval 1 -- \
    ctest --test-dir build/integration/candidate --output-on-failure -j1

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output available-supervisor --timeout 2400 --interval 1 -- \
    ctest --test-dir build/integration/candidate --output-on-failure -j1 \
    -E '^(expert_parity|pool_test)$'
```
