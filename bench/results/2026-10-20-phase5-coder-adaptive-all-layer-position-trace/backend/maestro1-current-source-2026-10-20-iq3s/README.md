# Current-source HIP and SYCL build — maestro1 — 2026-10-20

The shared CPU Q8_1 expert mirror, parity selector/CTest, and current root
verifier sources were staged from the integration checkout. The SYCL build also
used the current `sycl/src/program/generate.cpp` overlay and its CMake project.
Input source hashes are recorded separately for HIP and SYCL; the SYCL binary
and overlay hashes are recorded in `sycl-binary-and-overlay-hashes.txt`.

| Backend | Build | `strata --help` | Binary SHA256 |
| --- | --- | --- | --- |
| HIP, gfx1100 | Pass | Exit 0 | `581af2cc63d880b0483caca14492fa7f92c9d63b3d12bb8fb01f92afa179ca7a` |
| SYCL | Pass, 123/123 steps | Exit 0 | `b915d4da04f582bc230e1373646f23509f738842722ff1e8de7d6ddaf8c37fb2` |

Both builds used two jobs. Build logs, CLI output and exact source hashes are
retained here. The SYCL link emitted unused-function warnings from the migrated
DPCT compatibility headers and a GCC install-dir preference warning; link and
CLI checks passed. These are x86_64 compile, link and CLI checks only. maestro1
provides no accelerator execution or Orin performance evidence.
