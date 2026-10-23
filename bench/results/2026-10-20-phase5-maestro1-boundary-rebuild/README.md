# maestro1 HIP and SYCL boundary rebuild — 2026-10-20

The current shared source was synchronized to maestro1 and rebuilt with the
existing toolchains using one job. HIP and SYCL both compiled and linked, and
each resulting `strata` binary completed `--help`. The result file records the
same scope. The SYCL build produced 37 compiler warnings; neither backend was
run on accelerator hardware, and this x86_64 node provides build evidence only.

The changed integration sources and shared GGML header listed in
`source-sha256.txt` match between this checkout and maestro1. Build logs,
binary hashes, CLI output and the build result are retained under `logs/`.
No binaries or build products are included.
