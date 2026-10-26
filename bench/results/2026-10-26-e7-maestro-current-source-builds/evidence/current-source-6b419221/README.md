# Current-source HIP/SYCL build: expert-ID Q8_1 filter

Date: 2026-10-26. Exact source commit: `6b419221a0d712d18685b19df27e059fc455841f`.
The build checkout is `/mnt/sda2/tmp/calvin/strata-ninfer-build-e0-1f9f116b/src`;
maestro1 is x86_64 and contributes compile/link evidence only. The build
dependency is the pinned ggml checkout `llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d`.

Both configured `strata` and `native_expert_parity` targets built with
parallelism 1. HIP linked successfully on the initial build. SYCL compiled the
changed targets but its first final link lacked oneMKL library paths; sourcing
both the oneAPI compiler and `mkl/2026.1/env/vars.sh`, then rebuilding the two
remaining links, succeeded. Full compressed logs are adjacent.

| Backend | Build | Additional check | Binary SHA256 |
| --- | --- | --- | --- |
| HIP / ROCm 7.2.53210 | `strata`, `native_expert_parity` passed | `strata --help` passed; `native_expert_parity --q8_1-selector-contract` passed (0 failures) | `f41e8ac72084a32ce6e84851f64be6b164a46565f5e6ddc4521b3e00a333c2a0` (`strata`) |
| SYCL / oneAPI 2026.1 | `strata`, `native_expert_parity` passed after the oneMKL link-path fix | `strata --help` aborts because maestro1 has no SYCL device/platform. The separate SYCL parity program does not implement `--q8_1-selector-contract`; it interprets the option as a GGUF filename, so that contract is unsupported on this target. | `3cddbe84f5e026d3d2f1a4f3a549016a50b876db8ef25ef359ba7507e5286934` (`strata`) |

The HIP parity binary hash is `d4bc6586513ec2cb7ba49f3258719e1b40949f0f6c49504cc83884ee2607ccd5`; the SYCL parity binary hash is `dfae2ab4d211705f270ef0a33033079793b32e8bf477ed9e13f9c0fd7b4d9354`. No GPU runtime or Orin performance qualification was performed. HIP/SYCL binaries and toolchains remain on maestro1.
