# Current-source CUDA native-expert parity dump — Orin — 2026-10-16

This targeted runtime test covers the current `native_expert_parity` utility,
including its new `--dump-f32-dir` option. The tested source is the same as
`e6a55b30f596ecc5173d2eb55a4087662b7ee88f` for code; later commits through
`e0138898599ca9e412bf90b38377b02a798ba0bd` changed documentation and recorded
results. The utility binary SHA256 is
`dab5b63f5cb655cbf4ce66e3da860bb036147bff174c3b8cffac580a2d5436ab`; the
serving binary remains `57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`.
The model is the pinned `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`
IQ1_M artifact documented in the [Phase 7 model identity report](../2026-10-15-phase7-current-source-coder-iq1m-256k/README.md).
Model files stay under `~/models/strata-orin-validation/`.

The CUDA target rebuilt successfully with one build job. The Orin test opened
the first model shard, selected layer 0 expert 0, generated the requested float
dumps, and returned zero failures. The utility reported GPU dequantization
bitwise equal to the independent `ggml` `to_float` conversion for all
4,915,200 values, including fp16 conversions; embedding rows also matched
exactly. Its width-invariance checks found zero differing rows, and the two GPU
kernel paths were bitwise equal. For the expert output, reported relative error
against float was 1.22% CPU and 1.12% GPU; CPU/GPU relative difference was
1.39%. The utility classified this sampled expert case as `ok`. This is a
single layer/expert operator test, not full-model quality evidence.

The successful run and a repeat both exited 0 in 1.08 and 1.07 seconds. All
seven float dump files had identical SHA256 hashes across runs; hashes are in
`dump-output-sha256.txt`. The large transient dequantized-weight dumps were
removed after comparison. Each run sampled host availability twice, with a
minimum of 24.62 GiB, safely above the six-GiB floor. Clocks remained dynamic;
no power or clock settings were changed. EMC clock readback was unavailable.

The first attempt exited 1 because the requested dump directory did not yet
exist. The retry created it and passed; all attempts and memory/clock supervisor
records remain in this directory. This targeted runtime check covers the only
code difference since the full current-source Orin CUDA regression. It does not
replace a new full CTest/Python regression or cross-engine comparison. Phase 8
remains open.
