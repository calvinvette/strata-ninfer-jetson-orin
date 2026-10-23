# maestro1 HIP/SYCL rebuild for current Phase 5 source — 2026-10-20

This report records x86_64 compile/link and CLI-help checks on `maestro1`. It is
build evidence only: no HIP/SYCL GPU execution, Orin runtime qualification,
model inference or performance measurement was performed.

The source snapshot is based on repository commit `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`
with the current worktree copies of `src/kernels/cpu/native_expert.cpp` and
`src/kernels/native_expert_parity.cpp` overlaid. The full per-file source
manifest is `source-sha256.txt`; the refreshed remote snapshot passed
`sha256sum -c` before the final build. No model files were copied to maestro1.

The first isolated build completed both backend compile/link passes before the
source overlay was refreshed. The subsequent incremental build compiled the
refreshed CPU expert source for HIP and SYCL; HIP also compiled and linked
`native_expert_parity`. The SYCL configuration has `STRATA_SYCL_PARITY=OFF`,
so that parity executable is outside its build scope. The exact build and
configure logs, binary hashes, source verification, and help output are
retained under `logs/`.

Both rebuilt `strata --help` checks exited successfully after loading the
corresponding ROCm and oneAPI runtime environments. Calling the SYCL binary
without its oneAPI environment first failed to locate `libmkl_sycl_blas.so.6`;
the recorded check uses the required environment. The oneAPI setup emitted
warnings about unavailable hwloc and direct UMF setup, but the help command
completed with exit status 0.

Reproduce from the validation checkout on maestro1 with the recorded
`build/integration/build-phase8-maestro1.sh`, `TRACE_ROOT`, and
`TRACE_TMPDIR` values in `logs/run-build.sh`. Build logs identify the HIP
`gfx1100` and Intel oneAPI SYCL toolchains. Runtime support remains
unqualified; maestro1 supplies no Orin performance evidence.
