# VMM virtual-address reservation accounting — Orin — 2026-10-10

The opt-in owner trace now records successful CUDA VMM address-range reserves
and releases separately from physical allocation handles and range mappings.
The parser reports peak and live reserved virtual bytes per device in a
dedicated `virtual_address_ranges` section. These numbers are address-space
extent only: they do not imply physical backing and are never included in the
concurrent physical allocation-request totals. A reserve that is not followed
by a successful release remains visible at log end.

The Orin `vmm_test` passed with tracing enabled. It emitted two reserve and two
release events, with a 27,262,976-byte concurrent virtual-range peak and no
range left live. Its separate unique physical-handle request peak was
18,874,368 bytes. The `expert_cache_segmented_test` also passed and emitted two
reserve/release pairs across two cache lifetimes: 100,663,296 bytes peak
reserved address space, separately from a 100,663,296-byte requested physical
handle peak. Both tests ended with zero live bytes in both ledgers. This tests
trace lifecycle and separation, not device-wide memory pressure or full CUDA
driver ownership.

The candidate CUDA `strata` target and both test executables built locally with
one job. Targeted CTest ran `vmm_test` and `expert_cache_segmented_test`: 2/2
passed. The focused Python owner parser suite passed 20 tests. Source and
candidate binary hashes and the raw traced test logs are retained under
`orin/`. On maestro1, the changed `expert_cache.cpp` and `vmm.cpp` translation
units compiled and the HIP `strata` target linked; its binary passed `--help`.
Source hashes before/after match. A broad default build was stopped after
17/191 steps once it had compiled both changed files; its partial log is kept
separate from the passing target build. The SYCL build uses its separate source
copies of both files, which were not changed.
