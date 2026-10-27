# 160K GDN state divergence localization

Date: 2026-10-27 (Orin AGX). Source: `0295db1e` (source unchanged); binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`. This diagnostic repeats the 163,840-token Q2_0 held-out task at accepted prefix length 163,886, with final GDN arrays captured from both staged grouped-compute backends.

Follow-up raw-output trace used source commit `edb4d9fc` and binary SHA-256
`f40e30a1a20d3d27e72b81fd9394295d47bee0b5824b767d433dc493e7b8615e`. It
captures the pre-normalization GDN `o` vector alongside normalized `y` for
layer 2 at generated positions 163840–163885. The same held-out task returned
the exact answer and matching token IDs and residency, but again failed final
state parity in `gdn`, `tail`, `pooled`, `pooled_full` and `kv`. This sequential
run took 53.96 minutes; minimum sampled available memory was 7.20 GiB against
the 6-GiB floor and peak swap was 5.98 GiB. It is diagnostic evidence, not a
performance result.

| GDN state layer | Relative L2 (Strata vs NInfer) | Reading |
|---:|---:|---|
| 0 | 0 | Bitwise equal |
| 1 | 6.87e-10 | First tiny numeric delta |
| 2 | 3.41e-06 | Delta grows |
| 3 | 0.00441 | Strong amplification |
| 4 | 0.00414 | Remains material |
| All 36 layers | 3.5981% | 94.65% of 29,417,472 floats differ |

The answer, all 47 generated token IDs and resident map match, but the request fails final-state parity. Layer 0 GDN is exact, layer 1 first differs at very small magnitude, and the state delta grows markedly by layers 2–3. This localizes where the final state divergence becomes visible; it does not identify the operation that first caused it, establish which backend is correct, or prove the tiny layer-1 delta causes later state drift. Other final state fields (tail, pooled, pooled-full and KV) also differ.

The GDN dump run completed with checker failure as expected. Minimum sampled available RAM was 6.47 GiB and peak swap was 5.63 GiB; the six-GiB floor remained satisfied and OOM counters were zero. The run is not performance evidence. Full arrays and comparator output are retained locally under `gdn-dump-exacttarget/`; the 226 MiB binary dumps are deliberately not committed. Summary metrics are in `gdn-dump-exacttarget/gdn-summary.json`.

## Generated-token trace

A paired follow-up captured layer-2 GDN intermediates for generated positions
163840–163885 (46 records; terminal position 163886 had no regular GDN
intermediate record). Both arms still returned the exact answer, identical 47
token IDs and the same resident map; final state differed in the same five
fields. Minimum sampled available memory was 6.70 GiB, above the 6-GiB floor;
peak swap was about 4.7 GiB. This diagnostic is not performance evidence.

At the first generated position (163840), inputs and all captured intermediates
except `y` were bitwise equal. The `y` arrays differed in 579/6,144 values,
with max absolute delta `5.96e-8` and relative L2 `2.50e-8`; `gdn_out` and the
captured FFN values were still exact. First observed differences in other
segments appeared at position 163849 (`x`, `gate`, `beta`, `ffn_x`, `ffn_y`),
then at 163877 (`qkv`, `h`, `z`, `gdn_out`), where `x` relative L2 was
`6.88e-4` and `gdn_out` relative L2 was `4.68e-3`. At position 163885,
`gdn_out` relative L2 was `9.59e-4` and `ffn_y` relative L2 was `3.86e-3`.
The full compact per-position metrics are in
[`generated-token-trace-summary.json`](generated-gdn-trace/generated-token-trace-summary.json);
raw diagnostic arrays remain local.

The raw `o` trace shows a first difference at position 163840: 1,486/6,144
values differ, max absolute delta `1.49e-8`, relative L2 `3.13e-8`; `y` at the
same position differs in 1,283 values, max absolute delta `5.96e-8`, relative
L2 `3.31e-8`. Both relative L2 values remain below `9e-8` through position
163876. At position 163877, both jump together: `o` relative L2 `5.11e-4` and
`y` relative L2 `1.41e-3`, with 6,141/6,144 values differing in each. The
maximum in this captured window occurs at 163877; both differences shrink at
later positions. This shows normalization is not the first observed source:
the recurrence output already has a tiny arithmetic discrepancy at the first
generated token, followed by a much larger event at the same position as the
previously observed `qkv`, `h`, `z` and `gdn_out` differences. It does not
identify the originating operation or establish which backend is correct.

An independent FP64 replay of the captured recurrence inputs, initialized from
the separately captured bitwise-equal layer-2 prompt-boundary state, matches
captured raw `o` across all 46 generated positions with worst relative L2
`3.52e-7` for Strata and `3.58e-7` for NInfer. At position 163877, where raw
`o` differs by `5.11e-4` between backends, the captured recurrence inputs have
already split substantially: 10,233/10,240 `h` values differ, and all 48 gate
and beta values differ. The first input differences in this trace appear at
position 163844 (`x`: 2,047/2,560 values, gate: 10/48, beta: 15/48). This
places the large raw-output split downstream of a changed layer-2 input, not in
the recurrence equation itself. The FP64 replay uses a separately captured
prompt-boundary state rather than a state snapshot from the exact raw-`o` run,
so it does not prove same-run trajectory equivalence or locate which earlier
model-layer operation first changed the activation.

## Same-run boundary and fused read follow-up

A same-run paired trace captured committed layer-2 GDN state at accepted
positions 163839, 163840, 163844, 163877 and 163886, plus the model-layer-1
boundary at generated position 163844. The previous separate-run claim that
layer-2 state was bitwise equal at the prompt boundary does not hold for this
same-run pair: at accepted position 163839, 109,395/786,432 state values differ
(relative L2 `1.701e-8`). The delta remains small at position 163844
(`1.923e-8`) and rises to `2.114e-4` at 163877. At the captured layer-1 / next
layer-2 boundary at 163844, all eight compared fields are bitwise equal across
the arms. The first same-run layer-2 GDN input deltas are already visible at
163844: `x` differs in 2,047/2,560 values, gate in 10/48 and beta in 15/48.
This places the first observed change between the captured equal boundary and
GDN input, but the capture so far does not include each fused read output.

An opt-in capture for the fused grouped-residual read was validated on the
2,048-token held-out control. Its `xn`, `lo`, `rs`, `inj_out` and `mixed`
payloads were all bitwise equal for model layer 2 at position 2048; final state
also matched. The control took 181.6 seconds and minimum available RAM was
12.40 GiB. A same-run 160K capture at layer 2 / position 163844 then found all
five read outputs bitwise equal (`xn`, `lo`, `rs`, `inj_out`, `mixed`), even
though the paired request still returned exact answer, token IDs and residency
with the same five persistent-state fields different. It took 53.97 minutes;
minimum available RAM was 7.09 GiB, peak swap 6.36 GiB and OOM counters were
zero. The run ended on the expected checker failure, not the memory guard.

This exact read capture does not reproduce the GDN `x` difference seen at
163844 in the other same-run trace. The fused read writes `mixed_`, which the
GDN diagnostic copies directly as `x`; however, that `x` was not captured in
this read-capture pair, so the two observations should not be treated as a
simultaneous stage-to-stage proof. They indicate run-to-run variation in the
observed onset or an instrumentation-sensitive path. Next capture both fused
read outputs and GDN intermediates at position 163844 in the same pair. The
short-control capture and comparator are diagnostic only and opt-in.

The diagnostic's default-path control, with raw capture disabled, passed the
same 2,048-token held-out task: exact answer, token IDs, residency and all nine
final state fields matched. Minimum available memory was 11.55 GiB; sequential
elapsed time was 182.2 seconds. This validates the ordinary no-capture path at
this short context only. The opt-in trace and short control metrics are
summarized in
[`gdn-o-trace-summary.json`](generated-gdn-trace/gdn-o-trace-summary.json);
raw arrays remain local. Keep the memory guard in place and do not infer
equivalence from final text.

The existing Orin operator checks also passed during this follow-up. The
independent `gdn_parity --selftest` measured recurrence-output relative L2
`2.032e-7` and state relative L2 `3.978e-8` against its FP64 reference; its
convolution, normalization, layout and fused multi-token cases passed. The
separate `gdn_rec_parity` reported bitwise-equal recurrence variants for the
tested lengths 1–4099. These synthetic checks validate bounded operator
contracts. The focused trace replay adds captured-input numerical evidence,
with the separate-state limitation above; it still does not identify the
earlier model-layer operation.

## All-generated-position GR-read v2 capture

A paired 160K run on source `655a6755` (binary SHA-256
`d3bbd6194d8cf48101c150627873b7fa2b6002e07aab9fa5228b6c498c086feb`)
recorded concatenated STGRRD2 rows plus GDN `x` at layer 2 for every generated
position where a regular verifier row was produced: 163840–163885 (46 rows).
The request generated 47 tokens and stopped at the requested terminal position
163886, which has no regular capture row.

The first nine rows, 163840–163848, are bitwise equal across backends. At
163849 raw residual `R` is the first differing GR-read field: 58/2,560 values
differ, relative L2 `3.719e-9`, maximum absolute delta `2.328e-10`. The same
position has 301/10,240 `xn` values differing (relative L2 `1.381e-8`) and
644/2,560 `mixed` values differing (relative L2 `5.269e-8`). This shows the
first observed mismatch precedes normalization and is already present in the
layer-2 residual input. The earliest differing rows after that are 163854 and
163875; all fields return to exact equality between those positions.

At 163877, the divergence becomes large: `R` differs in 2,558/2,560 values
(relative L2 `3.704e-5`), `xn` in 10,226/10,240 (`5.282e-4`), and `mixed` and
same-run GDN `x` in 2,559/2,560 (`6.880e-4`). At 163878 the relative-L2
difference in GDN `x` falls to `8.625e-8`. Across all 46 positions, each
backend's `mixed` equals its same-run GDN `x` bitwise. Cross-backend GDN `x`
differs only at 163849, 163854, 163875, 163877 and 163878.

A preceding selected-position pair reported bitwise-equal GDN `x` at 163877.
The current all-position run reproduces the large split there, but because the
capture density differs, run-to-run and instrumentation sensitivity remain
unresolved. Do not assign this variation to a specific runtime operation.
Both arms still produced the exact expected text, identical 47 token IDs and
the same resident map; final state differed in GDN, tail, pooled, pooled-full
and KV. This is a correctness failure and diagnostic trace, not performance
evidence. The checker exited 1 for final-state mismatch. The supervised pair
took 3,260.8 seconds; minimum available memory was 6.55 GiB, peak swap 1.76
GiB and sampled OOM counters were zero.

The compact comparison and task outputs are committed beside this note under
`generated-gdn-trace/gr-read-r-v2-all-generated/`. Large GR/GDN arrays and
supervisor telemetry remain local. Next capture the residual producer and
preceding layer boundary at all generated positions, then evaluate the first
`R` difference with an independent numerical oracle.

## Selected boundary repeat at the reported first split

A second supervised paired 160K run captured the layer-1 output and the
layer-2 boundary/read tensors at position 163849, token 12, where the
all-position run had first found a small raw-`R` split. In this pair, all eight
boundary fields matched bitwise: the layer-1 residual/MoE/injection outputs,
the next-layer residual/MoE/injection inputs, the post-read residual and `xn`.
All six GR-read v2 fields (`R`, `xn`, `lo`, `rs`, `inj_out`, `mixed`) also
matched bitwise. For each backend, same-run `mixed` equalled GDN `x` exactly.

The earlier 163849 `R` split and same-layer GDN `x` delta therefore do not
reproduce in this selected-boundary pair. The previous all-position capture
found those deltas in five positions, while an earlier selected-position pair
reported a small raw-`R` delta at 163849. These observations establish
run-to-run or capture-configuration sensitivity; they do not identify which
factor causes it. The current pair still returned the exact expected answer,
all 47 token IDs and the same resident map, but final GDN, tail, pooled,
pooled-full and KV state differed. The checker exited for that state mismatch.

The pair took 3,286.7 seconds; minimum available memory was 6.70 GiB, peak
swap was 0.86 GiB and sampled OOM counters were zero. This is diagnostic
evidence, not a performance result. Compact per-field evidence is in
[`boundary-comparison.json`](generated-gdn-trace/gr-read-r-v2-boundary-163849-retry2/run/boundary-comparison.json),
[`gr-gdn-comparison.json`](generated-gdn-trace/gr-read-r-v2-boundary-163849-retry2/run/gr-gdn-comparison.json)
and [`summary.json`](generated-gdn-trace/gr-read-r-v2-boundary-163849-retry2/summary.json).
To localize the persistent-state mismatch without assuming that 163849 is a
stable onset, capture boundary records across model layers at a fixed accepted
token and repeat with identical capture settings.

## Correction: fused residual-read capture is not valid yet

The fused-read equality claims recorded above are withdrawn. The earlier 2K
and 160K capture files contained only zero-filled pinned buffers because the
instrumentation marked them captured during allocation, before any D2H copies
were queued. They do not establish equality for `xn`, `lo`, `rs`, `inj_out` or
`mixed`. A later 2K trace selected the requested position-2048 row while
recording a one-token graph, but the request still failed the capture guard
and produced no qualified capture. The graph replay/flag lifecycle remains
unresolved; require a nonzero payload plus independent comparison before
using fused-read evidence.


## Qualified 2K fused-read capture (2026-10-27)

The earlier correction above remains applicable to the old zero-filled files.
The later selected-position failure was caused by two distinct control-flow
details: the fused-read helper's `false` return requests a separate Q8_1
quantization fallback, and the target one-token graph must be refreshed after
the current window inputs are staged. The diagnostic copies are now queued
before that fallback return, and only the selected target window rebuilds its
graph. A missing layer capture is reported as an error.

At layer 2 / position 2048, a paired Strata/NInfer trace produced 52,568-byte
files with valid `STGRRD1` headers and 13,128 nonzero floats per backend. All
five fields (`xn`, `lo`, `rs`, `inj_out`, `mixed`) matched bitwise. The
same-run layer-2 GDN `x` vector matched each backend's captured `mixed` vector
bitwise, and the two GDN `x` vectors matched each other. The full 48-token
retrieval check passed exact answer, token IDs and all persistent-state fields.
The compact comparison is
[`gr-read-gdn-debug-two-token-fixed/comparison.json`](generated-gdn-trace/gr-read-gdn-debug-two-token-fixed/comparison.json);
the full-answer run is in the adjacent
`gr-read-gdn-debug-full-answer/` folder. Comparator unit tests passed (3).
This qualifies the diagnostic at both 2K and the selected 160K position. The 160K task still ends with the previously observed five-field state divergence, so later generated positions need same-run localization.


## Same-run 160K capture (2026-10-27)

The repaired paired trace captured layer-2 fused-read state and GDN `x` at
position 163844, token 9269. Both backend GR-read payloads were fully nonzero
(13,128 floats) and bitwise equal across all five fields. On each backend,
`mixed` matched the same-run GDN `x` vector bitwise; the two GDN `x` vectors
also matched. Thus the earlier report of an `x` delta at 163844 came from a
separate run and is not reproduced by simultaneous capture. The held-out task
returned exact matching text and token IDs but still differed in final GDN,
tail, pooled, pooled-full and KV state. The supervised run took 3,238 seconds,
with 6.72 GiB minimum available memory, 6.05 GiB peak swap and no OOM events.
See [`comparison.json`](generated-gdn-trace/gr-read-gdn-fixed-same-run/comparison.json).
The subsequent paired trace at 163849 and 163877 is summarized below; it establishes the first observed small input divergence at 163849 in this same trajectory.


## Same-run multi-position trace (2026-10-27)

At layer 2 / position 163849 (token 12), the first differing fused-read field
was `xn`: 301/10,240 values differed, relative L2 `1.38e-8`, max absolute
`4.77e-7`. `lo` differed in 129/320 values (relative L2 `4.38e-8`),
`inj_out` in 2/4 (relative L2 `7.81e-8`), and `rs` was exact. The fused-read
`mixed` output matched each backend's same-run GDN `x` exactly. Cross-backend
GDN `x` differed in 644/2,560 values at 163849 (relative L2 `5.27e-8`, max
absolute `3.58e-7`). At 163877 (token 15), GDN `x` differed in 2,559/2,560
values (relative L2 `6.88e-4`, max absolute `1.30e-3`). This establishes the
first observed small difference at the fused-read input, five tokens after
the exact 163844 capture, and substantial growth by 163877. It does not yet
identify the upstream operation that changed `xn` or determine which result is
correct. The exact answer and token IDs matched, while final GDN, tail, pooled,
pooled-full and KV state did not. The supervised paired run took 3,285 seconds,
with 6.51 GiB minimum available memory, 2.07 GiB peak swap and zero observed
OOMs. See
[`comparison.json`](generated-gdn-trace/gr-read-gdn-multi-position-163849-877/comparison.json).


## Raw residual input capture added

GR-read diagnostic format v2 adds the raw residual `R` immediately before the
read and normalization, while retaining the v1 parser for earlier files. A
paired 2K control produced exact values for `R`, `xn`, all three read stages,
and GDN `x`; full output and persistent-state parity passed. At the 160K first
split (163849), comparing raw `R` to `xn` will show whether the small mismatch
is present before normalization or is introduced in that step. The short-run
comparison is
[`gr-read-r-v2-short-check/comparison.json`](generated-gdn-trace/gr-read-r-v2-short-check/comparison.json).
