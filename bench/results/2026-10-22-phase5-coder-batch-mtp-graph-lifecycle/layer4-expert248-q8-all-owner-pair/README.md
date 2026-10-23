# Expert 248 owner transition and Q8_1 selector diagnostic

This experiment follows the position-68 layer-4 owner transition in the
[two-live profile capture](../layer4-profile-e11-first-positions68-71/README.md).
It asks whether the native CPU Q8_1 dot path changes the result when the same
activation is evaluated by the CPU and CUDA expert implementations, and checks
the same narrow point in a second two-live service capture.

## Independent operator oracle

Using the captured default-selector prompt-1 activation, the independent
`native_expert_parity` oracle evaluated layer 4 expert 248 from the same IQ1_M
Coder shard. The CPU and CUDA results differed in all 7,680 compared words,
with CPU/GPU relative L2 1.13e-2; the oracle reported zero failures against its
independent backend tolerances. Re-running that *same activation* with
`STRATA_NATIVE_CPU_Q8_1_DOT=all` made CPU and CUDA output bitwise equal (0 of
7,680 words differed), again with zero oracle failures. The first oracle run is
in [the default supervisor log](../supervisor-layer4-position68-expert248-oracle-default/stdout.txt);
the second is in [the Q8_1-all log](../supervisor-layer4-position68-expert248-oracle-q8-all/stdout.txt).

The default-selector service capture independently joins that expert result to
the two-live row: at position 68 prompt 1 has exact activation, route IDs and
weights, and expert 248 is the only rank whose owner differs (CPU in serial,
CUDA in batch). Its expert-248 part differs, while the shared contribution is
exact; the combined output differs in all 2,560 values, with relative L2
0.0028174 and maximum absolute difference 1.058e-4. Prompt 0's corresponding
position-68 batch part is not slot-tagged in the capture, so the analyzer leaves
that comparison unavailable.

## Two-live Q8_1-all service cell

The second capture used the same model, binary, expert profile, two prompts,
six-token limit, context, and cache configuration, with
`STRATA_NATIVE_CPU_Q8_1_DOT=all`. Both batch token streams match their serial
controls. Slot allocation is reversed in this run and is resolved from the
explicit position-71 rows; the position-68 row with omitted slot metadata is
joined by complement. For prompt 0 at position 68, expert 248 changes from CPU
to CUDA at rank 1 with exact activation, route IDs and weights. All ten expert
parts, the shared output and combined output are bitwise exact. Prompt 1's
position-68 row has no slot-tagged batch parts and is not assigned a part
comparison.

Committed GDN state is exact for prompt 0 at position 68 and prompt 1 at both
positions. Prompt 0 first differs at position 71, model layer 30: 619,151 of
817,152 values differ, but absolute L2 is 1.1445e-6, maximum absolute error is
1.267e-7, and relative L2 is 5.84e-9. This is near-bitwise numerical
agreement, not exact state parity. The supervisor recorded 18.61 GB minimum
physical/admission availability across 143 samples and zero cgroup low/high/max/
OOM/OOM-kill events. The run took 147.53 seconds and is a correctness
diagnostic, not a performance measurement.

## Limits and reproduction artifacts

These are two individual two-live sequences, not repeated paired trials. The
selector changes earlier CPU arithmetic and therefore the expert routes and
activation history between cells; the default and Q8_1-all service captures do
not constitute a controlled whole-model intervention on an identical history.
The same-input isolated oracle does provide a controlled operator comparison.
No end-to-end quality, general multi-live correctness, or performance claim
follows. The Q8_1 selector remains opt-in.

The compact JSON files preserve route/slot joins, per-position state deltas,
owner changes and all qualified output comparisons. Full service arrays,
telemetry, oracle arrays and supervisor traces remain in local sibling capture
directories and `/tmp`; they are not committed. Recreate the two compact
analyses with `analyze_layer4_profile_capture.py` and the profile-generation
and capture commands in the linked report, adding `--q8-1-selector all` when
analyzing the Q8_1-all cell.
