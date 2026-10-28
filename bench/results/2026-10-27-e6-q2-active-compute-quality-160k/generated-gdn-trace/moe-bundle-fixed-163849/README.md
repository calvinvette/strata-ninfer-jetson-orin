# E6 160K MoE bundle and boundary capture

## Outcome

The corrected bundle writer was exercised in a paired Strata-versus-strict-
NInfer run of the held-out Q2_0 retrieval task. The prompt contained 163,840
tokens; token position 163,849 was selected for all captures. Both arms returned
the exact expected answer in 47 generated tokens, with identical token IDs and
the same 3,000-expert resident map. Final persistent state still differed in
`gdn`, `tail`, `pooled`, `pooled_full` and `kv`; `L`, `ple`, `dead` and
`ple_prev` matched. This remains a failed state-correctness cell, not a
performance result.

Both arms emitted all 47 residual-boundary records (8,666,800 bytes each) and
three-layer MoE bundles (399,744 bytes each). The boundary comparison found
exact equality through layers 0–6. The first recorded difference was layer 7's
MoE output: 638/2,560 values differed, relative L2 `3.82e-8`, maximum absolute
delta `3.73e-9`. The layer-7 bundle confirms route IDs, route weights and MoE
input were exact; 1,886/25,600 expert-part values differed (relative L2
`3.55e-8`, max `1.49e-8`), leading to the same tiny combined-output delta.

At layer 8, route IDs still matched, but all ten route weights differed
(relative L2 `2.96e-4`, max `8.10e-5`). The MoE input differed in all 2,560
values (relative L2 `6.54e-4`, max `0.001675`); expert parts, shared output
and combined output had relative L2 differences `0.00706`, `0.01672` and
`0.00922`. The all-layer boundary shows the difference growing across layer
8's residual/normalization path. This locates the first observed perturbation
at layer 7 expert arithmetic and the large amplification by layer 8's MoE
input; the exact intervening operation and which result is more accurate remain
unknown. See the compact machine outputs in the local-only
`moe-bundle-comparison.json` and `boundary-comparison.json`.

The supervisor recorded 54.44 minutes elapsed, minimum available memory
6.87 GiB against the 6 GiB floor, peak swap 6.08 GiB, and zero cgroup OOM
kills. Clocks were observed without controls; energy was not measured.

## Reproduction and identity

The run used the Q2_0 config and workload in the parent report directory and
the Release CUDA executable SHA256
`fbd40926be198adc92cd9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`. The
paired harness reported failure only for final-state mismatch. Bundle and
boundary parsing/comparison completed for both arms. Raw logs, captures and
supervisor telemetry remain local-only under this directory.

The underlying serializer defect and its short 2K validation are described in
the [bundle-writer follow-up](../moe-bundle-debug7-2049/README.md). E6 remains
open; the next diagnostic should replay the exact layer-7 output delta through
the operations leading to layer 8 MoE input, then use an independent expert
operator oracle to bound backend arithmetic error before any performance
qualification.
