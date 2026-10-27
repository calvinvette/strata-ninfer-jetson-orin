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
