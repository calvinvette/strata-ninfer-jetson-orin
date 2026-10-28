# E6 focused layer-8 update at position 163,842

## Outcome

A paired 160K Q2_0 retrieval run captured layer-8 GDN intermediates and
committed state immediately before/after accepted position 163,842. Both arms
returned the exact expected answer in 47 tokens with identical token IDs and
expert residency. Final `gdn`, `tail`, `pooled`, `pooled_full`, and `kv` state
still differed; this is not a state-parity qualification.

The layer-8 state immediately before the step (position 163,841) matched
bitwise, including recurrent and convolution portions. At the step input,
however, `x` already differed in 2,559/2,560 values (relative L2 `3.90e-4`, max
absolute `8.37e-4`). The GDN `qkv` projections differed by `1.58e-3`,
convolution output `h` by `1.02e-3`, `z` by `6.03e-4`, and gate/beta by
`4.88e-5`/`8.88e-5` relative L2. Raw recurrence output `o` differed by
`4.28e-4`; normalized `y` by `1.31e-3`; projected GDN output by `3.96e-3`.
The post-step recurrent and convolution states differed by `2.30e-4` and
`9.10e-4` relative L2, matching the first split in the full-answer timeline.

The independent FP64 recurrence oracle replayed each backend from the exact
shared pre-step state using its captured `h`, `gate`, and `beta`. It reproduced
raw `o` at relative L2 `9.84e-8` for Strata and `9.20e-8` for NInfer. Thus the
recurrence calculation is correct for each set of inputs; the material
difference is already present in layer 8's incoming activation `x` and its
projections. This shifts the investigation upstream of the layer-8 recurrence.
It does not identify the source of `x`'s difference, and other run settings have
shown different first-split positions and magnitudes.

The supervisor sampled 3,062 records over 54.04 minutes. Minimum available
memory was 6.56 GiB, peak swap 1.31 GiB, and sampled cgroup OOM-kill counters
were zero. Clocks were read without control; energy was not measured.

## Reproduction and artifacts

The run used the E6 Q2_0 model/config/workload and Release CUDA binary SHA256
`fbd40926be198adc92de9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`.
Both `gdn_trace_oracle.py` replays passed. Raw captures, oracle JSON, and
supervisor logs remain local-only. This is a correctness diagnostic only.
