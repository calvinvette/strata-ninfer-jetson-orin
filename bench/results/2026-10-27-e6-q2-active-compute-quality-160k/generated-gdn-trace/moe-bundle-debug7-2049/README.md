# E6 MoE bundle writer follow-up

## Result

A paired Q2_0 retrieval diagnostic completed on Orin with the Strata expert
backend and strict NInfer expert backend. It used the held-out 2,048-token
workload and captured token position 2,049 at model layers 1, 7 and 8. Both
arms returned the exact expected answer in 47 generated tokens, with identical
token IDs, resident maps and all nine final persistent-state fields.

Each arm emitted a 399,744-byte `STMOEBN1` bundle containing three records. The
independent bundle comparator found exact equality in route IDs and weights,
MoE input, each of ten expert outputs, shared output and combined output at all
three layers. Both files had SHA256
`95662cbe709cfad6c048807fbcc239425769998dad3353e9fbe9c307eaf77f20`. The
supervisor reported 11.77 GiB minimum available/admission memory and zero
cgroup OOM events. This is correctness/capture evidence, not a performance run.

## Root cause and fix

The GPU graph filled the opt-in bundle buffers for both ordinary and batch
verifier execution, but file serialization was called only by
`run_slot_rows`. This retrieval workload uses ordinary single-request
`Verifier::run`, which already had a separate writer for its residual boundary
capture. The ordinary path now calls the shared bundle serializer after the
captured device results are available, using the window's positions and the
ordinary-path slot marker (`-1`). Batch serialization remains unchanged.

## Reproduction and source identity

The run used Qwen3.8-Flash-Next Q2_0, config
`bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/config.json`, and
workload
`bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/input/workload.json`.
Prompt-content SHA256 was
`06f8532c00c06d82c474e562f42f0acd299ede4f90c01efbb405cc4085551349`; token-ID
SHA256 was
`46aed19a70a9df341e7e2362dfadbc543b6bdc4076e41fae6d94bf28ddd8097f`.

The diagnostic binary used for this capture was
`a4d31a011cfc7a245ff9878b1ecbc6be15395f5f633683fb83a7e2b43ec8c94c` and
included temporary, opt-in writer tracing used to confirm the call path. The
trace-only code was removed afterward. A subsequent Release rebuild of the
durable fix passed and produced binary SHA256
`fbd40926be198adc92cd9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`.
Integration Python discovery passed 207 tests.

Raw run logs, bundle files and supervisor telemetry remain local under this
directory and are excluded from Git. This short capture does not resolve the
state divergence observed in the 160K diagnostic; E6 remains open.
