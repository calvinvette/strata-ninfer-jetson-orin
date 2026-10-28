# E6 reduced-capture GDN recurrence oracle

## Outcome

A same-workload 160K Q2_0 paired retrieval run captured layer 8's committed
state at position 163,848, GDN inputs and raw output at 163,849, and MoE bundles
for layers 7 and 8. Each arm returned the exact expected answer in 47 tokens;
token IDs and expert residency matched. Persistent `gdn`, `tail`, `pooled`,
`pooled_full`, and `kv` still differed, so the harness correctly marks this as a
state-parity failure rather than a qualification.

The independent FP64 recurrence oracle replayed position 163,849 using each
arm's own committed layer-8 state and captured `h`, `gate`, and `beta`. It
reproduced Strata raw `o` at relative L2 `1.11e-7` (maximum absolute error
`1.56e-7`) and NInfer at `7.99e-8` (`1.14e-7`). Both are consistent with
float32 rounding against this independent equation oracle; NInfer was slightly
closer in this single sample. This supports the recurrence implementation for
the captured inputs and state, but says nothing about whether the two incoming
states are correct or equivalent.

At position 163,848, the captured layer-8 recurrent states already differed in
783,877/786,432 values (relative L2 `2.64e-4`, maximum absolute `1.86e-4`); the
30,720-float convolution states matched exactly. At the next token, layer-8
GDN `x` differed by relative L2 `3.32e-7`, while `qkv`, convolution output
`h`, and `z` were exact. Small gate/beta differences (`2.62e-7` and
`1.03e-7`) preceded `y` at `5.18e-4` and projected GDN output at `2.08e-3`.
The subsequent MoE input differed by `6.33e-4`.

Routes matched at layers 7 and 8. In this run layer-7 bundle inputs were not
bitwise equal, unlike the prior capture, but layer-7 expert parts retained the
same tiny relative difference (`3.55e-8`). Layer-8 expert parts, shared output,
and combined output differed by relative L2 `0.00748`, `0.01314`, and
`0.00793`. This changing layer-7 input and state trajectory reinforces that
the onset depends on run/capture history. The oracle shows the recurrence
formula itself accounts for each arm's raw output; it does not explain how the
committed states diverged earlier in the sequence.

The 3,051-sample supervisor run lasted 53.86 minutes. Minimum available memory
was 7.14 GiB, peak swap 6.58 GiB, and sampled cgroup OOM-kill counters were
zero. Clocks were observed without control and energy was not measured.

## Reproduction and artifacts

The run used the parent E6 Q2_0 config/workload and Release CUDA executable
SHA256 `fbd40926be198adc92de9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`.
Both `gdn_trace_oracle.py` replays passed. Raw captures, oracle outputs and
supervisor telemetry remain local-only. This is correctness diagnosis only;
E6 and end-to-end state qualification remain open.
