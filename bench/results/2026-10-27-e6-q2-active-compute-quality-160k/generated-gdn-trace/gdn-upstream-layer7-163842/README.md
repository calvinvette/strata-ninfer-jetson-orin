# E6 same-position upstream GDN/boundary capture

## Outcome

A paired 160K Q2_0 retrieval run captured layer 7 and 8 residual boundaries,
layer 7 MoE internals, layer 8 GDN inputs/raw output, and layer-8 state at
positions 163,841 and 163,842. Both arms returned the exact expected answer in
47 tokens with identical token IDs and expert residency. Final persistent
`gdn`, `tail`, `pooled`, `pooled_full`, and `kv` still differed.

At accepted position 163,842, every captured layer-7/8 boundary field matched
bitwise, including `next_layer_xn`. Layer 7 route IDs/weights, input, all ten
expert parts, shared output, and combined output also matched exactly. Layer 8
raw GDN `o` and normalized `y` were bitwise equal. Both independent recurrence
replays produced the same relative L2 error, `1.32e-7`, against the FP64
equation oracle. The layer-8 pre/post state captures were also identical at
163,841 and 163,842.

This does not close the long-context state mismatch: the final state still
differs. It does show that this capture trajectory had no layer-7/8 split at
163,842, in direct contrast with the previous focused run at the same position,
which saw GDN `x` differ by `3.90e-4` and post-step state differ by up to
`9.10e-4`. Other timelines found yet different first-split positions. The
diagnostic instrumentation is therefore changing or selecting different
execution trajectories; these captures cannot establish a stable earliest
divergent operation. More instrumentation at this same point is unlikely to
resolve the discrepancy. Preserve the state-parity failure and assess it with
repeatable, minimally instrumented paired runs before making a backend change.

The supervisor sampled 3,063 records over 54.06 minutes. Minimum available
memory was 6.51 GiB, peak swap 1.50 GiB, and sampled cgroup OOM-kill counters
were zero. Clocks were read without control; energy was not measured.

## Reproduction and artifacts

The run used the E6 Q2_0 config/workload and Release CUDA executable SHA256
`fbd40926be198adc92de9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`.
All raw captures, comparisons and supervisor telemetry remain local-only.
This is a correctness diagnostic, not performance evidence or qualification.
