# Current-source HIP and SYCL builds — maestro1 — 2026-10-18

The tracked build inputs from integration commit `0b28cd634fa3a7ba9da514df0200d96baea330e4`
were copied to an isolated snapshot on maestro1 and checked against the
801-file SHA256 manifest before building. The immutable NInfer reference,
models and local build products were not copied. The pinned llama.cpp checkout
at `3cf03257f219afbe7334045ff7c6a06ac68c627d` was used from maestro1's existing
validation workspace.

| Backend | Configuration | Result | Binary SHA256 |
| --- | --- | --- | --- |
| HIP | Release, gfx1100, CUDA off, tests off, conversation tests on, prefill MMQ on | Full build and `strata --help` passed | `b04e9a6c2cee0116ecdd82cee9404fa18c3b321c8aec2382be0bfd871958e3e5` |
| SYCL | Release, oneAPI DPC++ 2026.1.1, parity option off | Full 123-step build and `strata --help` passed | `783ce7dbe23f010593f9cd0cc5efeaef4537db7d75d61bc6e2cd33bdede42aea` |

The first HIP build stopped at step 76 because the initial source transfer
omitted Strata's tracked `third_party/ggml/ggml-common.h` include. The header
and its license/version sidecars were added, the 801-file manifest was checked
again, and the incremental HIP build completed successfully. No source code
change was made to address this snapshot assembly error.

Builds ran with one job on maestro1's x86_64 host (3.7 GiB RAM). Build outputs,
temporary files and logs were placed under `/mnt/sda2`, which had 89 GiB free;
the host root filesystem remained untouched. The toolchain versions, selected
CMake options, build wrapper, full logs, help output, binary hashes and source
manifest are retained here. CMake tests were disabled, so no test execution is
claimed. maestro1 has no usable AMD GPU or SYCL platform; these results prove
x86_64 compile/link and CLI startup only, not accelerator execution or Orin
performance.

The relevant source snapshot SHA256 values are in
[`source-sha256.txt`](source-sha256.txt); the exact path list is in
[`source-files.txt`](source-files.txt). Run `sha256sum -c source-sha256.txt`
from the repository root to verify the current tracked inputs. Build log
hashes are in [`logs/SHA256SUMS.txt`](logs/SHA256SUMS.txt).
