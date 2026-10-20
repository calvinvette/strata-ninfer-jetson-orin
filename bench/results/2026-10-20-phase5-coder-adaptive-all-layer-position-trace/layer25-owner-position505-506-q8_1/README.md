# Layer-25 owner trace with IQ3_S/IQ4_NL CPU Q8_1 mirror — Orin — 2026-10-20

This randomized same-service pair used the pinned Coder IQ1_M model, candidate
binary `9212d814…`, and `STRATA_NATIVE_CPU_Q8_1_DOT=all`. It captured all-layer
dispatch rows at positions 505 and 506 plus layer-25 verifier routes, expert
parts, shared output and combined MoE output. Both arms passed under separate
28-GiB supervisors.

At position 505, adaptive migration still changes expert 183 from CPU to GPU.
Its same-input output matched the GPU output from `native_expert_parity` exactly
after the opt-in IQ3_S/IQ4_NL Q8_1 mirror. Initial and recovery layer-25 inputs,
expert IDs, router weights and owner-independent verifier routes match. Across
both selected positions, all routed expert parts, shared-expert outputs and
combined MoE outputs are bit-identical between initial and recovery requests.
The delayed control is also bit-identical across those captured fields.

This local operator boundary is now exact at positions 505/506, but it does not
resolve the sequence-level state mismatch. The adaptive arm returned the same
recovery token IDs while its `gdn`, `tail`, `pooled`, `pooled_full`, and `kv`
fingerprints still differ from the initial short request. The delayed arm's
fingerprints match. Minimum host/admission availability was 14.25 GiB for
adaptive and 14.36 GiB for delayed, with zero sampled cgroup memory events.
This is correctness localization, not a migration fix, performance result or
quality comparison.

`owner-analysis.json` compares per-layer activation, IDs and route owners.
`adaptive-layer25-verifier-comparison.json` and
`delayed-layer25-verifier-comparison.json` compare the selected verifier rows
and include raw capture hashes. The independent same-input expert parity
artifacts and FP32 vectors are retained in the parent
`../layer25-owner-position505-506/operator-checks/expert183/q8_1-mirror/`
directory. The enclosing result report documents the paired-run reproduction
command and remaining limitations.
