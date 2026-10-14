# Accepted-only adaptive window boundary check

This is correctness evidence for the accepted-prefix cap used by Strata's
opt-in adaptive MTP path. It does not establish a serving improvement or change
defaults.

## Implementation

`include/strata/spec/accepted_window.hpp` isolates the integer boundary rule:
the committed MTP window is capped to the remaining accepted-token allowance
before any chained window is admitted. It rejects invalid values and integer
overflow. The standalone test exercises 1,515 combinations and edge checks;
this extracted policy is also used by `src/program/generate.cpp`.

## Orin run

The clean supervised run used Qwen3.8-Flash-Next GSQ RCO Q2_0, the local
artifact-aware PLE pack, FP16 KV, a 2,048-token prompt, and 32 generated tokens.
The native GGUF shard was `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf`
(37,623,740,192 bytes), and the PLE shard was
`Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf` (28,800,138,432 bytes).
Both were already in the local `~/models/strata-orin-validation/Q2_0/`
directory; this run downloaded no models.
It compared MTP off/2/3/4 with accepted-only adaptation enabled and the same
config, at 3000 expert-cache slots and prefill 512. Prompt SHA256 is
`93cefb75fa4bb48eec0bcbf5771e06a6cce6bbad03c463df644fb45634b3dc15`; the
candidate binary SHA256 is
`5a72dbad8a79782a7cd778ab222fdcfe82f3665b25923767215f0f465bbcd213`.

All four arms emitted identical token IDs and matched all nine recorded
persistent-state fields at final state. Every shared accepted-prefix boundary
also matched exactly. MTP2/3/4 offered and accepted 17/10, 24/13, and 31/17
drafts. The supervisor exited successfully with a 6 GiB admission floor;
minimum physical host availability was 16.90 GiB and minimum admission
availability was 9.76 GiB. Sampled cgroup high/max/OOM counters remained zero.
Energy was not request-attributed. Timings are retained for context but are
single observations and are not a performance comparison.

The first launch had a malformed command separator and did not run. A corrected
preliminary run inherited capture variables and overwrote a tracked activation
fixture; the fixture was restored byte-for-byte from the parent commit. That
run is excluded. The clean run uses `config-accepted-window.json`, which removes
the activation-capture environment variables. Its supervisor and raw outputs
are in `supervisor-clean/` and `run-clean/`. The first maestro1 build attempt
also stopped because the isolated source bundle omitted Strata's vendored GGML
header; its licensed copy was added and the detached build resumed. That failed
attempt is not treated as build evidence.

## Reproduction

From the repository root on the Orin host:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-accepted-window-boundary/supervisor-clean \
  --timeout 7200 --interval 1 -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-14-phase5-accepted-window-boundary/config-accepted-window.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-14-phase5-accepted-window-boundary/run-clean \
  --prompt-tokens 2048 --tokens 32 --windows 0 2 3 4 \
  --use-config-adaptive-swaps --run
```

The C++ unit test reports 1,515 checks with zero failures. Selected accounting,
owner, graph, PLE and accepted-prefix CTests passed 18/18; integration Python
discovery passed 136/136. The Phase 3 PLE regression was rerun on the current
checkout: all seven artifact-aware stages passed for three tokens, with worst
relative L1 `1.148e-7`. Its supervised
minimum host availability was 24.51 GiB. Raw output and supervisor data are in
`ple-refresh/`.

## Portability builds

The shared-source change compiled and linked successfully with both backend
configurations on maestro1, an x86_64 host running Linux 6.8. HIP targeted
`gfx1100` using AMD clang 22.0.0git; SYCL used Intel oneAPI DPC++ 2026.1.1.
Both builds used one job. The HIP build completed 240 steps and the SYCL build
123 steps. `strata --help` passed for each binary, and the HIP build's
`accepted_window_test` reported 1,515 checks with zero failures. These results
are build/help evidence only; maestro1 supplied no Orin performance or GPU
runtime qualification.

Binary SHA256 values:

| Backend | SHA256 |
| --- | --- |
| HIP | `7090a616d355f6c254d2464f213b5d9a404da57cd1b9a763f7ec5bfd045afba4` |
| SYCL | `18837ef51b301dd4d09cc63ea1adc7e0ce5f87d11f7e4d6352480f97bdb1983d` |

Full configure/build logs, help output, the HIP unit-test output, source hashes,
and toolchain identity are retained under `maestro1/logs/`.
