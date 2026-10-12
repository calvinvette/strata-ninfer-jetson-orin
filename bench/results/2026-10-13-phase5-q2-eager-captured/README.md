# Q2_0 eager and captured routed-expert decode — Orin — 2026-10-12

This Phase 5 check adds a real eager execution path for the native MoE route.
`session_eager` calls each layer's existing pre/router half, synchronizes before
reading its mapped doorbell, dispatches the existing GPU-hit and CPU-miss
callbacks, copies the miss outputs to the layer's parts buffer, and runs that
same layer's post/combine half. `--no-capture` uses this path when the expert
pool is enabled; `--no-capture --no-pool` retains the GPU-only direct path.
Profile-backed serving still prepares the residency table required by the MTP
verifier, even when target layers run eagerly.

The current CUDA Release build passed on Orin. The final supervised focused
CTest run passed 9/9: `published_prefix_test`, `spec_verify_parity`,
`ple_parity`, `captured_graph_trace_test`, `coupled_draft_test`,
`spec_prob_test`, `ple_reader_selftest`, `native_dense_ple_key_test`, and
`dequant_q5_1_test`. Raw output and telemetry are under
`supervisor-ctest-final/`. Q2_0 serving also executes the PLE path in both eager and
captured arms.

The model comparison used the same binary (`1135dd9093a7bbf15c874516bc75886a029d4d149196898b15023ad95907d047`), exact
512-token formatted prompt (SHA256 `ca13a79c83650d0bda01e8db5cc641308e496ff8342cb17471916c8d0a502729`),
Q2_0 weights, 3,000-slot profile-filled cache, FP16 KV, 64K context, and eight
generated tokens. MTP-off and window-2 arms ran sequentially in each mode under
a 28-GiB cgroup cap and six-GiB availability floor. The two modes emitted the
same IDs; all nine final persistent-state fields and every accepted-prefix
trace matched arm by arm. Window 2 offered and accepted four drafts in both
modes. See `capture-eager-comparison.json` and the raw `eager-run-sourcefinal/` and `captured-run-sourcefinal/` outputs.

| Mode | MTP | Prompt ms | Decode ms | Minimum host availability | Minimum admission headroom |
| --- | ---: | ---: | ---: | ---: | ---: |
| Eager | off | 16,157.8 | 4,688.6 | 15.47 GiB | 13.79 GiB |
| Captured | off | 14,532.8 | 4,720.8 | 15.52 GiB | 14.31 GiB |
| Eager | 2 | 17,531.6 | 4,004.6 | 15.47 GiB | 13.79 GiB |
| Captured | 2 | 16,746.4 | 3,902.8 | 15.52 GiB | 14.31 GiB |

These are single, sequential correctness runs with dynamic clocks, not
randomized paired performance repetitions; they do not qualify a speed claim.
EMC sampling was unavailable and energy was not measured. No clocks or
services were changed. The 28-GiB cap applies to each runner; the six-GiB floor
is whole-board available memory.

Earlier startup probes exposed harness validation and verifier residency
requirements before any request ran; their supervisor and engine logs remain
under `supervisor-eager/`, `supervisor-eager-8/`, `supervisor-eager-pair/`,
`supervisor-eager-final/`, and `eager-run-final/`. The corrected run is retained
under `supervisor-eager-ready/` and `eager-run-ready/`. The current-binary final
runs are under `supervisor-eager-sourcefinal/`, `eager-run-sourcefinal/`,
`supervisor-captured-sourcefinal/`, and `captured-run-sourcefinal/`.

The focused transaction/PLE test commands were:

```sh
ctest --test-dir build/integration/candidate --output-on-failure \
  -R '^(ple_parity|published_prefix_test|spec_verify_parity|captured_graph_trace_test|coupled_draft_test|spec_prob_test)$'
ctest --test-dir build/integration/candidate --output-on-failure \
  -R '^(ple_reader_selftest|native_dense_ple_key_test|dequant_q5_1_test)$'
```

This validates eager/captured correctness for the exercised Q2_0 prompt and
MTP settings. Pool sizing/resizing, other termination paths, long chains,
quality, and randomized eager-versus-captured performance remain open Phase 5
gates.
