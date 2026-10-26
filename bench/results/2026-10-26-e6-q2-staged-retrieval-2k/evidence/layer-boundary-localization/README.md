# CPU-miss versus staged layer-boundary localization

Date: 2026-10-26. Hardware: Jetson AGX Orin 32 GB, SM87, CUDA 12.6.
Model: Qwen3.8-Flash-Next GSQ RCO Q2_0. The exact 2,048-token held-out
retrieval prompt was run with CPU-miss (`--pcie-frac 0.0`) and strict NInfer
staged (`--pcie-frac 1.0`) routes. Each diagnostic process generated one token
after fresh prefill; captures were filtered to prompt position 2047, token 271.
Three supervised pairs captured GDN stages at layers 0 and 1, then per-expert
MoE parts at layer 0. Minimum available physical memory across the runs was
11.55–11.72 GiB. Read-only clocks were sampled; no clock controls were used.
Energy was not measured.

All three pairs produced token 19910 in both arms. Each retained the known
six-field final-state mismatch (`gdn`, `ple`, `tail`, `pooled`, `pooled_full`,
`kv`); the runner's nonzero status is that expected state-parity failure, not
a memory-floor or capture failure. Detailed numeric results are in
[`summary.json`](summary.json). Raw captures and supervisor logs remain local.

The first captured output difference is at model layer 0's MoE. The route IDs
and input activations match exactly. Seven of ten per-expert outputs are also
bit-identical. The three missed experts (90, 109 and 88) differ between CPU
fallback and staged GPU execution at about `9.5e-8`–`1.09e-7` relative L2;
maximum absolute deltas are at most `2.98e-8`. An independent Q2_0 × Q8_1
runtime-contract oracle matches both arms' output for these experts at
`5.4e-8`–`9.1e-8` relative L2. This is a small CPU/GPU arithmetic difference
within the sampled operator oracle, not evidence of an NInfer-only operator
error. The combined layer-0 FFN output differs at `2.43e-8` relative L2.

At layer 1, the hidden input differs by `7.04e-8` relative L2. QKV, the
convolution result, Z and projected GDN output are bit-identical; gate, beta
and recurrence output have only small differences. Its MoE input differs at
`1.03e-7` relative L2 and combined MoE output at `1.53e-7`. In a separate
Q8_1 comparison of sampled MoE inputs, layer 1's scales and codes match, while
layer 2 is the first sampled layer with changed codes (34 scales and 103 code
values). These observations place the first captured numerical difference in
CPU-versus-staged expert arithmetic at layer 0 and show how it reaches later
layers. They do not prove that this alone causes every persistent-state
mismatch or quantify its general effect on model quality.

The staged Strata-versus-NInfer control previously matched state exactly on
the same workload, so these results point to CPU-miss versus GPU execution as
the relevant boundary for this case. The failed three-pair staged-backend
performance screen remains unchanged: median decode-rate gain was 0.00%.

The retrieval checker now accepts `--capture-gdn-layer L --capture-gdn-position P`
to capture the existing verifier's GDN and feed-forward intermediate record
for one layer/position. Reproduce the captures with the commands recorded in
the matching `supervisor-layer-stage-*` and `supervisor-layer0-moe-capture`
`result.json` files. The same-activation operator checks used the captured
layer-0 activation, experts 90, 109 and 88, and the local qualified CUDA
binary. Python syntax/help checks and all three operator checks passed.

## Opt-in Q2_0 CPU arithmetic mirror trial

The CPU expert path already contains a CUDA-order Q2_0 × Q8_1 dot helper but
did not expose it for Q2_0 gate/up and Q2_0 down as a selector. An opt-in
`q2_0/q2_0` pair was added to `STRATA_NATIVE_CPU_Q8_1_DOT`; the default remains
GGML CPU arithmetic. Its selector-contract check passes. The standalone
`native_expert_parity` check on the exact layer-0 activation made experts 90,
109 and 88 bit-identical between CPU and GPU (0/7,680 output values differed
for each).

A CPU-only service trial restricted to model layer 0 returned the same one
output token as staged execution, but all six final state fields still
mismatched. It made the three targeted expert rows exact, while seven other
active rows that were bit-identical under the default owner split now differed
by about `9.6e-8`–`1.05e-7` relative L2. A second CPU-only trial selected the
mirror for all Q2_0/Q2_0 layers; it also retained all six state mismatches.
These results show the arithmetic helper is useful for isolating owner
rounding, but the broad format/layer selector affects other CPU-executed rows
and does not repair whole-request state. It is not a proposed default or a
qualified fix. No performance measurement was made. Compact values and memory
records are in `summary.json`; raw captures remain local.

## Expert-ID-filtered layer-0 mirror

The earlier layer-wide selector changed unrelated CPU rows. An opt-in
`STRATA_NATIVE_CPU_Q8_1_DOT_EXPERTS` filter now limits the mirror to listed
expert IDs within the selected pair/layer, and the retrieval checker exposes
this as `--cpu-q8-1-experts`. For the held-out 2,048-token prompt, the CPU arm
selected Q2_0/Q2_0 at layer 0 for IDs 83, 88, 90 and 109. At captured position
2047, IDs 90, 109 and 88 were routed; those three were the only rows changed
from the default CPU arm. The other seven routed expert rows were unchanged.
All ten targeted CPU rows and the combined layer-0 output matched the staged
GPU arm bit for bit.

The one-token service run kept matching residency maps and emitted the same
token ID. PLE state now matches; GDN, tail, pooled, pooled-full and KV state
still differ. The final GDN dump is exact at GDN state ordinal 0, differs only
at roughly `1e-9` relative L2 through ordinals 1–3, then first has a material
difference at ordinal 4 (`5.07e-6`); ordinal 5 reaches `0.00329`. For this
model, every fourth model layer is QSA, so GDN ordinal 4 maps to model layer 5.
Global relative L2 is
`0.03792`. The default CPU-miss/staged trace first had a material difference
at GDN state ordinal 2 (`9.94e-4`). This intervention therefore removes the sampled
layer-0 expert delta and delays material GDN divergence, but later state drift
remains. Minimum available/admission memory was 11.66 GiB, above the 6 GiB
floor. The one-token run does not assess answer quality or performance.

Compact values are in
[`q2-cpu-mirror-layer0-targeted-gdn/summary.json`](../q2-cpu-mirror-layer0-targeted-gdn/summary.json),
with per-layer state metrics and paired expert-row comparisons alongside it.
The 113 MiB per-arm state dumps and raw captures remain local.

### Layer-3 filtered-mirror follow-up

A second supervised one-token retrieval run kept the Q8_1 mirror filtered to
layer-0 experts 83, 88, 90 and 109, while capturing routed MoE rows at
position 2047 in layer 3. Route IDs matched. All ten layer-3 expert output
rows and the shared output were bit-identical; the layer input differed by
`7.89e-8` relative L2 and the combined layer output by `1.36e-7`. Token ID and
residency matched, while final GDN, tail, pooled, pooled-full and KV fingerprints
still differed. The state dump again first showed a material difference at GDN
state ordinal 4 (model layer 5; `5.07e-6` relative L2); the global difference
was `0.03792`. Minimum
available/admission memory was `11.65 GiB`. The run exited nonzero because the
state-parity check failed, not due to a runtime error. This sampled layer-3
capture does not identify which state operation amplifies the small incoming
difference. It is neither a quality nor a performance result.

Compact [layer-3 summary](../q2-cpu-mirror-layer3-targeted-gdn/summary.json),
[MoE comparison](../q2-cpu-mirror-layer3-targeted-gdn/moe-comparison.json) and
[GDN comparison](../q2-cpu-mirror-layer3-targeted-gdn/gdn-comparison.json) are
checked in. Raw captures and 113 MiB per-arm GDN dumps remain local.

### GDN state-history crossover at model layer 5

The next paired capture targeted model layers 4 and 5, then captured selected
accepted GDN states and intermediates at model layer 5. Model layer 4 is a GDN
block followed by an MoE. Its GDN `qkv`, convolution output `h`, `z`, and
projected `gdn_out` matched exactly at position 2047. Its two changed expert
rows (131 and 156) each differed by about `1.1e-7` relative L2; combined output
differed by `1.82e-7`.

At model layer 5 (GDN state ordinal 4), position 2047's input `x` differed by
`1.29e-7`; `qkv`, `h`, and `z` were exact, while gate/beta differed by
`1.53e-7`/`4.38e-8`. The normalized GDN output `y` differed by `1.69e-4`,
`gdn_out` by `1.95e-3`, and the layer's `ffn_y` by `7.89e-3`. The following
MoE saw a `6.70e-4` input difference and all ten expert rows changed. Those
expert-row changes are downstream of changed inputs and are not evidence of
different CPU/GPU arithmetic on matching inputs.

Committed state at model layer 5 was already different at captured position
2044 (`8.15e-4` whole-state relative L2), split between recurrent state
(`3.86e-4`) and convolution state (`8.15e-4`). At positions 2046 and 2047 the
convolution state was exact while recurrent state remained different
(`2.53e-4` and `2.25e-4` relative L2); whole-state differences were `6.29e-6`
and `5.07e-6`. The captured `h` differed at position 2045 (`1.98e-4`) and was
exact at 2046, consistent with the convolution buffer realigning after an
exact QKV update. A CUDA recurrence crossover replay started from the captured position
2044 state and replayed positions 2045–2046. Both route-matched replays
reproduced each captured committed recurrent state bitwise. Swapping the paired
GDN inputs changed recurrent state by `1.61e-4` and `9.99e-5`; swapping only
the initial recurrent state changed it by `2.71e-4` and `2.30e-4`. Gate-only
and beta-only effects were smaller (`1.85e-8`/`3.01e-8` at 2045 and
`1.90e-8`/`3.35e-8` at 2046). In this sampled window, the pre-existing
recurrent-state difference has the larger local effect. The replay covers the
recurrent component, not convolution-state updates. The earlier prompt
operation that created either state difference remains unidentified, and the
replay does not evaluate normalized output. Minimum available/admission memory was
`11.71 GiB`. The run is diagnostic only, with no quality or performance claim.

The replay helper now accepts a model-layer argument while preserving the
existing layer-1 invocation. The checked-in crossover can be reproduced with:

```bash
build/integration/e0-cuda-build/gdn_parity \
  --replay-crossover-model-layer 5 2044 2045 2046 \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/q2-cpu-mirror-layer5-history/cpu-miss.gdn-commit \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/q2-cpu-mirror-layer5-history/ninfer-staged.gdn-commit \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/q2-cpu-mirror-layer5-history/cpu-miss.layer5.gdn-diag \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/q2-cpu-mirror-layer5-history/ninfer-staged.layer5.gdn-diag
```
The tested Orin `gdn_parity` binary SHA256 was
`68242c05dc2567753177c7400a8fdfbc3361dc49c1af0a9ff820b5de9f613a8c`.

Compact [model-layer-4](../q2-cpu-mirror-layer4-targeted-gdn/summary.json),
[model-layer-5](../q2-cpu-mirror-layer5-targeted-gdn/summary.json) and
[state-history/replay](../q2-cpu-mirror-layer5-history/summary.json) summaries,
per-stage and expert-row metrics, committed-state comparisons and the crossover
JSON are checked in. Raw committed states, GDN intermediate captures and logs
remain local.

Reproduce on Orin with:

```bash
python3 tools/integration/run_control.py \
  --output bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/supervisor-q2-cpu-mirror-layer0-targeted-gdn \
  --timeout 600 --interval 1 --sample-clocks -- \
  python3 tools/integration/ninfer_q2_retrieval_check.py \
    --config bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/config.json \
    --engine build/integration/e0-cuda-build/strata \
    --workload bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/input/workload.json \
    --output bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/q2-cpu-mirror-layer0-targeted-gdn \
    --compare-cpu-miss-staged --max-new 1 --capture-moe-layer 0 \
    --capture-moe-position 2047 --dump-gdn \
    --cpu-q8-1-selector 'q2_0/q2_0@layer=0' \
    --cpu-q8-1-experts '83,88,90,109' --run
```

## Adjacent-position state-drift localization

Follow-up captures compared CPU-miss and strict NInfer at adjacent prompt
positions 2041–2047 using the same 2,048-token retrieval and one-token output.
The CUDA binary SHA256 was
`fccda8493f9f41e96f0ceabb905f4cb6301b5be00aab9a6e242b3b782a536f5e` from
source commit `44db548402b193202703256da81d75720312cc8d`. Every run emitted the
same token ID (`19910`) and matching token IDs, but final persistent state
still differed. These are single diagnostic runs, not timings. The
supervisor's minimum available memory was 11.49 GiB, above the 6 GiB floor.

At layer 0, the GDN stages through `gdn_out` were exact at captured positions
2043–2046. At positions 2043 and 2045, MoE inputs and route IDs were exact;
three and four of ten expert rows differed by about `1e-7` relative L2, with
combined output around `2.9e-8`. This reproduces a small, sparse CPU/GPU expert
rounding delta before the larger downstream differences.

At layer 1 positions 2043 and 2045, inputs differed by only `9.71e-8` and
`1.25e-7` relative L2; projected QKV and convolution output `h` were exact.
Small gate, beta and `y` differences were followed by GDN output differences
of `3.42e-5` and `1.31e-5`, then FFN output differences of `9.29e-4` and
`1.85e-3`. Routes still matched, but all ten expert rows differed after the
MoE input had moved by `2.29e-5` and `8.63e-6` relative L2. At layer 2 the
corresponding positions had GDN output differences of `4.64e-3` and
`4.74e-3`; some neighboring positions had exact QKV but still differed in
later convolution and recurrent outputs.

The selected committed-state capture for layer 1 remained close at the
positions emitted by the verifier (2042, 2044, 2046 and 2047): relative L2
ranged from `5.42e-10` to `1.10e-9`, with maximum absolute delta at most
`2.98e-8`. The capture path did not emit records for every requested position.
Together, these observations place the early sparse expert rounding delta at
layer 0 and the first sampled material output amplification in layer 1's
stateful GDN/FFN path. They do not establish which state update operation
causes it or whether either route is the intended numerical result. E6 state
and quality gates remain open.

Compact per-stage metrics, capture positions, binary identity and memory
records are in [`position-sweep-summary.json`](position-sweep-summary.json).
The compact [layer-0 GDN](../layer0-jump-capture/gdn-comparison.json) and
[MoE](../layer0-jump-capture/moe-comparison.json), [layer-1 GDN](../layer1-position-sweep/comparison.json),
[layer-1 MoE](../layer1-moe-jump-capture/comparison.json), [layer-2 GDN](../layer2-position-sweep/layer2-position-comparison.json),
and [committed-state](../gdn-state-step-sweep/comparison.json) summaries sit
beside the local raw captures. Raw arrays and engine logs remain local.
[`analyze_gdn_layer_capture.py`](../../analyze_gdn_layer_capture.py) regenerates
the checked-in GDN stage summaries from those raw captures;
[`analyze_ninfer_backend_capture.py`](../../../../../tools/integration/analyze_ninfer_backend_capture.py)
regenerates the MoE comparisons.

## CUDA recurrence crossover replay

To separate the starting-state difference from the layer-1 input difference,
`gdn_parity --replay-crossover` replays the actual CUDA
`gdn_step_norm_multi` kernel for positions 2043 and 2044. Each replay starts
from the captured committed state after position 2042 and uses the captured
`h`, gate, beta and `z` values. Swapping the start state and input sequence
creates four combinations. The two route-matched replays each reproduce their
captured committed recurrent state after position 2044 bit for bit. This
validates the capture pairing and the state recurrence replay for this sample.

With the CPU-miss start state held fixed, swapping to the staged inputs changes
the recurrent state by `4.35e-8` relative L2 after position 2044. With staged
inputs held fixed, swapping only the captured start state changes it by
`1.14e-8`. From the staged start state, the corresponding effects are
`4.33e-8` for input and `1.21e-8` for the start state. After position 2043,
the input effects are `4.13e-8`–`4.18e-8`, compared with `1.38e-8`–`1.58e-8`
for the start-state effects. In this two-token sample, the captured GDN inputs
therefore have roughly 2.6–3.8 times the local effect of the already-existing
state delta. The layer-1 QKV, convolution `h`, and `z` arrays match at these
positions; gate and beta contain the small observed deltas, so this crossover
principally attributes the state change to those gate/beta inputs.

The replay was extended to swap one field at a time from the CPU-miss inputs
while holding the CPU-miss starting state fixed. After position 2044, changing
gate alone gives `3.98e-8` relative L2; changing beta alone gives `2.27e-8`;
changing both gives `4.35e-8`. Gate is the larger isolated contributor in
this sample, and the two effects are not additive. The outputs and full
per-position difference counts are in the compact JSON.

A second window uses the captured state after position 2044 and inputs at
2045–2046. Both route-matched replays again reproduce their captured states
bit for bit. After position 2046, swapping the full two-position input sequence
changes state by `3.51e-8` relative L2, while swapping only the initial state
changes it by `4.22e-8`. Gate alone contributes `2.66e-8` and beta alone
`2.46e-8` in that window. Thus gate remains the larger isolated field effect,
but the pre-existing state delta is larger than the combined input effect in
this second sample. These adjacent windows show that local sensitivity depends
on the captured state and inputs; they do not support a general ranking of
input versus state effects. See
[`gdn-recurrence-crossover-window-2045-2046.json`](gdn-recurrence-crossover-window-2045-2046.json).
The replay utility now derives the route-match flag from measured state
differences and exits nonzero if either route fails bitwise reproduction.

This is a local perturbation result, not a numerical oracle for the full model:
the replay sets gamma to zero because only recurrent state is compared, and it
does not evaluate normalized GDN output. It does not explain why gate/beta
inputs differ upstream or establish either route as the correct result. The
existing `gdn_parity --selftest` also passed all 84 recurrence cases with zero
failures. Compact crossover values are in
[`gdn-recurrence-crossover.json`](gdn-recurrence-crossover.json); raw inputs and
state captures remain local.

The final `gdn_parity` source, including checked CUDA resource cleanup and
single-field swaps, passed the Orin CUDA build and the 84-case self-test. The
executable SHA-256 is recorded in `position-sweep-summary.json`. At source
commit `07ed49d7`, maestro1 rebuilt and linked the HIP target with two jobs.
This is x86 compile/link evidence only; maestro1 has no relevant
accelerator runtime. The configured SYCL `gdn_parity` target uses the separate,
unchanged `sycl/src/kernels/gdn_parity.cpp`, so it had no work for this
CUDA/HIP-only source change. The HIP executable SHA-256 is
`fa0ddc7b8fb1d712567593d0153c9748ea51926c513b83f4f3ba02574b48055e`.

Reproduce on the Orin with the matching captured raw files using:

```bash
cmake --build build/integration/e0-cuda-build --target gdn_parity --parallel 2
build/integration/e0-cuda-build/gdn_parity --selftest
build/integration/e0-cuda-build/gdn_parity --replay-crossover \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/gdn-state-step-sweep/cpu-miss.gdn-commit \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/gdn-state-step-sweep/ninfer-staged.gdn-commit \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer1-position-sweep/cpu-miss.layer1.gdn-diag \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer1-position-sweep/ninfer-staged.layer1.gdn-diag
build/integration/e0-cuda-build/gdn_parity --replay-crossover-window 2044 2045 2046 \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/gdn-state-step-sweep/cpu-miss.gdn-commit \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/gdn-state-step-sweep/ninfer-staged.gdn-commit \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer1-position-sweep/cpu-miss.layer1.gdn-diag \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer1-position-sweep/ninfer-staged.layer1.gdn-diag
```

## 2026-10-26 current-source layer-1 replay

To verify the early stateful amplification with captures from the same exact
pair, the corrected Orin binary repeated the 2,048-token CPU-miss versus strict
NInfer staged request with layer-1 GDN stage records at positions 2043–2047 and
committed state at positions 2042, 2044, 2046 and 2047. Source commit was
`03806747172378e9eb5a99a2a2194c655675b236`; the `strata` binary SHA256 was
`1b02fc2e34bfef1fd27e5e720163e4be746cc0998812eea7389e9ff4eadc6f6f`. Both
arms emitted token 19910 and the same residency map; final persistent state
still differed. The supervised request took 163.0 seconds, with 11.31 GiB
minimum available/admission memory. It is a diagnostic pair, not a timing or
quality result.

At layer 1, positions 2043 and 2045 had input relative-L2 differences of
`9.71e-8` and `1.25e-7`; QKV, convolution `h`, and `z` were exact. Gate and
beta differed at about `6e-8` relative L2. The GDN outputs then differed by
`3.42e-5` and `1.31e-5`, followed by FFN outputs at `9.29e-4` and `1.85e-3`.
At neighboring positions 2044, 2046 and 2047, GDN output was exact despite
similarly small input/gate/beta changes. The first two positions therefore
show a repeatable but position-dependent amplification through GDN/FFN.

CUDA recurrence crossover from the captured layer-1 start states reproduced
both arms bitwise at both windows. After positions 2043 and 2044, swapping the
captured GDN inputs changed recurrent state by `4.18e-8` and `4.35e-8` relative
L2; swapping only the starting state changed it by `1.38e-8` and `1.14e-8`.
Over positions 2045–2046, the corresponding input effects were `3.51e-8` and
`3.65e-8`, while start-state effects were `4.22e-8` and `4.29e-8`. This
confirms that both current input and accumulated state matter, with their
relative effects changing by window. It does not identify where the captured
gate/beta input deltas began, evaluate normalized GDN output, or establish
which backend is correct. Layer-1 committed state remained close (`9.44e-10`
global relative L2 across the four captured states), even though downstream
layers later diverge materially.

The 84-case `gdn_parity --selftest` passed with zero failures. The pair can be
reproduced on Orin with:

```bash
python3 tools/integration/run_control.py \
  --output /tmp/layer1-gdn-current-supervisor --timeout 600 --interval 1 --sample-clocks -- \
  python3 tools/integration/ninfer_q2_retrieval_check.py \
    --config bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/config.json \
    --engine build/integration/e0-cuda-build/strata \
    --workload bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/input/workload.json \
    --output /tmp/layer1-gdn-current --compare-cpu-miss-staged --max-new 1 \
    --capture-gdn-layer 1 --capture-gdn-positions 2043 2044 2045 2046 2047 \
    --capture-gdn-commit-layer 1 --capture-gdn-commit-positions 2042 2044 2046 2047 --run
build/integration/e0-cuda-build/gdn_parity --replay-crossover-model-layer 1 2042 2043 2044 \
  /tmp/layer1-gdn-current/cpu-miss.gdn-commit /tmp/layer1-gdn-current/ninfer-staged.gdn-commit \
  /tmp/layer1-gdn-current/cpu-miss.layer1.gdn-diag /tmp/layer1-gdn-current/ninfer-staged.layer1.gdn-diag
build/integration/e0-cuda-build/gdn_parity --replay-crossover-model-layer 1 2044 2045 2046 \
  /tmp/layer1-gdn-current/cpu-miss.gdn-commit /tmp/layer1-gdn-current/ninfer-staged.gdn-commit \
  /tmp/layer1-gdn-current/cpu-miss.layer1.gdn-diag /tmp/layer1-gdn-current/ninfer-staged.layer1.gdn-diag
```

The compact [paired summary](layer1-gdn-recurrence-current/run1/summary.json)
contains stage, commit-state, and crossover metrics. Raw diagnostic captures,
logs and supervisor telemetry remain local-only.

## Repeated layer-0 to layer-1 capture

Two further supervised pairs captured layer-0 MoE inputs, routes, expert rows
and combined output together with layer-1 GDN stages at positions 2043–2047.
The per-position comparisons were identical across both runs. Layer-0 inputs
and route IDs matched exactly; three or four of the ten expert rows differed
slightly, leaving combined-output relative-L2 deltas from `2.11e-8` to
`3.05e-8`. The next layer's GDN input differed by `5.48e-8` to `1.25e-7`.
QKV, convolution `h`, and `z` remained exact; gate/beta deltas were about
`3.3e-8` to `8.1e-8`. At positions 2043 and 2045, GDN output differences
grew to `3.42e-5` and `1.31e-5`, and FFN differences to `9.29e-4` and
`1.85e-3`. The neighboring positions had exact GDN outputs. Both pairs
returned the same generated token and residency map but failed final-state
parity. Minimum available/admission memory was 11.55–11.61 GiB; these are
localization runs, not performance or quality measurements.

Both initial runs also requested the layer-0 residual-boundary record at
position 2043, but neither arm wrote it. Follow-up telemetry showed that the
batch writer was not called. The request used the ordinary verifier's
multirow path, while boundary copying supported only single-row ordinary
windows and the distinct slot-batch path. That left the residual unmeasured in
those initial repeats. A multirow ordinary-verifier capture was then added and
validated in a fourth pair below. The earlier failed attempts remain part of
the record; raw files remain local-only.

### Capture-path telemetry follow-up

A third same-day pair added teardown telemetry; both arms reported
`copy_queued=1`, `multirow_graph=0`, `batch_writer=0`, and `target_seen=0`.
A fourth pair with the writer-position check moved ahead of its graph check
also reported `batch_writer=0`. The target therefore was not processed by the
slot-batch writer, which narrowed the failure to the ordinary verifier path.
The ordinary path had supported only one-row capture. Both pairs still failed
final persistent-state parity. Raw run3/run4 captures and logs remain
local-only.

### Multirow ordinary-verifier boundary capture

The opt-in boundary hook now captures multirow ordinary-verifier windows,
including row groups split across streams. A fifth paired 2K run emitted
matching-format records for layer 0 / position 2043 from both arms. The
independent comparator found the layer-0 input residual (`layer_output_rt`)
and injection (`layer_output_inj2`) bitwise equal. The MoE output differed in
729 / 2,560 values, with relative L2 `2.90e-8` and max absolute delta
`1.49e-8`. The next layer's pre-read residual differed with relative L2
`3.11e-8`; the post-read residual showed the same cross-arm difference. The
next-layer read activation differed in 2,495 / 10,240 values,
with relative L2 `6.19e-8` and max absolute delta `2.86e-6`. This directly
measures the intervening residual step: the first cross-arm difference is
already present in the layer-0 combined MoE output and is carried into the
next layer's read, with a small increase there.

The same run's MoE comparison found exact inputs, route IDs/weights, and shared
output for all five captured positions. Three or four routed expert rows per
position differed at about `8.75e-8`–`1.10e-7` relative L2; other routed rows
matched bitwise. The combined MoE output then differed by `2.11e-8`–
`3.05e-8`. This points to small owner/backend arithmetic differences in a
subset of expert rows, rather than routing or shared-expert output. The
compact [per-expert comparison](layer0-to-layer1-current/run5/moe-comparison.json)
contains each position and row's metrics; raw captures remain local.

The pair produced the same generated token and residency map but failed final
persistent-state parity in GDN, PLE, tail, pooled, pooled-full and KV fields.
Minimum available/admission memory was 11.61 GiB. Prompt times were 58.84 s
(CPU miss) and 58.75 s (NInfer staged); this diagnostic pair is not a
performance comparison or quality qualification. The [compact boundary
comparison](layer0-to-layer1-current/run5/boundary-comparison.json) and raw
captures remain local pending the normal evidence-retention decision.

### Position-union CPU mirror intervention

The five-position comparison identifies ten expert IDs with CPU-miss/staged
row differences across positions 2043–2047: `64, 72, 83, 88, 90, 109, 120,
123, 136, 144`. A paired run enabled the existing Q2_0/Q2_0 CPU arithmetic
mirror at layer 0 only for that ID set. All ten expert rows, combined MoE
outputs and layer-0 boundary fields then matched the staged arm bit for bit at
all five positions. PLE final state also matched. GDN, tail, pooled,
pooled-full and KV state still differed, so correcting these sampled rows
does not repair the full request. See the compact [MoE
comparison](layer0-to-layer1-current/run6/moe-comparison.json) and [boundary
comparison](layer0-to-layer1-current/run6/boundary-comparison.json).

A follow-up repeated the same mirror with layer-1 committed-state captures.
The CUDA recurrence replay reproduced both captured arms bitwise. At positions
2043–2046, swapping the current captured inputs had zero effect because the
recurrence inputs matched; swapping only the starting state changed the
resulting state by relative L2 `1.72e-8`–`1.89e-8`. Thus the layer-1 recurrent
state was already different before these positions even after the selected
layer-0 rows were mirrored. The [two replay summaries](layer0-to-layer1-current/run7/crossover-2043-44.json)
and [positions 2045–2046](layer0-to-layer1-current/run7/crossover-2045-46.json)
record this local crossover. The run still failed final-state parity in GDN,
tail, pooled, pooled-full and KV. Minimum available/admission memory was
11.64 GiB. Prompt times were 58.61 s (CPU mirror) and 59.10 s (NInfer staged);
one pair with diagnostic copies is not a performance result.

The next correctness experiment should trace the layer-1 starting-state
difference backward across earlier prompt windows while capturing matching
layer-0 MoE rows. This is required to find whether earlier expert IDs, another
layer transition, or both produced the state gap.

### Layer-1 expert-row intervention

With the 15-ID layer-0 mirror active, a paired capture at model layer 1 found
exact MoE input, route IDs/weights and shared output, but two or three routed
expert rows differed per position (IDs `70, 74, 97, 130, 146, 149, 152`;
about `9.7e-8`–`1.19e-7` relative L2). The combined MoE output differed by
`2.24e-8`–`6.75e-8`, matching the layer-1 `ffn_y` delta. See the [layer-1 MoE
comparison](layer0-to-layer1-current/run10/moe-comparison.json).

The Q8_1 diagnostic filter now supports scoped lists such as
`0=64,68;1=70,74` when paired with selectors scoped to layers 0 and 1. Its
functional selector-contract check passed on Orin. A follow-up pair used the
position-derived ID lists for each layer. Layer-1 expert rows, combined MoE
output and committed GDN state at positions 2042, 2044, 2046 and 2047 then
matched bitwise across arms. Token IDs still matched, while final GDN, tail,
pooled, pooled-full and KV state did not. The local layer-0 and layer-1
arithmetic differences are therefore removed at these sampled positions, but
another transition still causes request-level state divergence. See the
[layer-1 MoE comparison](layer0-to-layer1-current/run11/moe-comparison.json)
and [GDN checkpoint comparison](layer0-to-layer1-current/run11/gdn-state-comparison.json).

The pair took 59.24 s prompt time on CPU-miss and 58.68 s with NInfer staging,
with one-token decode times of 223 ms and 204 ms. Diagnostic copies and one
pair make these non-qualification timings. Minimum available/admission memory
was 11.61 GiB. Next, use a final per-layer GDN state dump to identify which
later model layer first diverges after correcting the sampled layer-0 and
layer-1 expert rows. The complete final-state and output-quality gates remain
open.

### Layer-2 extension and first later state divergence

A subsequent CPU-miss/staged pair kept the layer-0 and layer-1 expert mirrors,
captured layer-2 MoE rows and GDN checkpoints, and dumped the final per-layer
GDN state. The final GDN dump is bitwise equal for layers 0, 1 and 2. Layer 3
is the first differing layer: relative L2 `1.31e-9`, maximum absolute delta
`2.98e-8`. The difference grows over later layers. The layer-2 MoE inputs,
routes/weights and shared output were exact, but expert rows differed for IDs
`75, 84, 89, 114, 130` (per-row relative L2 about `8.9e-8`–`1.2e-7`), producing
combined output deltas about `2.29e-8`–`4.00e-8`. Thus the first sampled
unmirrored MoE arithmetic delta remains at layer 2 and immediately precedes
the first nonzero final GDN state at layer 3. This is a local correlation, not
yet a causal proof for the request-level state mismatch.

The run generated equal token IDs and equal residency maps but failed final
state parity in GDN, tail, pooled, pooled-full and KV. The harness also marks
the exact-answer check false because this diagnostic used `--max-new 1`; it is
not a workload-quality test. Minimum available/admission memory was 11.61 GiB.
Prompt time was 59.32 s (CPU miss) and 59.03 s (NInfer staged), with one-token
decode times 219 ms and 210 ms. These are single-pair diagnostic timings, not
performance evidence. Compact local comparisons are in
[`run12/moe-comparison.json`](layer2-extension/run12/moe-comparison.json) and
[`run12/gdn-state-comparison.json`](layer2-extension/run12/gdn-state-comparison.json);
raw large GDN dumps remain local. The next intervention mirrors only the
layer-2 IDs above and captures layer 3 to test whether the same local
arithmetic discrepancy explains the first layer-3 state delta.

That intervention extended the mirror through layer 2 and captured layer 3.
The final GDN dump remained bitwise exact through layers 0–2; layer 3 still
differed by relative L2 `8.72e-10` (maximum absolute delta `2.98e-8`). The
layer-3 MoE inputs, routes and shared output were exact, while rows for expert
IDs `78, 87, 94, 113, 135` differed by about `1e-7` relative L2. Combined
layer-3 MoE output deltas were zero at positions 2043, 2045 and 2047, and
`2.49e-8`–`6.34e-8` at the other captured positions. The GDN state gap grew at
layer 4 to relative L2 `5.07e-6` and at layer 5 to `3.22e-3`. This points to a
repeating small expert-row arithmetic discrepancy at each successive layer;
the layer-2 intervention alone does not explain or repair request state.
Compact [layer-3 comparisons](layer3-extension/run13/) and the final state
summary are retained locally. The diagnostic again produced equal token IDs
and equal residency maps but failed state and exact-answer checks; the latter
is expected to fail for a one-token output cap and is not a quality test.

A follow-up now mirrors the identified layer-3 rows and captures layer 4. It
will check whether layer-3 GDN state becomes exact and whether the first
remaining delta moves to layer 4.

### Layer-3 mirror and layer-4 arithmetic outlier

The layer-3 mirror made the final GDN dump bitwise equal through layers 0–3;
layer 4 became the first differing state (relative L2 `1.78e-6`, maximum
absolute delta `6.16e-5`). Captured layer-4 inputs, routes and shared output
were exact. Most differing expert rows were again near `1e-7` relative L2,
but expert 106 at position 2042 differed by relative L2 `9.60e-4`, maximum
absolute `9.02e-5`; the combined MoE output at that position differed by
relative L2 `9.79e-5`. The per-position layer-4 row IDs also include 82, 91,
131, 153 and 156. Layer 4 therefore contains a localized larger arithmetic
outlier that merits separate investigation from the small rounding-sized
differences. With no layer-4 mirror, later GDN gaps grew to relative L2
`2.99e-3` at layer 5 and `5.41e-3` at layer 6.

The paired run again emitted the same token IDs and residency map but failed
request state parity; it used `--max-new 1`, so its answer check is not a
quality evaluation. A follow-up mirrors layer-4 IDs and captures layer 5.
Compact raw-derived results are in [`run14/moe-comparison.json`](layer4-extension/run14/moe-comparison.json)
and [`run14/gdn-state-comparison.json`](layer4-extension/run14/gdn-state-comparison.json);
large dumps remain local.
