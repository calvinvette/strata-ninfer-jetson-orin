# Accepted-prefix publication boundary

This is a direct model-level state check of Strata's greedy decode versus MTP
speculation using the pinned Orin IQ1_M pack and MTP files. Both arms use the
same candidate executable, weights, formatted prompt, 32-token output limit,
KV/cache settings and runtime environment; only the MTP window differs
(`--mtp-max-t 1` versus `4`). The generated output is a measurement, not a
committed fixture.

## Pre-fix result

The pre-fix run completed normally in both arms and emitted identical 32 token
IDs. MTP offered 27 drafts and accepted 23. Despite matching output, the
post-request fingerprints differed: state length was 1493 for spec 1 and 1494
for spec 4, and GDN, PLE, indexer, KV and PLE-history fingerprints differed.
The binary SHA-256 in both arms was
`ff158a467798e9cfc9b4d94d8cdc1e4fd88012b01266ef3b6227e55a18fb466e`.
This is a failed model-state parity cell, not evidence of a performance win.
The pre-fix run kept the default CPU-sharing setting; the focused rerun harness
disables prefill CPU sharing in both arms to reduce cross-process scheduling as
a numerical confound.

Inspection located an output-budget clipping issue in the service, CLI and
pipelined decode paths: verification could accept a longer prefix than the
request published, while commit kept the whole verifier match. The implementation
now limits commit and consumed-token history to the published output prefix,
including EOS clipping.

## Post-fix Orin result

On 2026-10-09, the active local machine (`orin1`, ARM64, Linux 5.15.148-tegra,
Orin nvgpu) ran the fixed candidate under `tools/integration/run_control.py`.
The test used existing model files in `/home/calvin/models/strata-orin-validation`,
the same 1462-token formatted prompt, and identical runtime settings except for
the MTP window (`--mtp-max-t 1` versus `4`). Both arms used candidate binary
SHA-256 `7c3b6e0a196db25d9d3546b7d23ccac90303f6d1967f736de6e30de047527da3`.

The arms emitted identical 32 token IDs and identical final fingerprints for
all nine captured state fields: sequence length, GDN, PLE, tail, dead-state,
pooled state, full pooled state, KV, and PLE history. Spec 4 offered 27 drafts
and accepted 23; the output limit clipped the final verifier window. The
supervisor passed with a 6 GiB floor and sampled minimum available physical
memory of 9,207,517,184 bytes (8.57 GiB). This is sampled host availability,
not CUDA-free-memory or energy measurement. Raw token/state results, engine
logs, supervisor report, tegrastats and memory samples are in `post-fix-orin/`;
identities are recorded in `post-fix-orin/SHA256SUMS`.

The native ARM64/CUDA `strata` and `published_prefix_test` targets rebuilt with
one job. The shared selector's eleven host checks, harness dry-run, conversation
cache tests and CLI help pass. The earlier restricted-shell integration suite
had two socket-test environment errors; the supervised model comparison here
passed. The GDN CUDA selftest did not run in that earlier managed-shell attempt,
so the model-level state comparison does not replace that operator test.

Follow-up backend validation now compiles the changed `src/program/generate.cpp`
with the maestro1 HIP toolchain, recompiles the updated `gdn_parity` target,
and completes a clean 123-step SYCL engine build. The SYCL port has a separate
`sycl/src/program/generate.cpp`, so its successful build does not compile the
changed HIP/native source. Details and source/binary hashes are in the [Phase 2
backend report](../2026-10-09-phase2-backend-build/README.md). No HIP or SYCL
GPU runtime result is claimed.

This test exercises one naturally occurring accepted-prefix length (23 of 27)
with a final output-budget clip. It does not qualify zero/intermediate/all
acceptance across controlled windows, EOS clipping, cancellation, long-chain
drift or pipelined runtime behavior. A separate supervised 8-token follow-up
matched emitted IDs and most state fields but found a `pooled_full` spare-row
mismatch; details are in the [short-prefix state report](../2026-10-09-short-prefix-state-followup/README.md).
These transaction and runtime cases remain Phase 5 work.

Raw pre-fix logs and results are retained beside this report. No model files,
build products, credentials or local environment files are included.
