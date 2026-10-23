# Current worktree HIP/SYCL rebuild — maestro1 — 2026-10-20

The current Phase 5 diagnostic source set rebuilt and linked on maestro1 for
HIP and SYCL with one build job. Both rebuilt binaries exited successfully
with `--help`. Source file hashes are retained in `source-sha256.txt`, and
build logs, help output, and binary hashes are under `logs/`.

The first HIP attempt exposed an incomplete validation snapshot: its
`include/strata/kernels/cpu/native_expert.hpp` lacked the already-committed
layer-aware `native_fmt` declaration used by the current parity harness. The
compiler reported four “too many arguments” errors in
`src/kernels/native_expert_parity.cpp`. After copying the exact header from
this worktree and verifying its SHA256, the HIP build completed. The original
failure and successful retry are both retained. The full refresh script then
rebuilt HIP and SYCL from the synchronized source tree.

The Orin CUDA build of `strata` and `native_expert_parity` also completed, and
the focused current-binary CTests passed 5/5 (`accepted_usage_test`,
`accepted_window_test`, `verify_parity`, the IQ3_XXS/IQ4_NL CPU Q8_1 expert
test, and the Q8_1 selector contract). The integration Python suite passed
163/163. `git diff --check` passed.

This is compile/link and CLI-startup evidence on x86_64 for HIP/SYCL, not
accelerator runtime or Orin performance evidence. The opt-in diagnostic and
owner arithmetic remain unqualified as a state-migration correction; Phase 5
and Phase 8 remain open.
