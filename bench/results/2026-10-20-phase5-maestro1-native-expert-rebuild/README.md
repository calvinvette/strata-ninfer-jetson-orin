# Current native expert CPU source backend builds — maestro1 — 2026-10-20

The uncommitted `src/kernels/cpu/native_expert.cpp` hash
`b10b75bdd6d444474b1a41cd36378fe3fe05399e8d5cdd396bd644fd42213a50` was
copied into the isolated maestro1 Strata validation checkout and built with
the existing HIP and SYCL toolchains. Both builds compiled and linked with one
job; both resulting `strata --help` checks passed. The HIP build rebuilt 22
targets, including `native_expert_parity`; the SYCL build rebuilt the shared
CPU library and `strata` in three steps. SYCL emitted one Clang
`-Wgcc-install-dir-libstdcxx` warning. The logs and resulting binary hashes
are retained under [`logs/`](logs/).

This verifies compilation and CLI startup only. maestro1 is x86_64 and no HIP
or SYCL device runtime or model execution was tested. It provides no Orin
performance evidence.
