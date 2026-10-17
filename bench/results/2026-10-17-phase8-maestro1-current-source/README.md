# Current-source HIP and SYCL build checks — maestro1 — 2026-10-17

The current integration source at commit `1b369ab4070059bb57a50934fac3860871469220`
was rebuilt on maestro1 for HIP and SYCL. The isolated snapshot contains the
tracked CMake, engine, backend, test, tool and data build inputs. Its 800-file
SHA256 manifest was checked on maestro1 before compilation. Documentation,
benchmark results and the immutable `reference/ninfer` snapshot were not copied.

| Backend | Configuration | Result | Binary SHA256 |
| --- | --- | --- | --- |
| HIP | Release, gfx1100, CUDA off, tests off, conversation tests on, optional prefill MMQ off | Build exited 0; log reached 185/186; a second build reported no work remaining | `6684d0db987b1ae2f059dc026294a175f5aa0434a82114b454efef4af8b5d74c` |
| SYCL | Release, oneAPI DPC++ 2026.1.1, parity option off | 123/123 build steps; pass | `ed2f8dbcdb507d3e0809c333e3bcd448ccbe3c5adc80589a687ba08615f048ed` |

Both executables' `--help` commands exited 0 with their toolchain library
environments loaded. The output is retained in `logs/hip-help.txt` and
`logs/sycl-help.txt`. The first help attempts without those environments exited
127 because the dynamic loader could not find the HIP and oneMKL libraries;
those were launcher-environment failures and were rerun successfully.

maestro1 is Ubuntu 22.04.5 on x86_64 with four CPU cores and 3.7 GiB RAM. The
build used two jobs. HIP used ROCm SDK `7.10.0a20251120` and AMD clang
`22.0.0git`, targeting `gfx1100`; SYCL used Intel oneAPI DPC++/C++
`2026.1.1.20260724`. CMake was 3.31.10, Ninja 1.13.2 and GCC 11.4.0. Both
configurations used the existing llama.cpp checkout at
`3cf03257f219afbe7334045ff7c6a06ac68c627d`. Full configure and build logs,
tool versions, CMake cache selections, source hashes, executable hashes and
the actual build wrapper are retained in `logs/`.

The checked-in build wrapper was adjusted for this run to use two jobs and to
leave optional HIP prefill MMQ disabled. That optional path was not changed by
the integration commits since the prior backend matrix. The HIP configuration
reported that pack-dependent expert-arena and IQ-parity tests could not be
registered because their local pack and Python fixtures were absent. Tests
were disabled in the CMake configuration, so no CTest pass is claimed here.
The HIP progress counter stopped at `185/186` despite a zero exit status; an
immediate audit build exited 0 with `ninja: no work to do`, confirming that no
build action remained. Its output is retained as `logs/hip-build-audit.txt`.
Compiler warnings were present, including HIP ignored-result warnings and
SYCL DPCT unused-function warnings; neither build had a configure, compile or
link error.

These are x86_64 compile/link and CLI-startup checks only. maestro1 has no
usable AMD GPU or SYCL platform, so these results do not qualify HIP/SYCL
accelerator execution, model behavior, or Orin performance. Native CUDA/ARM
runtime evidence remains in its separate Orin reports. Phase 8 remains open
for the selected serving-profile, default-path regression and rollback gates;
Phases 5–7 still have their documented open qualifications.

To reproduce with a fresh snapshot on maestro1, place the tracked build inputs
from this commit under the `source/` directory, provide the pinned llama.cpp
checkout and local toolchain paths recorded above, then run:

```sh
TRACE_ROOT=/path/to/phase8-run bash logs/run-build.sh
```

The wrapper writes configure/build logs and binary hashes under
`TRACE_ROOT/logs/`. Load the ROCm and oneAPI library environments shown in the
wrapper before invoking each executable's `--help` command.
