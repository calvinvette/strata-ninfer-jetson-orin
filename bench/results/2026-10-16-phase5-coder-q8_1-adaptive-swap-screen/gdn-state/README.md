# Direct GDN state magnitude follow-up — Orin — 2026-10-16

This follow-up measures the FP32 GDN state after a short prompt, rather than
relying only on the engine's state hash. It uses the same current Strata binary
(`c07cf3f634788d055316cbf345a2fa17dd66449cb5ddd8690781dbbd72403c88`) and
the same `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M artifact
(revision `5348543e0147355ac9cbcb031184a3546350988e`) as the parent screen.

Three supervised runs captured state at L=527 after the same 512-token prompt:

| Run | Sequence | Adaptive cadence | Accepted output IDs vs initial | GDN state vs initial |
| --- | --- | ---: | ---: | --- |
| `initial-default` | short 512 | 100,000 | exact | reference |
| `post-long-delayed-default` | long 2,048, then same short 512 | 100,000 | exact | bit-identical |
| `post-long-active-default` | long 2,048, then same short 512 | 4 | 16/16 differ | 29,414,608 / 29,417,472 floats differ |

The delayed run reproduces the initial short-run GDN dump byte-for-byte after
the long request. In the active-swap run, 99.9903% of GDN floats differ from
that matched state. Relative L2 difference is 0.7376, maximum absolute
difference is 17.7336, and mean absolute difference is 0.026689. Per-layer
relative L2 ranges from 0.5835 to 0.8942. The active run passed all seven
adaptive byte and residency checks. Minimum host/admission availability was
14.45 GiB; the delayed run's minimum was 14.24 GiB. Both ran under
`MemoryMax=28G` with zero cgroup memory events.

This is direct evidence that active adaptive migration in this tested sequence
is associated with a large persistent GDN-state change and changed continuation
tokens. It does not identify which internal mutation causes the difference,
measure KV or PLE numeric state, establish task-quality impact, or qualify other
models/profiles. This remains a one-run-per-arm diagnostic follow-up; Phase 5
confirmation is still open. EMC readback was denied; energy was not
request-attributed and clocks remained dynamic.

Each `result/analysis.json` records request IDs, state hashes, raw-dump SHA256,
dimensions and binary identity. The little-endian dump starts with a
32-byte `STGDN01\0` header (`cells`, `layers`, `floats_per_layer` as uint64),
followed by layer-major FP32 values. Run logs, telemetry, hashes and per-layer
comparison output are retained in this directory. The three compressed
full-state dumps are kept locally at
`~/models/strata-orin-validation/integration-captures/2026-10-16-coder-gdn-state/`
because each is about 110 MB compressed and together they add about 330 MB to
the repository. `dump-sha256.txt` records their hashes; rerun the capture script
to regenerate them.

Reproduce the numeric comparison with:

```sh
gcc -O3 -o /tmp/compare_gdn_state gdn-state/compare_gdn_state.c -lm
/tmp/compare_gdn_state \
  <(gzip -dc ~/models/strata-orin-validation/integration-captures/2026-10-16-coder-gdn-state/initial-default.gdn-state.f32.gz) \
  <(gzip -dc ~/models/strata-orin-validation/integration-captures/2026-10-16-coder-gdn-state/post-long-active-default.gdn-state.f32.gz)
```

The comparison program also prints per-layer changed-value counts, relative L2
and maximum absolute difference. Reproduction runs use `dump_gdn_state.py` and
the `run_control.py` invocations retained in the supervisor directories.
