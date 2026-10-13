# maestro1 accepted-row adaptive build check

The opt-in accepted-row usage path compiled and linked as a HIP-configured
`strata` executable on maestro1. No HIP runtime is claimed.

| File or artifact | SHA256 |
| --- | --- |
| `src/program/generate.cpp` | `a1a391a18030d4f3a8f5e724558452d43c351a0a36ab0f424bc161642546dc71` |
| `src/core/expert_source.cpp` | `06eee3a04bb8c7ffdff58a29d596e6c73389e6b94e0603fa4341d215bdcffb34` |
| `include/strata/core/expert_source.hpp` | `c24d56ab26d07702d995d656648285ecffed2ef7186f014e0669dde6e2591882` |
| `src/core/session.cpp` synced for the full link | `ed42765bcccead8be20584c3ddcb42c7add1016b8566a7e0a66fa9775e80a344` |
| HIP-configured `generate.cpp.o` | `c0b840e3ce8ebf40f8a16441d7067cdae187a0d1f8d4a03fff7f329981f490e9` |
| HIP-configured `expert_source.cpp.o` | `9babe1d5b03c696bbd8d4a357a3db3e1bd49da6f61482e51b1863ea830e5067f` |
| HIP `strata` executable | `d6aa3ce058a0f52c9046ab6144dc27da09df71ec8548db738cdaa4d7824aebb7` |
| Full build log | `77fc291c2ee60d3c6a949db622da40f26e7061b23ede4374f6058f8e9b00a6dc` |
| Changed-object log | `73d32429d2c40330e0226fb6371fcfb9507efc8b4612675f1da66f01ab2f843c` |
| Initial stale-snapshot link failure log | `841373ec0f975e3dc116892276feb4c9d185ef314e45ff62ea9e52523d239990` |

The command used maestro1's `q8_1-neon/build-hip` tree and its configured
`gfx1100` HIP toolchain. The object check used `ninja -j2`; the full target then
rebuilt the validation tree and linked `strata`. The initial link failed because
that snapshot had the current `session.hpp` declaration but a stale `session.cpp`
without `session_eager`. After syncing the matching current source, the full
target linked and a repeat build reported no work. The successful build emitted
ignored-HIP-return-value warnings but no errors. SYCL's program and expert-source
files live under a separate `sycl/` source tree; that tree was not changed by this
candidate. No SYCL runtime or build claim is made.
