# Coder IQ1_M 8K retrieval accepted-prefix state check — Orin — 2026-11-05

Two fresh guarded pairs compared Strata and strict NInfer on the exact 8,192-token
active-ticket retrieval prompt, with a 16,384-token context reservation, static
expert profile, greedy sampling, `--spec 2`, and accepted-prefix state capture.
Both returned `73192` with identical six token IDs. In both pairs all 11 final
state fields matched. At shared accepted-token checkpoints 1, 2, 3 and 6, all
11 state fingerprints matched between backends and reproduced across pairs.
The last commit accepted three tokens, so interior states 4 and 5 were not
sampled.

The supervisors passed in 774.4 and 789.8 seconds. Minimum
host/admission availability was 20.70 and 20.99 GiB; sampled swap peaked at
1.38 and 1.86 GiB. The pre-existing cgroup OOM-kill counter remained at one
in both pairs. Clock readings were observational; EMC readback was unavailable
and energy was not measured. This is state and answer evidence for one task
and diagnostic setting, not a broad quality or performance result. The capture
can affect scheduling; final-only checks are reported separately in
[`../retrieval-8k-final-only/README.md`](../retrieval-8k-final-only/README.md).

The compact result record is [`results.json`](results.json). Raw service logs
and supervisor telemetry remain in the adjacent local run directories and are
not part of this report.
