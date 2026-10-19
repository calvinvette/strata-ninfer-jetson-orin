# Current-source CUDA and CPU test suite — Orin — 2026-10-19

The current CUDA build at source commit recorded in `source-commit.txt` passed
the bounded rebuild of `strata`, the accepted-window and accepted-usage tests,
and the GPU verifier, GDN and batched-verifier parity tests. The complete
serial CTest suite then ran under the integration memory sampler with a six
GiB host-availability floor.

CTest reported 128 tests: 124 passed, two skipped and two failed. The skipped
`iq_parity_fixtures` and `iq_parity` cases require an IQ fixture absent from
this checkout. The legacy `expert_parity` and `pool_test` cases require
`pack/full/experts.bin`, which is absent. The available Coder pack is a
different format/layout and is not a valid substitute. `expert_parity` also
reported that this ARM host lacks the AVX-512 features required for its x86
VNNI path. These two failures are unsupported fixture/hardware cells; no
engine failure was observed in them. Their full output is retained in
`ctest-stdout.txt` and `ctest-stderr.txt`.

The focused tests passed: accepted-prefix window and usage, GDN recurrence,
speculative sampling, verifier batch parity, KV Q8/stream/hybrid/Q4 parity,
PLE parity and reader self-test, captured-graph lifecycle, CPU Q8_1 contract,
all registered native-expert format cases, and Q8_1 grouped-window checks for
IQ2_S/Q2_0, IQ2_S/IQ4_NL and IQ3_XXS/IQ4_NL. The fused IQ prefill test passed
in 89.50 seconds. These tests verify their listed contracts, not full model
quality or service performance.

The 287.7-second suite retained at least 20.70 GiB host/admission availability.
Observed cgroup `low`, `high`, `max`, `oom` and `oom_kill` counters remained
zero. CPU/GPU clocks were sampled without changing them; GPU observations were
dynamic, EMC readback was denied, and energy was not attributed. Raw memory,
tegrastats and supervisor records are included here. The binary hash is in
`strata-binary-sha256.txt`.

Reproduce from the repository root:

```sh
python3 tools/integration/run_control.py \
  --output build/integration/resume-phase5-ctest-20261019 \
  --timeout 3600 --interval 1 --sample-clocks -- \
  ctest --test-dir build/integration/candidate --output-on-failure --parallel 1
```

This broad current-source regression check does not close Phase 5: accepted
prefixes pass these unit/parity contracts, while the separate layer-2
CPU/GPU owner-placement state divergence remains unresolved. It also does not
close Phase 6 or qualify the Phase 8 release profile.
