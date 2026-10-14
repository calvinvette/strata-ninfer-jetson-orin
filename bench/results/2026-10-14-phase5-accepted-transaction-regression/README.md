# Accepted-prefix transaction regression — Orin — 2026-10-14

This focused hardware regression ran seven current-build tests on Orin under a
28-GiB systemd memory ceiling and the six-GiB host-availability floor. All
seven passed in 8.42 seconds. The supervisor measured minimum host and
admission availability of 24.406 GiB, with zero sampled cgroup high, max, OOM
or OOM-kill events. GPU frequency was sampled read-only; EMC access was denied
and no energy was attributed to this short correctness run.
The test source was commit `2b6dc076`; the checkout was at `b8638915` (the
backend evidence documentation commit). Test and service binary hashes are
retained in `binary-sha256.txt`.

The set covers published-output prefix clipping, accepted-use accounting,
adaptive-window boundaries, verifier parity, GDN commit parity, speculative
verification parity, and QSA state/index parity. In particular,
`gdn_parity --selftest` exercises bitwise convolution-history commits for every
`T=1..8` and `keep=0..T`, using an independent host prefix selector and checks
that the verifier input rows remain unchanged. `accepted_usage_test` checks
zero, one, intermediate and full commits, rejected-suffix isolation and
invalid staging. `verify_parity`, `spec_verify_parity` and `qsa_parity` cover
the corresponding GPU verification and persistent-state paths.

The zero-row case is defined for the convolution-history and accepted-usage
helpers; the `Verifier::commit` API itself accepts only `1..T`. This run does
not claim a zero-row full verifier transaction. It also does not replace the
long-chain accepted-prefix comparisons or cancellation/recovery state checks
recorded elsewhere, and makes no performance claim. Full CTest output,
supervisor telemetry and command metadata are retained in `ctest-run1/`.

Command:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-accepted-transaction-regression/ctest-run1 \
  --timeout 1800 --interval 1 --sample-clocks -- \
  ctest --test-dir build/integration/candidate --output-on-failure -j1 \
  -R '^(published_prefix_test|accepted_usage_test|accepted_window_test|verify_parity|gdn_parity|spec_verify_parity|qsa_parity)$'
```

Service binary SHA256: `e84dc9af72bd46ceb1f6fc1643aa5b97cd8c6fbf815b99b8163092806c84da9c`.
