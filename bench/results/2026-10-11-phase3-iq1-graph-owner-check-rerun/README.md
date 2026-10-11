# IQ1_M/MTP graph-owner trace coverage rerun

This is a trace-coverage check, not a memory-sizing or performance result. The
IQ1_M candidate ran the seven real-model API/cancellation scenarios with
speculative decoding enabled. The six-GiB physical host-headroom supervisor
passed; minimum `MemAvailable` was 8,291,631,104 bytes (7.72 GiB). All seven
protocol scenarios passed, including OpenAI and Anthropic streaming, decode
cancellation, and prefill cancellation followed by successful recovery.

The driver wrapper observed ten successful `cudaGraphInstantiate` calls. The
integration owner trace observed ten corresponding graph-instantiation events:

- 3 verifier window graphs
- 1 verifier commit graph
- 2 MTP device-prefill graphs
- 2 MTP round graphs
- 2 MTP step graphs

The events are adjacent to the runtime instantiation timestamps and identify
owner instance/device plus graph class. This closes attribution for the graph
calls observed in this one IQ1_M/MTP request sequence. It does not count graphs
that were already instantiated before the traced interval, price CUDA graph
pools, or establish completeness for every runtime configuration. The earlier
unpatched check in the parent directory observed the same ten runtime calls but
only four owner labels; it established that six MTP captures needed labels.

`graph-owner-validation.json` contains assertions over the runtime probe, owner
events, protocol scenarios, headroom result and owner-ledger totals.
`owner-summary.json` reports 104 allocation and 104 free events, with zero
observed requested allocation bytes live at log end. These are instrumented
sites only and do not represent total physical memory. The process probe,
configuration, logs, supervisor samples, and protocol output are retained here.

Validation:

- Native CUDA `strata` target rebuilt on Orin; binary SHA256 is recorded in
  `source-sha256.txt` and `backend-builds.json`.
- HIP `strata` target rebuilt on maestro1 with one job. This is x86 build
  evidence only.
- SYCL's changed MTP translation unit compiled on maestro1. A full SYCL target
  link was not run because the configured tree triggered a clean 94-object
  rebuild; an earlier bounded full-target attempt was interrupted to avoid
  consuming the memory-limited host. This is not SYCL runtime evidence.
- The focused owner-observation Python tests passed (22 tests); full integration-tooling unittest discovery passed (75 tests).
- A fresh six-GiB supervised CTest selection passed all five tests: `conversation_cache_test`, `conversation_memory_test`, `vmm_test`, artifact-aware Q2_0 `ple_parity`, and `expert_cache_memory_test`. Minimum `MemAvailable` was 24.48 GiB.

The independent artifact-aware Q2_0 PLE oracle and focused memory/PLE CTest
batch passed earlier in this Phase 3 continuation; see
[`2026-10-11-phase3-current-ple-memory`](../2026-10-11-phase3-current-ple-memory/README.md).
The PLE result uses real layer-1 weights and table rows but synthetic hidden
state/history; it is not a full-model quality result.

This trace-only change does not promote or import a NInfer component. It remains
specific to Strata's CUDA/HIP and SYCL MTP graph ownership paths. For a future
Strata + Splash integration, identify each native graph creation site and emit
owner labels after successful instantiation; calibrate the platform memory
counter independently and never infer executable bytes from the owner count.
