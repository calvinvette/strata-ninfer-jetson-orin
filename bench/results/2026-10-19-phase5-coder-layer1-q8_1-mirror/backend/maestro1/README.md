# maestro1 HIP/SYCL rebuild — 2026-10-19

The maestro1 x86_64 build used the pinned Strata source at `c5f9f319` with the
four-file layer-scoped selector overlay identified by
`../../source-overlay.sha256` (SHA-256
`012acd4bc85f1ba4d822487b9bb18891100b993e3f4f895974a450d95e2fd1d7`). The
build script and complete configure, compile/link, CLI, binary-hash, source
manifest and cgroup records are retained here.

HIP targeted `gfx1100`; SYCL used oneAPI 2026.1. Both builds completed, and both
`strata --help` commands exited 0. The incremental SYCL build completed all 20
reported Ninja steps; HIP linked `strata` and `native_expert_parity`. Compiler
warnings were emitted, with no build failures. The final `memory.events` file
records zero `max`, OOM and kill events for this run. Both builds used two jobs
and a 1.5-GiB scope.

This is x86_64 compile/link and CLI evidence only. maestro1 did not execute the
HIP or SYCL accelerator paths, load a model, or provide Orin performance
evidence. The Orin CUDA build, selector contract test and service arms are
recorded separately in the parent report.

Verify retained log integrity with `sha256sum -c logs/SHA256SUMS`. The source
manifest records the copied source snapshot; the four changed implementation
files match the local overlay used for this build.
