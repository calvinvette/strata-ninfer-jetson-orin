# Initial numerical contract preparation

Prepared during Phase 1 controls, before any candidate kernel timing. This is a
contract for a selected correctness diagnostic, not a promoted NInfer kernel or
completed Phase 2 gate. Parent source revisions remain Strata `0be090c` and
NInfer `b07248f2`.

## First operator: weighted RMS normalization

Strata symbol: `native_gr_rms_norm_weighted_multi` in
`src/kernels/cuda/native_gr_norm.cu`. For contiguous F32 input
`[tokens, groups, columns]` and gamma `[groups, columns]`, each row independently
computes `x * rsqrt(mean(x*x) + epsilon) * gamma`. Gamma repeats across tokens,
not across groups. Input, gamma and output are caller-owned, aligned and
nonoverlapping. Positive dimensions and finite nonnegative epsilon are required;
zero epsilon also requires a nonzero row. Inputs and intermediate sums must be
finite. The operator enqueues on the caller's stream without allocating or
synchronizing; no persistent state changes. It uses 256 threads for columns
below 1024 and 1024 threads otherwise.

NInfer symbol: `ninfer::ops::rmsnorm` in `include/ninfer/ops/rmsnorm.h`. Its ideal
formula is similar, but input, gamma and output are BF16, one gamma vector is
shared across rows, epsilon is strictly positive, and `unit_offset` can add one
to gamma. Its BF16 rounding criterion cannot qualify Strata's F32 output. Reuse
the mathematical-contract and independent-oracle method; adapting its kernel
would require an explicit represented-type, gamma-broadcast and offset contract.
No implicit BF16 conversion is admitted.

The independent diagnostic computes squares, sums, square roots and products
naively in FP64 from the represented F32 inputs. It does not reproduce CUDA's
XOR reduction or `rsqrtf`. Predeclared criterion, before inspecting results:

- Relative L2 error at most `1e-5` (zero oracle norm uses absolute error).
- Maximum absolute error at most `1e-6 + 1e-5 * max(abs(oracle))`.
- All results finite; input/gamma unchanged and output guard bytes unchanged.
- Invalid dimensions, epsilon, alignment and null pointers fail before launch.

For the selected 128/2560/10240-column shapes, the 256/1024-thread schedule
performs bounded per-thread accumulation plus two short warp trees. The budget
covers approximately tens of FP32 rounding steps, reciprocal-root approximation
and final multiplies; it is deliberately tighter than BF16 storage rounding.
It is not a promise for arbitrary overflow-prone inputs, all future reduction
schedules or a whole-model logit tolerance. Changes to this criterion require a
recorded rationale independent of candidate timing.

Synthetic fixtures include actual column sizes 128, 2560 and 10240; dispatch
edges 1023/1024/1025; several groups with distinct gamma; token counts 1/2/64;
zero, near-zero and ordinary represented inputs; signed gamma; and nondefault
stream completion. No model tensors are committed as test fixtures.

## Projection formats

NInfer attention input projection's fixed contract uses BF16 activations with
5120 input columns, query/gate width 6144, key/value width 1024, and RowSplit
Q4G64_F16S/Q5G64_F16S weights. Strata's Coder artifact has 2560 hidden columns
and a mixed GGUF/native codec inventory. The pinned pack is distributed under
the IQ1_M filename, but the fresh header inventory finds routed expert tensors
in IQ2_S, IQ4_NL, IQ3_XXS, IQ3_S, Q2_0 and IQ4_XS; none has GGML type IQ1_M.
Dense source tensors additionally include Q6_K, BF16, F32, Q4_K and Q5_K.
The distribution label is not a per-tensor codec contract. These encodings are
not interchangeable with NInfer groupwise codes. Exact artifact tensor inventory
must precede any projection promotion, including conversion cost and independent
codec checks. A shared word such as Q4 or Q5 is insufficient.

## State seams to audit

The existing service FIFO/request status owns protocol lifecycle. `SessionState`
owns GDN recurrence/conv state, QSA KV/indexer state and PLE token/history state.
`Verifier` and its graph registrations own verification staging/capture;
the serve loop decides accepted lengths and token publication. `ExpertCache`,
`DeviceArena` and platform memory checks own their physical allocations. These
are an initial map to source, not proof of accepted-prefix transactions or
unique allocation accounting. Phase 2 must validate exact ownership and seams
without creating a second mutable scheduler or physical ledger.

## Executed diagnostic, 2026-10-09

The selected existing Strata operator passes 25 numerical cases and eight invalid
argument cases on Orin SM87: maximum relative L2 `6.953762979552452e-8`, maximum
absolute error `9.905367370777185e-7`, with unchanged inputs/gamma and guards.
See [raw results](../../bench/results/2026-10-09-paired-api-controls/weighted-rms-oracle/stdout.txt)
and [diagnostic identities](../../bench/results/2026-10-09-paired-api-controls/evidence/diagnostic-identities.json).
No NInfer kernel is copied or timed. Overlap/nonzero-row assumptions remain caller
preconditions; the invalid-case suite is not exhaustive validation of every
pointer or legal dimension. This tolerance does not qualify the open whole-model
logit discrepancy or accepted-prefix state.

## Existing state API audit, 2026-10-09

`Verifier::commit` rejects `n_keep < 1` and `n_keep > last_t_` before launching.
A one-token window can self-commit during recording; wider windows use a commit
graph. Host PLE history advances after commit, and an asynchronous commit needs
`wait_commit` before state inspection. NInfer's zero-length transaction cannot
be mapped blindly to `Verifier::commit(0)`. The zero-retained/publication test must establish
the caller's no-publication/rollback semantics and directly inspect persistent
state; simply accepting a rejected API call is insufficient.

The existing `conversation_snapshot_test` freshly passes 3901 checks on native
Orin CUDA. It uses independent byte patterns for snapshot save/restore, refusal
preservation, several KV formats/modes and ring reconstruction. The GDN recurrence
kernel parity test now checks every recurrence commit prefix 0..T for windows
T=1..8 against fresh single-token replay (84 cases), plus all 44 convolution-history
prefixes against independent host selection. The native run passes both suites
bitwise, and the same test source compiles under the maestro1 HIP toolchain. These
are kernel-level checks. A separate post-fix model-level spec1/spec4 comparison
now verifies token and persistent-state parity for the observed output-clipping
case; cancellation, recovery and other prefix cases remain untested.
[Snapshot raw result](../../bench/results/2026-10-09-verifier-owner-trace/conversation-snapshot-native/stdout.txt);
[GDN prefix evidence](../../bench/results/2026-10-09-gdn-prefix-kernel/).


## Accepted drafts, retained state and publication

Pinned NInfer's `docs/maintainer/replayssm-gdn.md` and
`src/core/gdn_replay_records.h` distinguish these lengths. D drafts produce
T=D+1 verifier inputs: the pending anchor followed by drafts. A accepted drafts
license P=A+1 outputs, ending in a correction or bonus token. The input prefix
advanced is the old anchor plus A drafts; the last output becomes the next
pending anchor. Publication can retain M<=P after EOS/output-budget clipping.
NInfer's replay transaction commits the retained prefix M.

Strata's original serve, pipeline and CLI loops called `commit(a+1)`. Zero
accepted drafts therefore request commit(1), not commit(0). Clipping, pending
anchors and persistent state must be audited at the publication boundary before
adapting transaction tests. The broader transaction gate includes direct state
comparison for retained lengths, including zero, rejected-suffix isolation,
cancellation/recovery and long chains; final text and a `commit(0)` rejection
cannot prove those cases. They remain Phase 5 work. At the source-audit stage, no
semantic bug or adapter equivalence was concluded from that map; the direct
model check below later found a clipping mismatch.

The first direct spec-1/spec-4 model check exposed a concrete clipping mismatch:
both arms emitted identical 32-token IDs, while MTP accepted 23/27 drafts and
the final persistent-state fingerprints differed (state length 1493 vs 1494;
GDN, PLE, indexer, KV and PLE-history also differed). In the observed final
window, the verifier match exceeded the request's remaining output budget, but
the old service, CLI and pipeline paths committed `a+1` before publishing the
shorter output. The worktree now commits only the published prefix in these
paths and uses that prefix for consumed-token history and pipeline rollback.
The shared host-side prefix selector has eleven no-GPU cases for zero accepted
drafts (one retained correction output), intermediate and full accepted
prefixes, output-budget clipping, EOS handling and empty boundaries. Its
zero-output-budget case checks the selector result only; it does not exercise a
zero-length `Verifier` transaction, which Strata rejects and the active decode
loops do not issue. The supervised post-fix Orin rerun emitted identical token
IDs and matched all nine captured persistent-state fields for this case. Raw
data and its bounded scope are in the [state comparison report](../../bench/results/2026-10-09-accepted-prefix-publication/README.md).
An additional 8-token run matched IDs and state length but differed in
`pooled_full`, the in-progress spare indexer row; automatic and fixed cache
configurations reproduced it. This unresolved state case is tracked for Phase 5
in the [short-prefix follow-up](../../bench/results/2026-10-09-short-prefix-state-followup/README.md).

## Independent IQ4_NL codec diagnostic contract

Before inspecting diagnostic results, the criterion is exact F32 bits and exact
round-to-nearest-even BF16 bits for finite FP16 scales. An IQ4_NL block contains
18 bytes: little-endian FP16 scale followed by 16 packed bytes. Low nibbles map
to elements 0–15; high nibbles map to 16–31. Each code indexes the pinned ggml
16-entry nonlinear table; no linear zero-point reinterpretation is allowed.
The table is format data, independently stated in the fixture, rather than
imported from either production decoder. The source definition is pinned ggml
`3cf03257` `ggml-common.h`/`ggml-quants.c` (MIT, existing attribution retained).

The independent oracle interprets the half significand/exponent with FP64
`ldexp`, multiplies by integer code values and selects the nearest BF16 number
by adjacent-value distance with even-code tie breaking. It does not call the
production half conversion or BF16 bit-rounding helper. A finite half times a
seven-bit integer fits exactly in F32; thus exact bits, including signed zero,
are justified rather than a tolerance chosen after observing results.

The standalone test covers all 63,488 finite half bit patterns and all 16 codes
in both halves, row slicing with nonzero row0, multiple rows, 32/256/288-element
launch edges, 640/2560/10240-column shapes, and a full synthetic 2560x640
routed-expert down matrix matching the artifact inventory. It checks scalar CPU decode
and existing CUDA F32/BF16 decode, packed-input preservation, output guards and
completion on a nondefault stream. Nonfinite scales, invalid shapes, FP16 output,
real artifact payloads, other codecs and NInfer RowSplit conversion are excluded.
No production source, default or codec is changed by this private diagnostic.


Executed on Orin SM87: all 14 IQ4_NL diagnostic cases pass, 3,726,080 exact values
per CPU/F32/BF16 route. Input and guard checks pass. [Raw evidence and identities](../../bench/results/2026-10-09-iq4-nl-codec-contract/README.md)
retain the initial missing-link-dependency failure and corrected explicit pinned
build. No other codec, real model tensor or cross-engine conversion is qualified.


## Checked projection seam map

The [per-layer contract report](../../bench/results/2026-10-09-projection-contract-map/README.md)
records 36 GDN and 12 QSA layers / 108 source projections. None supports direct
reuse of the pinned two-parent NInfer profile. Besides hidden width and codecs,
GDN stores QKV and gate/Z in different parents; QSA stores query/gate interleaved
by head and has 512 K/V rows instead of the profile's 1024. Each dimension,
format and arrangement reason is retained by symbol. This is not a converter,
all-profile impossibility proof or runtime plane qualification.

## Q6_K materialization contract, declared before diagnostic execution

The existing Q6_K scalar and CUDA F32/BF16/FP16 decoders are the next diagnostic,
selected from the pinned request profile's materialization cost. A block has
256 values in210 bytes: low fields128 bytes, high fields64, signed int8 subscales16,
and little-endian FP16 global scale at208. Each consecutive16-value group shares
a subscale; ideal value is `global_scale * subscale[group] * signed_quant` with
signed quants−32..31. Logical fixtures are independently encoded into the
mandated field locations; expected values use the retained logical arrays,
never a production decoder or a second transcription of its unpack loops.

The criterion is exact represented F32 bits and nearest-even BF16/FP16 bits,
plus unchanged packed input and output guards. A finite half significand has
11 bits; a127 subscale has7 and a31 quant has5, so products need at most23
significant bits and fit exactly in F32. Power-of-two extrema−128/−32 change
exponents without increasing that bound. Half conversion is checked by adjacent
represented-value distance, including the IEEE65520 overflow threshold. Some
synthetic scales deliberately overflow FP16; matching signed infinity is then
required, not classified as model-quality qualification. Nonfinite input scales
are excluded. BF16/F32 remain finite for all admitted fixture values.

Coverage is all63,488 finite half bit patterns with signed subscale edges, all256
signed subscale values × all64 quant codes in a separate fixture, rows1/3 with
row0=2, columns256/512/768/2560/6144/10240, and a full synthetic10240×2560 GDN
matrix with row0=1. Tests use a nondefault stream and explicit completion.
Packing/rounding known-value anchors precede execution. Other codecs, real
model payloads, invalid shapes, NInfer conversion, speed and persistent state
remain outside this diagnostic. The original test arithmetic is shared with
IQ4_NL through a private test header, not through production codec helpers.



Executed Q6_K diagnostic: CPU, CUDA F32, BF16 and FP16 match exact expected bits
on42,565,632 values in15 cases. Full GDN QKV shape coverage uses synthetic data;
finite-scale exhaustion includes synthetic FP16 overflow. [Commands, per-case
output and identities](../../bench/results/2026-10-09-q6-k-codec-contract/README.md)
retain scope. This does not qualify real tensor payloads or mixed-precision
model quality.
