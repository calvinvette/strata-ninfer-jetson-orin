# maestro1 backend compile record

The Q8_1 CPU quantizer change was checked in isolated Release builds on
maestro1. This x86 host provides compile and link evidence only; it does not
qualify Orin runtime behavior or performance.

The full HIP build passed for `gfx1100` with HIP enabled, CUDA disabled,
prefill MMQ enabled, conversation tests enabled and test targets otherwise
disabled. It completed 311 Ninja tasks with one worker. The full oneAPI SYCL
build also passed, completing 123 tasks with one worker. Both builds used the
pinned ggml checkout at `3cf03257f219afbe7334045ff7c6a06ac68c627d` and Release
configuration. They emitted existing compiler warnings but no errors.

After syncing the final source, both backends rebuilt the affected CPU
translation unit and linked the application target successfully. The HIP
incremental target rebuilt `expert.cpp`, `libstrata_kernels_cpu.a`, required
dependencies, and the HIP `strata` executable (18 tasks). The SYCL incremental
check rebuilt `expert.cpp`, `libstrata_kernels_cpu.a`, and linked the SYCL
`strata` executable. The SYCL final link required `TMPDIR` on the spacious
`/mnt/sda2` volume because maestro1's root filesystem had only 42 MiB free.
No unrelated files were removed. The isolated HIP build directory was removed
after its successful final link; logs remain on maestro1. The final SYCL binary
remains in the isolated build directory.

Final input identities:

| File | SHA256 |
| --- | --- |
| `src/kernels/cpu/expert.cpp` | `fb099ad96fbe60c4831e9edb7798f51c0fa84fccb2c6f2017f23b46b2aee33f9` |
| `CMakeLists.txt` | `da85e300675c2461f9cfec0e37c36ac79998bb261a9db8fe72bf1ac59de94c27` |
| `src/kernels/cpu/q8_1_contract_test.cpp` | `012107719774afb8801ca405dc29a6533ccae3905afe5d76f49f4f4c950159dc` |

The final SYCL executable SHA256 is
`072a8433d8a9b3dff28dd181d84a2c53dd75e993c864900738c0b3a63a8521fe`. The
HIP binary was not retained after its successful final link; its earlier full
build binary hash is not presented as the final artifact identity.

The build script, configuration logs, full build logs, final relink logs and
binary hashes are retained under
`~/workspace/strata-integration-validation/q8_1-neon/` on maestro1. The Q8_1
contract CTests are AArch64-only and were run on Orin; neither remote build
claims to compile the NEON instruction path.
