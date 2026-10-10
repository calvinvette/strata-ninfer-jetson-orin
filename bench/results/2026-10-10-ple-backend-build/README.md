# PLE oracle backend compilation — 2026-10-10

The modified `CMakeLists.txt` and `src/kernels/ple_parity.cpp` were copied into
the isolated maestro1 validation snapshot. SHA256 values match the local files
in `source-sha256.txt`.

The refreshed one-job HIP build passed on maestro1, and the test target was then
explicitly enabled and built. `ple_parity` compiled and linked successfully
under HIP; its binary digest is recorded in `binary-sha256.txt`. The same
updated source snapshot also completed the existing full SYCL build (123/123
steps); SYCL uses its separate `sycl/` CMake project and does not compile this
CUDA/HIP-specific PLE test source. The refreshed main-project SYCL build and
HIP production build are compile evidence only. maestro1 has no relevant GPU
runtime qualification.

The targeted HIP target log is retained as `hip-ple-parity.txt`. The full
build logs and validation environment remain in the isolated remote tree at
`~/workspace/strata-integration-validation/logs/`.
