# maestro1 HIP/SYCL build follow-up

On 2026-10-22, the synced source manifest matched the worktree hashes for
`include/strata/core/verify.hpp`, `src/core/verify.cpp`, and
`src/program/generate.cpp`. The HIP build used `--parallel 1`, rebuilt the
changed verifier and generator, linked `strata` and the configured test/tools,
and completed its `strata --help` check. Existing HIP warnings about ignored
`hipError_t` results were non-fatal.

The SYCL build reported `ninja: no work to do`; the configured SYCL tree uses
its separate `source/sycl` verifier/generator overlay. The existing SYCL
binary's `--help` check passed in the script's oneAPI environment. This records
no new SYCL source compile for the changed CUDA/HIP path. Neither backend ran on
an accelerator at maestro1, so this is x86 build and CLI evidence only.

The build command is `sync_build_maestro1.sh`; it syncs the three source files
and runs `build_maestro1.sh`. The HIP and SYCL binary hashes and captured logs
are retained here. Source manifest:

```text
75595d43c82ad36764f275a945cc30a45d8b072929dd3937c0599dd1de7cf7c3  include/strata/core/verify.hpp
9d6a41162b930197045155d66da0cfdd80d8e10b796f2b8b8e879f45ffe44d5f  src/core/verify.cpp
de1258c0fc439883c424562b58201d8d486e34a9a8cefbaffa22ae12390d16ba  src/program/generate.cpp
```
