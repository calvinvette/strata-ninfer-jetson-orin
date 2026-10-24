# Orin CUDA functional test suite — 2026-10-24

## Result

The candidate CMake tree registered 135 tests and was run serially on Orin
under `tools/integration/run_control.py`, preserving the six-GiB availability
floor. The run took 316.33 seconds. CTest reported 132 passes, two skips and
one failure. Both skips (`iq_parity_fixtures`, `iq_parity`) require external IQ
fixtures. `pool_test` failed before its assertions because its default
`pack/full/experts.bin` path is absent from this checkout. The supervisor
recorded 20.60 GB minimum physical/admission availability and no cgroup OOM
events.

The failing pool test was rerun against the existing one-layer Q2_0 fixture at
`~/models/strata-orin-validation/generated-fixtures/q2_0-s2-layer0/experts.bin`
via `STRATA_TEST_EXPERTS_BIN`. It passed all completion, serial parity, 200
repeated-batch and batch-size checks. No model data was copied into the repo.
This resolves the test's input-path prerequisite for this rerun; the registered
default-path CTest cell still needs its fixture configured to make a clean full
suite run.

The full suite included the newly extended `gdn_parity` (pass) and
`verify_batch_parity` (pass). `gdn_parity` separately passed after its focused
addition of model-width convolution+L2 parity for windows T=1..8 and all split
`t_begin` positions. The run reports functional coverage only; this is not a
performance campaign. Full logs and supervisor telemetry are in the ignored
local `build/integration/ctest-full-20261024/` directory; the fixture rerun is
in `build/integration/pool-test-fixture-20261024/`.

## Reproduction

```sh
python tools/integration/run_control.py \
  --output build/integration/ctest-full-20261024/supervisor \
  --timeout 5400 --interval 1 -- \
  ctest --test-dir build/integration/candidate --output-on-failure -j1

STRATA_TEST_EXPERTS_BIN="$HOME/models/strata-orin-validation/generated-fixtures/q2_0-s2-layer0/experts.bin" \
  python tools/integration/run_control.py \
    --output build/integration/pool-test-fixture-20261024/supervisor -- \
    build/integration/candidate/pool_test --selftest
```

Build identity for the added parity test: SHA256
`83e2bcc512f5290aab703acbb0c644f68b670cc96b91e9dd1d4b84a4702b7c10`.
The report is tied to repository commit `23ffffb30dcc063a8281e0cec3b5a802eda470fc`.
