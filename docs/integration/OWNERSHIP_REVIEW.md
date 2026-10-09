# Runtime ownership review

Reviewed against the active Strata source after the clipped-publication fix.
This records which existing component owns each kind of mutable state; it does
not claim that every allocation is in one measured ledger or that every
transaction path has passed runtime parity.

| Concern | Current owner | Boundary and evidence | Integration decision |
| --- | --- | --- | --- |
| HTTP/API request ordering and status | Python `Service` | `serve/server.py`: `Service.fifo`, `status`, request queues and cancellation events. The `--batch` path is an explicit opt-in; control/slot file operations are rejected when they could interleave. | Keep API lifecycle in the existing service. Do not add a second scheduler. |
| Engine process and token protocol | `StrataEngine` plus the C++ serve loop | `serve/server.py`: `StrataEngine.generate`, `STOP`/`QUIT`, and `DONE` parsing. `src/program/generate.cpp`: request prompt, verification windows, output publication and finish status. | Python owns transport/process management; C++ owns per-request model execution and published tokens. |
| GDN, QSA KV/indexer, PLE history | `SessionState` | `include/strata/core/session.hpp`: `gdn_state`, `qsa_states`, `ple_hist`, and `ple_prev`; `session_init` carves state from a caller-supplied base and `session_release` removes registrations before that base is freed. | Keep one session as the authority for main-model persistent state. No duplicate NInfer-style state store is introduced. |
| Main-model speculative verification and commit | `Verifier` | `include/strata/core/verify.hpp`: `init(..., SessionState&)`, `run`, `commit(n_keep)`, `wait_commit`, and pipeline commit methods. Async commit requires the existing wait boundary before inspection. | Keep verifier graphs and commit transactions at this boundary. Callers choose the retained prefix. |
| MTP proposal state | `MtpDrafter` in the request loop | Draft generation and accepted/offered counters are handled by the C++ request loop; the MTP QSA state is separate from the authoritative main `SessionState`. | Treat MTP state as proposal/scratch state. Do not use it as proof of main-state parity. |
| Device allocations | Existing allocation owners (`DeviceArena`, `ExpertCache`, session arenas, verifier buffers) | `include/strata/core/device.hpp`: `DeviceArena` owns one CUDA allocation and its bump allocations. Session and verifier owners have their own lifetimes. | Retain local allocation ownership; Phase 3 must reconcile unique physical backing and overlapping views before extending admission accounting. |
| Physical memory authority and admission | Platform/memory checks plus existing allocators | `src/platform/memory.*`, the engine's shared-RAM headroom guard, and the Phase 1 control supervisor. Owner counters cover selected sites only. | One physical RAM authority remains. Do not add host RAM to CUDA capacity or claim a complete ledger from partial counters. |

## Transaction finding

Before the correction, the serve, ordinary decode and pipelined decode callers
committed `a+1` verifier inputs before clipping publication to the request's
remaining output budget or EOS. The direct model check showed equal token IDs but
different persistent state. `published_prefix()` now computes the one retained
output/input prefix used by those callers, including pipeline rollback and the
consumed-token history. Its eleven host-only tests cover accepted-prefix boundaries,
output limits and EOS.

The helper test proves the selector arithmetic. The post-fix Orin check also
confirms matching token IDs and nine persistent-state fingerprints for one
spec1/spec4 request clipped by the output budget. Cancellation/recovery, other
retained lengths, long-chain drift, and pipelined runtime behavior remain
untested. Exact allocation ownership and future reservations remain Phase 3
gates. The source-level ownership map does not supersede those measurements.
