# maestro1 backend builds

The isolated validation snapshot under `/home/calvin/workspace/strata-integration-validation/source`
received only the changed `src/program/generate.cpp` and
`include/strata/platform/integration_trace.hpp`. A one-job HIP build of `strata`
completed successfully with the maestro1 HIP 7.2.53210 / AMD clang 22 toolchain
and `gfx1100` compile target. The post-build hashes match this worktree's two
sources; the binary SHA-256 is recorded in `hip-hashes.txt`. `hip-cli-help.txt`
records a successful help-path exit after setting the toolchain library path.
Compiler compatibility warnings remain in the captured HIP log. maestro1 has no AMD
GPU runtime for this project, so this is compile/help evidence only.

The isolated SYCL snapshot also received the changed shared expert-cache header;
its migrated `sycl/src/core/expert_cache.cpp` source was unchanged. The one-job
SYCL 2026.1 build compiled all 12 steps, including `generate.cpp`. Its first link
attempt failed because `LIBRARY_PATH` omitted the pinned oneMKL directory. Retrying
with the pinned oneMKL library directory linked successfully. The source/header
and executable hashes are in `sycl-hashes.txt`. The captured first-link failure
and successful relink are retained separately. `strata --help` aborts because no
SYCL device is available on maestro1; this is recorded as unsupported CLI/runtime
evidence, not a source or GPU runtime qualification.

The expert-stage pinned/pageable owner trace was then built from the current
`src/core/expert_source.cpp` and shared trace header under HIP with one job. Their
post-build hashes match the Orin checkout; the updated HIP executable hash and
successful CLI help output are in `hip-stage-hashes.txt` and
`hip-stage-cli-help.txt`. This only checks x86 compilation and CLI startup; it
does not qualify AMD execution.
