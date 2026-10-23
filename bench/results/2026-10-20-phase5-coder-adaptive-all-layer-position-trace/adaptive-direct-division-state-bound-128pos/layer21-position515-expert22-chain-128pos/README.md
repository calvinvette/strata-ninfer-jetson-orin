# Layer-21 owner and verifier capture at position 515

This same-seed pair follows the confirmed layer-22 raw-state difference back
through the layer-21 MoE boundary. It uses the Coder IQ1_M model, binary
`0a5f9b0d…1996c`, seed `20261085`, and the opt-in layer-31/expert-22
reciprocal-SiLU selector. Both arms ran the 128-token short/long/short sequence
and captured layer-21 MoE routes, per-expert rows, combined outputs, all-layer
verifier MoE inputs, and the preceding layer-20 boundary.

The adaptive arm's layer-21 MoE input at position 515 is bit-identical between
the initial short request and recovery. Expert IDs and router weights are also
identical. The owner for rank 7 / expert 132 changes from CPU to GPU, however;
that expert's output row changes in all 2,560 values (relative L2 `0.014265`).
The other nine routed expert rows and the shared-expert output are exact. The
combined MoE output changes in all 2,560 values (relative L2 `0.002059`). The
full all-layer verifier-input capture confirms that layer 22 is the first
changed MoE input (relative L2 `0.0009497`). Thus the captured divergence enters
at layer 21 through adaptive CPU/GPU ownership of expert 132, not through a
changed route or router weight. This is a localization result; it does not yet
show whether the experimental layer-31 selector caused that ownership change.

Delayed control keeps expert 132 on CPU and is exact across routes, expert
parts, combined output, all captured MoE inputs, and the layer-20 boundary.
Both arms passed the supervisor. Minimum host/admission availability was
14.169 GiB adaptive and 14.200 GiB delayed control; cgroup memory events were
zero. Frequencies were observed dynamically with no clock changes; EMC
frequency was unavailable due to debugfs permissions, and energy was not
measured. Elapsed times were 629.9 and 602.8 seconds.

Raw captures and parsed evidence are retained here. `selected-position-analysis.json`
records selected MoE row/owner comparisons, each arm's `layer21-moe-analysis.json`
records route/part/output comparisons, and `moe-input-analysis.json` compares
the raw 48-layer verifier input records. The layer-20 boundary analysis is in
each arm's `result/layer20-boundary-analysis.json`. The [same-seed direct-division comparison](../layer21-selector-vs-direct-division.json) records the owner/output contrast. The pair is not a recovery fix and does not close Phase 5.
