# Q2_0 cancellation and layer-dump owner follow-up — 2026-10-11

The main [22 GiB cgroup cancellation run](README.md) passed: disconnect stopped
the 2,048-token prompt after 512 tokens, all 302 traced allocation/free pairs
balanced, and the same service returned `Hello Orin!`. The 18 GiB attempt is a
separate pressure-aborted cell retained under the sibling `18G-rerun` result.

The focused `--dump-layers` check exposed and then verified an early-return
cleanup fix in `src/program/generate.cpp`. On the Q2_0 native `--spec 2` route,
the option allocates 2,007,040 bytes of pinned host staging. The request then
fails with `--spec needs the device residency table (--expert-profile,
--expert-cache and the token graph)`: dumping disables the token graph that
this verifier path requires. Before the fix, this return had an allocation
event and no matching free event. After the fix, the same run emits both the
allocation and free for the same owner, instance and pointer. It is a cleanup
test on a rejected configuration, not a successful layer-dump run or a serving
path recommendation.

The post-fix run returned code 2 for that expected unsupported combination,
with 23,360,598,016 bytes minimum host availability (21.76 GiB). The staged
dump output is empty because verification rejected the path before the first
layer record was written. Its raw stderr and supervisor data are in
`../2026-10-11-phase3-layer-dump-owner/fixed/supervisor/`.

The native CUDA `strata` target rebuilt successfully with one compile job. The
compiler emitted the existing unused-variable warning at
`src/program/generate.cpp:8798`; no new warning was reported for the guard. The
rebuilt binary SHA256 is
`3306495d333c87cbf72e0f628b0ce94552e0492cf428b08d2d2fa96c370dcce3`.
maestro1 is reachable, but this checkout could not find `hipcc`, `icpx`, or
`dpcpp` on the host or in its installed tool paths, so no fresh HIP/SYCL build
is claimed here. The SYCL backend uses its separate generator source. Earlier
backend build evidence remains in the integration status; a fresh HIP build is
still needed before Phase 8 review.
