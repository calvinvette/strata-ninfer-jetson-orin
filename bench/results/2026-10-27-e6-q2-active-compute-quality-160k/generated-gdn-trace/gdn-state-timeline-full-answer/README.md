# E6 full-answer layer-8 state timeline

## Outcome

A paired 160K Q2_0 retrieval run captured only layer 8's committed state over
the generated answer. It recorded states at positions 163,840 through 163,885
(the final generated token is produced from the last committed input and has no
subsequent state update). Both arms returned the exact expected answer in 47
generated tokens, with identical token IDs and expert residency. Final
persistent `gdn`, `tail`, `pooled`, `pooled_full`, and `kv` still differed.

Layer 8 recurrent and convolution states matched bitwise at positions 163,840
and 163,841. At 163,842, both first differed: recurrent state had relative L2
`2.30e-4` (785,909/786,432 values; max absolute `1.96e-4`) and convolution
state had relative L2 `9.10e-4` (10,240/30,720 values). The recurrent-state
relative L2 peaked at `3.81e-3` at position 163,869; it was `2.36e-3` at the
last captured state, position 163,885. Convolution-state relative L2 peaked at
`1.42e-2` at 163,869 and was `6.82e-3` at 163,885.

This onset conflicts with the preceding reduced state-only timeline: that run
matched through 163,846 and first split at 163,847 by only `1.37e-8`. An earlier
multi-sidecar run also found much larger state differences at 163,848. The
timelines establish strong run/capture sensitivity, not a stable first split.
Both recurrent and convolution components move in this full-answer capture, so
the next diagnostic should capture layer-8 inputs and pre/post state at the
first split observed here (163,842) and compare the update against the
independent GDN oracle.

The supervisor sampled 3,053 records over 54.04 minutes. Minimum available
memory was 6.54 GiB, peak swap 1.40 GiB, and sampled cgroup OOM kills were zero.
Clocks were observed without control and energy was not measured.

## Reproduction and artifacts

The run used the E6 Q2_0 config/workload and Release CUDA binary SHA256
`fbd40926be198adc92de9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`.
Comparison covers 46 accepted input positions, 163,840–163,885. Raw state
captures, result JSON and supervisor telemetry remain local-only. This is a
correctness diagnostic, not performance or release qualification.
