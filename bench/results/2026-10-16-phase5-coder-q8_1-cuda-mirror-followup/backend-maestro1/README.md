# maestro1 backend compile record

The targeted HIP and SYCL builds used maestro1's isolated Phase 8 build trees
and one job. Their source snapshot began at `4b72a72b`; all nine CMake, include
and `src/` paths changed through `c62f3c90` were overlaid, including the two
current experimental expert files. The exact overlay hashes are in
`current-source-sha256.txt`. The original Phase 8 source files were restored
after building; the two restored native-expert hashes matched the pre-build
snapshot.

HIP built `strata` and `native_expert_parity`; SYCL built `strata`. Both
`--help` checks passed. Builds used ROCm SDK `7.10.0a20251120` / AMD Clang
`22.0.0git` for gfx1100, and Intel oneAPI DPC++ `2026.1.1.20260724`. Logs and
binary SHA256 values are retained beside this file. Compilation and CLI startup
are the only evidence here: maestro1 has no qualified AMD or Intel runtime
device, and no model was loaded.

The final HIP build and SYCL link used `/mnt/sda2` for scratch space where
needed. The logs preserve compiler warnings. The target commands and oneAPI
environment setup are listed in `commands.txt`. Earlier wrapper attempts that
omitted oneAPI setup or scratch-space configuration were corrected; the final
build logs end successfully.
