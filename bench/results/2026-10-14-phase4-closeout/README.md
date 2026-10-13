# Focused Phase 4 regression rerun — Orin — 2026-10-14

The current candidate build passed the focused ARM Q8_1 scalar contract,
opt-in NEON contract, and expert dispatch regressions (3/3). The exact tests
were `q8_1_scalar_contract_test`, `q8_1_neon_contract_test`, and
`expert_multi_test`; CTest reported 3.78 seconds total. The run used a 28-GiB
cgroup limit, read-only clock sampling and the normal six-GiB physical-memory
floor. Minimum host availability was 26,341,785,600 bytes; the observed OOM
and OOM-kill counters remained zero. EMC frequency was inaccessible and energy
was not measured.

The test command was:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase4-closeout/ctest/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  ctest --test-dir build/integration/candidate \
  -R 'q8_1_scalar_contract_test|q8_1_neon_contract_test|expert_multi_test' \
  --output-on-failure
```

Full stdout, stderr, supervisor JSON, memory samples and tegrastats are retained
in `ctest/supervisor/`. The tested binary and relevant source hashes are in
`SHA256SUMS.txt`. Existing operator screens, end-to-end paired campaigns and
HIP/SYCL build records are linked from the [Phase 4 closeout](../../../docs/integration/PHASE4_CLOSEOUT.md).
