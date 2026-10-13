# Source snapshot assembly retries

Two CMake configure attempts stopped before any backend compilation. The first
snapshot contained the engine sources but omitted `tests/hip`, so HIP CMake
reported empty `hip_*` test targets. The second added `tests/` but omitted
`tools/hip/tune_hipblaslt.cpp`, which CMake also requires for the configured
full HIP build. The final source snapshot added the tracked `tools/` directory;
its 782-file checksum manifest passed on maestro1, after which the full HIP and
SYCL builds completed. No source or build-tree files in the existing remote
validation checkout were changed.
