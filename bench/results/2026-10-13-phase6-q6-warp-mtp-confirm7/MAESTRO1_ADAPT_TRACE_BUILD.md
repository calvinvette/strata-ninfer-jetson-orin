# maestro1 adaptive trace build check

The server-loop adaptive-swap trace at commit preparation was compiled in the
isolated HIP validation tree at
`~/workspace/strata-integration-validation/q8_1-neon`. The exact current
`src/program/generate.cpp` was copied there, along with the current
`include/strata/core/session.hpp` needed by that source revision.

| File or artifact | SHA256 |
| --- | --- |
| `src/program/generate.cpp` | `958619930f743a04284af2a81efeac12b7e5a0e5738273baff3ea9a01d8bc9fc` |
| `include/strata/core/session.hpp` | `23969276005a59c27a3b6675e82f3dc6c1229322fa13c4a8923ebd0237f1ebf9` |
| HIP-configured `CMakeFiles/strata.dir/src/program/generate.cpp.o` | `dbed7fd9d109d892cb495b341344d49f0372ae47fc88c81ddee223f84f07b67f` |

The object is 1,382,928 bytes. The HIP configuration targets `gfx1100`, uses
`/usr/bin/c++` for this C++ translation unit, and compiles it with
`STRATA_USE_HIP=1` plus the HIP CUDA-compatibility header. A prior whole-target
attempt began unrelated llama.cpp MMQ rebuilds and was stopped; the focused
Ninja object target then compiled the changed translation unit successfully.
This is object-level compile evidence only: no HIP executable link or runtime
is claimed. The captured compiler output is in
`backend-builds/hip-generate-object-build.log` (SHA256
`1d12dce20c33cd117bb17dcf441fb5227238a5a5987e00aebfa37454c9c6f67f`).

The SYCL entry point is maintained separately in `sycl/src/program/generate.cpp`
and was unchanged; it does not use the modified translation unit. No SYCL
runtime result is claimed.
