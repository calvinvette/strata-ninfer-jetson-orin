# MTP logits owner trace check — Orin — 2026-10-11

The MTP draft logits allocation in `MtpDrafter::bind()` was missing from the
opt-in unique-allocation trace, and its destructor freed it without a matching
owner event. The implementation now records the exact requested size at the
successful CUDA allocation and emits the matching free only when `cudaFree`
succeeds. This is owner accounting only; it does not alter admission or add a
second memory authority.

The rebuilt native CUDA candidate passed the seven-scenario IQ1_M/MTP API
protocol run under the six-GiB physical-availability supervisor. Repeated
requests, OpenAI streaming, Anthropic streaming, decode cancellation and
prefill cancellation/recovery all passed. Minimum `MemAvailable` was
10,563,428,352 bytes (9.84 GiB). The owner trace balanced 53 allocations and
53 frees, with zero observed live bytes on host and device at process teardown.
The `mtp` owner peaked at 20,137,424 requested bytes and ended at zero. The
existing payload snapshot is 1,061,718,712 bytes and remains a separate counter;
it is not added to unique allocations.

The trace is opt-in and the runtime configuration keeps the existing IQ1_M
model, MTP weights, tokenizer, 4K context, spec4, 3 GiB workspace reserve and
loopback-only server. Model artifacts remain in `~/models/strata-orin-validation/`.
This run checks the MTP allocation/free path and cancellation cleanup, not graph
pool bytes, total physical ownership, speed, or a general memory threshold.

Validation on the rebuilt candidate:

- Artifact-aware Q2_0 `ple_parity` passed using the real layer-1 pack and GGUF table shard.
- Ten selected PLE, ownership, cache refusal, graph trace, pinned fallback, and Q2 reference CTests passed.
- Integration Python unittest discovery passed 92/92.
- Real IQ1_M/MTP API protocol passed 7/7; 53/53 owner allocation/free events balanced.
- Build used one job on Orin; `git diff --check` passed.

The first attempt invoked system Python and stopped before API requests because
that interpreter lacked `requests`. The reported validation run used the
existing `pack-venv` interpreter and completed successfully.
