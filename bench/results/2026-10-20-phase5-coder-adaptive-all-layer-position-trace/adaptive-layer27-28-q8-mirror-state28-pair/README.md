# Layer-27/28 Q8_1 owner mirrors — Orin — 2026-10-20

This short-only, same-service pair added opt-in Q8_1 mirrors at layers 27 and
28 to the existing layer 1/3/4/6/8/9/10/11/12/13/15/16/19/24 selector set.
It used seed 20261081, three repeated 512-token requests, 12 generated-token
limit, no prompt cache, and the pinned Coder IQ1_M model at revision
`5348543e0147355ac9cbcb031184a3546350988e`. Candidate binary SHA256:
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`.
Both supervised arms passed with at least 14.12 GiB host/admission
availability and zero cgroup events.

At layer 27, expert 175 changes CPU-to-CUDA with the same input and routes; the
same-input Q8_1 CPU and CUDA outputs are bit-identical. At layer 28, experts
146 and 36 change owner with unchanged layer input and routes; the selected
expert-36 CPU/CUDA oracle and service rows match exactly. Layer-28 `ffn_y`,
intermediates and raw committed recurrent/convolution state are bit-identical
across all three requests, with the state hash cross-checked to service GDN
ordinal 21. The first changed recorded dispatch input moves to layer 30.

This intervention does not restore global adaptive accepted-state parity: all
12 compared accepted-prefix state fingerprints still differ, and this run's
adaptive initial/recovery token IDs differ at 9/12 positions. Delayed control
remains exact. The opt-in mirrors are diagnostic only; Phase 5 remains open.

The raw route/oracle/state captures and analyses are retained beside this
report. The exact launch and randomized arm order are in each arm's `launch.txt`
and the campaign manifest.
