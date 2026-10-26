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
commit `cc8d1faf`, maestro1 rebuilt and linked the HIP target with two jobs.
This is x86 compile/link evidence only; maestro1 has no relevant
accelerator runtime. The configured SYCL `gdn_parity` target uses the separate,
unchanged `sycl/src/kernels/gdn_parity.cpp`, so it had no work for this
CUDA/HIP-only source change.

Reproduce on the Orin with the matching captured raw files using:

```bash
cmake --build build/integration/e0-cuda-build --target gdn_parity --parallel 2
build/integration/e0-cuda-build/gdn_parity --selftest
build/integration/e0-cuda-build/gdn_parity --replay-crossover \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/gdn-state-step-sweep/cpu-miss.gdn-commit \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/gdn-state-step-sweep/ninfer-staged.gdn-commit \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer1-position-sweep/cpu-miss.layer1.gdn-diag \
  bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer1-position-sweep/ninfer-staged.layer1.gdn-diag
```
