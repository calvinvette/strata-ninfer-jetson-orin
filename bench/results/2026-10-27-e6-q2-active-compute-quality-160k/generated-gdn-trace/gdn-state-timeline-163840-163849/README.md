# E6 layer-8 committed-state timeline

## Outcome

A paired 160K Q2_0 retrieval run captured only layer 8's committed state for
accepted positions 163,840 through 163,849. Both arms returned the exact
expected answer in 47 generated tokens, with identical token IDs and expert
residency. The final persistent-state check still differed in `gdn`, `tail`,
`pooled`, `pooled_full`, and `kv`; this is not a state-parity qualification.

The layer-8 recurrent state was bitwise equal between Strata and strict NInfer
at positions 163,840 through 163,846. The first observed split was position
163,847: 118,285/786,432 recurrent floats differed, but relative L2 was only
`1.37e-8` and maximum absolute delta `1.49e-8`. At positions 163,848 and
163,849, recurrent-state relative L2 remained `1.41e-8` and `1.33e-8`. The
30,720-float convolution state was bitwise equal at every captured position.

This changes the interpretation of the prior broad diagnostic. That run found
the position-163,848 recurrent states already differed by relative L2
`2.64e-4`; the reduced state-only capture instead finds only `1.41e-8` at the
same position. Other captures have also moved the first split between layers
1, 7, and 8. Together these results show substantial instrumentation/run
history sensitivity. The current pair locates a tiny first layer-8 recurrent
state difference at generated position 163,847, but cannot establish that this
is the stable onset or explain later final-state divergence. The convolution
state is not the source in the sampled interval.

The 3,053-sample supervisor run lasted 53.88 minutes. Minimum available memory
was 6.87 GiB, peak swap 4.50 GiB, and sampled cgroup OOM-kill counters were
zero. Clocks were read without control; energy was not measured.

## Reproduction and artifacts

The run used the E6 Q2_0 config/workload and Release CUDA binary SHA256
`fbd40926be198adc92de9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`.
State comparison was computed from the ten local `STGCMT1` records. Raw state,
logs, result JSON and supervisor telemetry remain local-only. E6 remains open;
this is a correctness diagnostic, not performance evidence.
