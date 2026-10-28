# E6 layer-8 GDN and MoE diagnostics

## Result

This paired Q2_0 retrieval diagnostic used a 163,840-token prompt and captured
the accepted token at position 163,849 in both Strata and strict-NInfer arms.
Both arms returned the exact expected answer in 47 generated tokens, with
identical token IDs and expert residency. Final persistent `gdn`, `tail`,
`pooled`, `pooled_full`, and `kv` fields still differed; `L`, `ple`, `dead`,
and `ple_prev` matched. This is a failed state-parity diagnostic, not a
performance result.

The bundle comparison again found the first observed split in layer 7 expert
arithmetic. Layer 7 route IDs, route weights and input were exact; expert parts
differed in 1,886/25,600 values (relative L2 `3.55e-8`, maximum absolute
`1.49e-8`), producing a combined-output difference of relative L2 `3.82e-8`
and maximum absolute `3.73e-9`.

At layer 8, the GDN raw output `o` differed in 6,139/6,144 values (relative L2
`6.49e-5`, maximum absolute `3.11e-5`); normalized `y` differed in
6,141/6,144 (relative L2 `7.08e-4`, maximum absolute `2.02e-4`). By the layer
8 MoE input, all 2,560 values differed (relative L2 `7.37e-4`, max
`0.00149`). Route IDs remained exact, while all ten route weights differed
(relative L2 `2.91e-4`, max `6.94e-5`). Expert parts, shared output and
combined output differed with relative L2 `0.00752`, `0.01379`, and
`0.00825`, respectively.

This is consistent with the layer-7 rounding-scale expert delta propagating
through layer 8 GDN and becoming larger before MoE routing. It does not prove
that GDN is the only amplifier, establish causal direction, or identify which
backend is more accurate. Instrumentation and run sensitivity remain concerns:
prior captures at the same position have shown different first-split layers
and magnitudes. The layer-7 expert outputs were therefore checked against the
independent Q2_0 oracle; the next useful step is instrumenting layer-8 GDN
inputs/stages in a controlled repeat.

The independent layer-7 check has now been run for all ten selected experts
using the shared captured activation, route IDs, and Q2_0 GGUF shard with Q8_1
activation quantization and FP64 accumulation. For nine experts, Strata and
NInfer expert parts were equally close to the oracle (relative L2 approximately
`5.74e-8`–`9.42e-8`). For one expert, NInfer was closer (`5.96e-8`) than Strata
(`9.15e-8`). These small errors support correct operator behavior and show no
systematic backend winner in this sample; they do not establish end-to-end
correctness or explain the layer-8 propagation.

The supervisor sampled 3,066 records over about 54 minutes. Minimum available
memory was 6.58 GiB, peak swap 1.38 GiB and sampled cgroup OOM-kill counters
were zero. Clocks were observed without control; energy was not measured.

## Reproduction and artifacts

The run used the parent report's Q2_0 model/config/workload and Release CUDA
binary SHA256
`fbd40926be198adc92de9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`.
Comparison JSON and raw captures are local-only in this directory. The compact
comparison outputs were generated with `compare_boundary_capture.py`,
`compare_moe_bundle.py`, and `compare_gdn_o.py`. No model, raw capture, or
supervisor log is committed. E6 remains open; no quality qualification or
performance claim follows from this diagnostic.
