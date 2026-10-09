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

The current serial retry uses a new build root to preserve the verifier-only
binary, loads the pinned existing oneAPI/ggml toolchains with the original
bounded single-job setting and explicit compiler paths, and verifies the exact
expanded source digests before configure. Its remote handle is in
`backend-build-handle.json`. Verify the live process or terminal result and
`sycl-build-clean.txt` before claiming an expanded SYCL pass. C++/SYCL builds
are compilation evidence only; maestro1 cannot qualify Orin CUDA behavior or
AMD/Intel GPU execution.
