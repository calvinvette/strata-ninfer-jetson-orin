# Position-521 layer-40 residual boundary — Orin — 2026-10-20

This supervised same-seed pair used the pinned Coder IQ1_M model, all eligible
layer-specific Q8_1 rules, prompt cache disabled, and the current candidate
binary. It captured all verifier MoE inputs and the residual/hyperconnection
boundary after layer 40, before layer 41's read, and immediately after that
read at generated position 521. Both arms passed; minimum host/admission
availability was 14.16 GiB adaptive and 14.26 GiB delayed, with zero cgroup
memory events.

Across adaptive initial-to-intermediate, all eight captured boundary fields
already differ after layer 40 and remain different before and after the next
read. The adaptive intermediate-to-recovery and recovery-to-continuation
boundaries are bit-identical. Every delayed-control transition is exact. The
CUDA-side verifier MoE input capture first differs at layer 40 at this
position; the separate position-521/522 layer-41 GDN capture finds exact raw
layer-41 pre-state but a changed `x` and post-state at position 521. Thus the
divergence is present at the layer-40 boundary before layer 41 processes the
token. The exact layer-40 operation is unresolved and is the next capture
target. This is a correctness trace, not a performance result.

Reproduce the parsed comparison with:

```sh
python3 compare_boundary_sequence.py --run-dir .
```

Raw captures are in each arm's `result/verify-boundary.bin`; the parsed
transitions are in `boundary-sequence-analysis.json`.
