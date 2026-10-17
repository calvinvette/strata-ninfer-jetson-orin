# maestro1 HIP build for service CPU-row capture

The current `src/core/expert_source.cpp` diagnostic capture compiled and linked
into the HIP `strata` target on maestro1. The baseline source snapshot was
`7dea072d300083bdcdff4cc4ed6d862746626d4e`; its `expert_source.cpp` bytes match
the parent integration tree. The build overlay used the worktree file with
SHA256 `b5d6ce040144278b978ebdd9c88d71dd045ea57e7b8fbdddcfac3826177a8395`.
Release mode, gfx1100, AMD clang 22.0.0git, and one build job were used. The
HIP target linked, and `strata --help` succeeded. The captured build log has
existing HIP compatibility warnings and no compile or link errors.

The focused final rebuild command was:

```sh
cmake --build ~/workspace/strata-validation/integration/current-e6a55b30-build-hip/build \
  --target strata --parallel 1
```

`strata-help.txt` and `build.txt` retain the output. The resulting binary hash
is `ccd6c7b9b6a33758a15bf039871399c5c5cdcf87b6b8587c64e487a8402e6c8a`.
The binary itself is not included. This is x86_64 compile/link and CLI evidence
only; maestro1 has no usable AMD runtime. SYCL resolves a separate migrated
`sycl/src/core/expert_source.cpp`, which this CUDA/HIP-only diagnostic change
does not modify. Its existing current-source build was checked and Ninja had
no work to do.
