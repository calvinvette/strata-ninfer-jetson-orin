# Expanded HIP/SYCL build qualification — 2026-10-09

The verifier-only HIP and SYCL source snapshot both built successfully in the
isolated maestro1 tree. Afterward the expanded native/SYCL owner edits were
applied and mtime-advanced. Expanded HIP compiled successfully. Its GPU runtime
is not available on maestro1.

The first expanded SYCL CMake rerun failed while CMake re-detected compiler
paths and cleared compiler cache values. The next wrapper failed before CMake
because it enabled `nounset` while sourcing Intel variables. A third setup
reached CMake using system 3.22.1, below the required 3.24, because that wrapper
did not restore the build-tools PATH. These are recorded setup failures, not
source compilation failures. They remain visible in `logs-expanded`.

The fresh-root retry completed all 123 Ninja steps and linked the expanded
`strata` executable. The seven expanded source digests matched before
configuration and were rechecked after the build. The build used one compile job
and produced no compiler errors. The expanded executable digests are in
`expanded-binary-sha256.txt`; the seven input source digests are in
`expanded-source-sha256.txt`. The full clean-root compiler log is retained here
as `sycl-build-clean.txt`; the remote handle and prior setup attempts are in
`backend-build-handle.json`. C++/SYCL builds are compilation evidence only;
maestro1 cannot qualify Orin CUDA behavior or AMD/Intel GPU execution.
