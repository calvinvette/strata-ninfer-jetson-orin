# Phase 3 Q2_0 regression on the Q8_1 candidate binary

This refresh reruns the Q2_0 PLE and memory/owner regression after adding the
opt-in Q8_1 NEON implementation. `STRATA_Q8_1_NEON` was unset, so the serving
and PLE tests exercised the unchanged scalar default. This is current-binary
regression evidence, not new memory-capacity or graph-backing evidence.

| Check | Result | Minimum `MemAvailable` |
| --- | ---: | ---: |
| Artifact-aware `ple_parity` plus 14 memory/owner/PLE CTests | 15/15 passed | 24.415 GiB |
| Integration Python discovery | 124/124 passed | 24.408 GiB |

Both commands ran under `tools/integration/run_control.py` with the standard
six-GiB availability floor. The CTest run took 16.63 seconds. Python discovery
took 3.14 seconds. No OOM event occurred. Frequencies were sampled without
clock controls; EMC sampling was denied. Energy was not measured.

The tested `build/integration/candidate/strata` SHA256 is
`66cf3491ee06a30f340d8210084626fad78c730ccc819d9f15f167f4c0291a62`.
Raw supervisor telemetry, CTest output and Python test output are retained in
`ctest/` and `python/`.

This reconfirms selected contracts for the existing Q2_0 route. It does not
extend the Phase 3 closeout to new cache/context combinations, private graph
backing, or a different model/backend.
