# Phase 2 backend rebuilds — 2026-10-09

The current integration sources were overlaid into maestro1's isolated
`strata-integration-validation/source` snapshot. The overlay contained only
`CMakeLists.txt`, `src/program/generate.cpp`,
`include/strata/core/published_prefix.hpp`, and
`src/core/published_prefix_test.cpp`; `src/kernels/gdn_parity.cpp` already had
the exact current SHA-256 in that snapshot. No model, reference checkout,
credential or executable was copied into this report.

## HIP

The gfx1100 HIP configuration rebuilt `strata` and `published_prefix_test` with
one compile job. The current `gdn_parity.cpp` source was then explicitly
recompiled and linked as a separate one-job target. Source hashes were checked
after the builds. The host-only `published_prefix_test` reports 11 checks and
zero failures; the HIP `strata --help` exits 0. Logs, source digests, and binary
digests are under [`maestro1/`](maestro1/).

The build emits existing HIP compatibility warnings, including ignored
`hipError_t` results. The compiler exits successfully. maestro1 has no AMD GPU
runtime for this project; no HIP GPU test or model run is claimed.

## SYCL

A fresh SYCL build directory configured with `STRATA_SYCL_PARITY=OFF` and
compiled `strata` in 123/123 Ninja steps with one job. Its CLI help exits 0.
The SYCL project resolves its own `sycl/src/program/generate.cpp`; it does not
compile the changed `src/program/generate.cpp` used by the HIP/native engine.
Source hashes for the SYCL CMake file and generation source matched before and
after. Build logs and binary/source digests are retained under
[`maestro1/`](maestro1/).

This is compile and CLI-help evidence only. SYCL parity targets were disabled,
and no Intel GPU runtime, Orin CUDA runtime or model state parity is established
by this report.
