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
