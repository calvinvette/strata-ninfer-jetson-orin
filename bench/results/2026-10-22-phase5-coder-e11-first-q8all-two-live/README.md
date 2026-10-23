# Two-live Q8_1 owner-parity diagnostic

This re-analyzes a current-source, two-live target-only capture with the
temporary expert-11-first residency profile and `STRATA_NATIVE_CPU_Q8_1_DOT=all`.
It is a narrow correctness diagnostic, not a supported residency profile or a
performance result.

Two six-token requests were compared with fresh serial controls at committed
positions 68 and 71. Both batch token streams matched serial. At position 68,
all 36 GDN states were exact for both prompts. Prompt 0 / slot 1's rank-1 expert
248 changed primary-VRAM-to-CPU ownership on an identical activation, route and
router weights; all ten expert parts and the combined MoE output were bitwise
equal. At position 71, all expert parts and MoE outputs were also exact for
both prompts. Prompt 1 / slot 0 had all 36 GDN states exact. Prompt 0 / slot 1
first differed at GDN model layer 30: 619,151/817,152 values differ there,
with relative L2 `5.84e-9` and maximum absolute difference `1.27e-7`; its output
still matches all six serial tokens.

The supervised run passed with a 6 GiB physical-availability floor and no
sampled cgroup events. Minimum physical/admission availability was 17.32 GiB
over 143 samples; clocks were dynamic and energy was not measured. Since the
profile, sequence and sample count are narrow, this does not bound other routes,
longer chains, cancellation, MTP, or user-visible quality. Phase 5 remains open.

The compact parsed evidence is in [`analysis.json`](analysis.json). The source
capture and supervisor logs are under
`../2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/` and remain local-only.
