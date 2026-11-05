# Coder IQ1_M 8K retrieval accepted-prefix state check — Orin — 2026-11-05

A single guarded pair compared Strata and strict NInfer on the exact 8,192-token
active-ticket retrieval prompt, with a 16,384-token context reservation, static
expert profile, greedy sampling, `--spec 2`, and accepted-prefix state capture.
Both returned `73192` with identical six token IDs. All 11 final state fields
matched. At shared accepted-token checkpoints 1, 2, 3 and 6, all 11 state
fingerprints matched between backends. The last commit accepted three tokens,
so interior states 4 and 5 were not sampled.

The supervisor passed in 774.4 seconds. Minimum host/admission availability was
20.70 GiB, sampled swap peaked at 1.38 GiB, and the pre-existing cgroup OOM-kill
counter remained at one. Clock readings were observational; EMC readback was
unavailable and energy was not measured. This is one instrumented functional
pair, not a repeatability, task-quality breadth or performance result. The
capture can affect scheduling; final-only repeated checks are reported
separately in [`../retrieval-8k-final-only/README.md`](../retrieval-8k-final-only/README.md).

The compact result record is [`results.json`](results.json). Raw service logs
and supervisor telemetry remain in the adjacent local run directories and are
not part of this report.
