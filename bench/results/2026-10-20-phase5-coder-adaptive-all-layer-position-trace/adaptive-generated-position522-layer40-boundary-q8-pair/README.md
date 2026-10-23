# Position-522 layer-40 residual boundary — Orin — 2026-10-20

This supervised same-seed pair used the pinned Coder IQ1_M model, all eligible
layer-specific Q8_1 rules, prompt cache disabled, and the current candidate
binary. It captured the verifier residual/hyperconnection state after layer 40,
before layer 41's read, and immediately after that read at generated position
522. Both arms passed; minimum host/admission availability was 14.15 GiB
adaptive and 14.22 GiB delayed, with no cgroup memory events.

All eight captured fields were bit-identical across the adaptive initial,
intermediate, recovery and continuation requests. The delayed control was also
exact. Together with the exact layer-40 routed expert parts and combined MoE
output, this clears the sampled layer-40 residual and layer-41 read boundary.
The previously captured verifier MoE input first differs at layer 41, after
these values. Layer 41 is a GDN block (GDN ordinal 31); the next diagnostic
captures its raw pre/post recurrent state and intermediate tensors to find the
first changed operation. This is a correctness trace, not a performance result.

Reproduce the boundary analysis with:

```sh
python3 compare_boundary_sequence.py --run-dir .
```

Raw records are in each arm's `result/verify-boundary.bin`; parsed transitions
are in `boundary-sequence-analysis.json`.
