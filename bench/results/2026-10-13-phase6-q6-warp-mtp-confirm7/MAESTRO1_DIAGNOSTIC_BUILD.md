# maestro1 verifier diagnostic build check

This is compile portability evidence for the opt-in CUDA verifier diagnostic
added at repository commit `44336b34`. `maestro1` is x86_64; no HIP or SYCL GPU
runtime behavior is claimed.

The isolated `q8_1-neon` source tree received these exact files:

| File | SHA256 |
| --- | --- |
| `src/core/verify.cpp` | `af3de88b37b98773211289598e761b8c5838106120dc075908f15d935c001424` |
| `include/strata/core/verify.hpp` | `9d8b8d94052af64194ccb1916f2f6299c9dd643cfba9e43cb49bc46ef23a1abe` |

The Release HIP configuration used `gfx1100`, HIP enabled, CUDA disabled,
prefill MMQ enabled, and the pinned ggml revision
`3cf03257f219afbe7334045ff7c6a06ac68c627d`. The updated
`CMakeFiles/strata_engine.dir/src/core/verify.cpp.o` compiled successfully at
331,392 bytes. A subsequent single-target Ninja check reported no work, which
confirmed that the object was current for the copied source. The remote build
log is `~/workspace/strata-integration-validation/q8_1-neon/logs/hip-build.txt`.

The full HIP application build was stopped at task 114/311 while compiling an
unrelated llama.cpp MMQ quantization instance. It had not produced the
`strata_engine` archive or final application link. This is translation-unit
compile evidence only, not a full HIP engine build.

The isolated SYCL `strata` target reported no work. The SYCL verifier uses the
separate files `sycl/src/core/verify.cpp` and
`sycl/include/strata/core/verify.hpp`; neither was changed by this diagnostic.
No SYCL rebuild or runtime result is claimed.
