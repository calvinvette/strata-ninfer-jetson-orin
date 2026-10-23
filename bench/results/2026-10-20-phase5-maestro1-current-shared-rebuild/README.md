# Current shared-source rebuild — maestro1 — 2026-10-20

All five modified top-level C++/header files were copied into the isolated
maestro1 validation source tree, and their hashes match this worktree in
[`source-sha256.txt`](logs/source-sha256.txt). The current HIP tree compiled
and linked the affected sources serially; its `strata --help` check passed.
The captured HIP log includes the final link.

SYCL uses a separate migrated source overlay. Its shared CPU
`src/kernels/cpu/native_expert.cpp` was rebuilt earlier in the same session at
the exact current hash (`b10b75bd…`), with `strata --help` passing; see the
[targeted HIP/SYCL rebuild](../2026-10-20-phase5-maestro1-native-expert-rebuild/README.md).
The follow-up SYCL invocation reported no work because the remaining changed
top-level files add CUDA verifier/trace diagnostics and are not resolved from
the SYCL overlay. This does not claim those opt-in CUDA diagnostics were
ported to SYCL.

The builds are x86_64 compile/link evidence only. No HIP or SYCL device,
model execution, or Orin performance was tested. The retained SYCL
`no-work` log and the earlier exact-source rebuild log make the scope
explicit.
