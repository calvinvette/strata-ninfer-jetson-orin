# Mode-matched expert 39 CPU/GPU oracle

This oracle uses the same captured layer-16 position-515 service activation and
`STRATA_NATIVE_CPU_Q8_1_DOT=all` selector as the CPU-owner service capture.
Expert 39 changes from CPU to VRAM ownership alongside expert 118, but the
same-input CPU and CUDA oracle rows for expert 39 are bit-identical. The direct
CPU-pool service capture matches its mode-matched standalone CPU oracle within
maximum absolute difference 5.0e-11 and relative L2 8.69e-10.

The corresponding component accounting is in
`../owner-transition-contribution-analysis.json`. Under unchanged input,
expert IDs and router weights, expert 39 contributes no measured owner-path
output delta; expert 118 contributes the full measured delta among these two
migrating experts. Other experts are assumed unchanged because their owner and
inputs are stable. The combined verifier parts buffer is a CUDA-side tensor,
not an independent observation of the service's mixed-owner output.

The supervised oracle passed with 24.49 GiB minimum host/admission availability
and no cgroup memory events. It is one operator input, not end-to-end state or
performance evidence. The reproducible command is the expert-118 command in the
sibling `../expert118-oracle-cpu-q8-1-all/README.md`, with `--expert 39` and this
folder used as `--dump-f32-dir`.
