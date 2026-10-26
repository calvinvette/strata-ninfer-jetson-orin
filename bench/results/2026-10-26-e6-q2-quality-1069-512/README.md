# E6 Q2_0 1,069-token task-quality diagnostic

This is a single-task diagnostic for the prompt used in the earlier E6
quality check. The original completion allowance could not satisfy its
200-word instruction, so this repeated prompt used a 512-token allowance.
The scoring checklist was written before either arm ran in
[`QUALITY_RUBRIC.md`](QUALITY_RUBRIC.md). It is not a general quality test,
state-parity result, or performance qualification.

Both arms used the same Q2_0 model files, 8,192-token context, 6-GiB resident
expert budget, 3,000 GPU-cache slots, prompt, and generation allowance. The
CPU-miss arm used the baseline backend configuration; the staged arm used the
strict NInfer expert backend. Each completed one warmup and one measured
request, naturally stopping before the 512-token limit. Raw request text,
engine output, residency, memory telemetry, and supervisor captures are local
only and are not committed.

| Arm | Measured output | Rubric 1: starts “Processor” | 200+ words | Fetch/decode/execute | Memory explanation | I/O or peripherals | No material factual error | Task result | Minimum available RAM |
|---|---:|---|---|---|---|---|---|---|---:|
| CPU-miss | 285 words | Fail (`A computer…`) | Pass | Pass | Pass | Pass | Pass | Fail: opening instruction | 11.10 GiB |
| NInfer staged | 268 words | Fail (`A computer…`) | Pass | Pass | Pass | Pass | Pass | Fail: opening instruction | 11.34 GiB |

Both completions gave a broadly accurate explanation of processor work,
memory, and input/output, but neither followed the required first word. Their
task-level outcomes are therefore both failures under the preregistered
rubric; the difference in wording does not establish a quality ranking.

The one measured request reported 8.2 predicted tokens/s for CPU-miss and 9.8
tokens/s for staged NInfer. These are single samples from a sequential,
task-quality diagnostic, with no uncertainty estimate. They are not a paired
performance result and do not offset the outstanding persistent-state and
broader quality gates. The minimum available memory in both runs remained
above the preserved six-GiB floor. No clock controls or service changes were
made; energy was not measured.
