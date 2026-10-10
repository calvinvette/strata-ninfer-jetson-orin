# Automatic cache reservation observations — Orin

Run date: 2026-10-09, local `orin1` (ARM64, Linux 5.15.148-tegra, Orin nvgpu).
The candidate was built natively with one job. Existing model files stayed in
`/home/calvin/models/strata-orin-validation`. The explicit config was changed
only from a fixed 5000-slot cache to `--expert-cache auto`; other harness
settings paired spec1 and spec4. Opt-in tracing reported planned cache holds
separately from allocation records.

The spec1 arm reported 3072 MiB VRAM slack and 225,639,656 bytes for MTP bind.
The spec4 arm reported 3072 MiB slack and 227,626,216 bytes for MTP bind. The
config requested a 64-token prefill chunk, but the sizing predicate considered
the profile cache borrowable and emitted no prefill-workspace reservation. At
runtime, both logs say there were too few cache slots to borrow and the prompt
path allocated its own buffers; the owner trace measured a 228,829,184-byte
prefill peak in each arm. The general 3072 MiB VRAM slack remains in the
cache-sizing budget for later allocations, so this does not establish an
admission failure or a reserve breach. It does show that the per-component
reservation forecast and actual owner path differ; measuring the resulting
free-memory margin and accounting for overlap remains Phase 3 work. No pipeline
windows were requested. The parser observed 30 allocations and 30 frees in
each arm; it does not claim these are all allocations or total physical
ownership. Planned reservations are metadata and are never added to those
allocation totals.

Both arms emitted identical 8-token IDs and finished at state length 1469.
Spec4 offered 9 drafts and accepted 7. The `pooled_full` spare indexer-row
fingerprint differed, so the harness correctly recorded a state-parity failure.
The supervised command returned 1 because of this comparison, not a memory
pressure abort. Minimum sampled available physical memory was 7,945,687,040
bytes (7.40 GiB), above the 6 GiB floor. Raw memory and tegrastats are retained;
energy was not measured. This is a diagnostic observation, not a performance
comparison or memory-ownership closure.

The raw paired logs, parsed owner summaries, config, supervisor output and
identity hashes are provided here. Verify them with `sha256sum -c SHA256SUMS`.
The root `generate.cpp`, expert-cache and expert-source instrumentation rebuilt
natively on this Orin machine. The changed expert-cache and expert-source files
and headers rebuilt under maestro1's HIP toolchain with one job; source hashes
matched. The shared expert-cache header compiled in maestro1's SYCL build, using
its separate unchanged cache source. Logs and binary hashes are in
`native-cuda-build.log`, `native-cuda-hashes.txt` and `maestro1/`. HIP is x86
compile/help evidence only; no AMD runtime was tested. SYCL linked after
supplying its pinned oneMKL library path; `strata --help` is unsupported because
maestro1 has no SYCL device. No HIP/SYCL GPU runtime was tested. A later
supervised run added the primary
SessionState backing event; its raw owner records and short-prefix state result
are in the [session-trace follow-up](../2026-10-09-short-prefix-state-followup/README.md).
No model files or build products are included.
