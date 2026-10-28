# E6 model-layer-4 GDN capture at position 163,885

## Outcome

This paired 160K Q2_0 run captured the boundary after model layer 3 and GDN
intermediates at model layer 4 for the final accepted token position 163,885
(token ID 23). Both arms generated the same exact 47-token answer, token IDs,
and expert residency. The final persistent state still differs in `gdn`,
`tail`, `pooled`, `pooled_full`, and `kv`.

The boundary after layer 3 already differs: the residual stream relative L2 is
`1.05e-3`, the hyperconnection MoE row is `1.48e-2`, and the next-layer
post-read activation is `1.45e-3`; the next-layer `xn` is `4.75e-3`. At GDN
layer 4, the incoming `x` differs by `5.74e-3` relative L2 before the
recurrent update. GDN `qkv` and convolution output `h` differ by `4.51e-3`
and `4.58e-3`; gate and beta differ by `1.43e-3` and `6.99e-4`. Raw recurrence
output `o` differs by `2.53e-3`, normalized `y` by `5.40e-3`, projected GDN
output by `9.19e-3`, and the final feed-forward output by `1.18e-2`.

This shows that the layer-4 recurrence receives materially different inputs
for this generated position; the recurrence cannot explain the incoming `x`
split. This run did not capture the pre-step layer-4 recurrent state, so it
cannot independently replay the recurrence equation or assign the upstream
difference to a specific QSA or MoE operation. The matched final answer and
residency do not establish internal parity. This is one position in one
instrumented trajectory, not a stable earliest-divergence claim.

| Capture | Relative L2 | Maximum absolute delta |
|---|---:|---:|
| Layer 3 residual stream | 1.05e-3 | 6.97e-5 |
| Layer 3 MoE row | 1.48e-2 | 4.49e-4 |
| Layer 3 next-layer post-read activation | 1.45e-3 | 8.01e-5 |
| Layer 3 next-layer `xn` | 4.75e-3 | 4.02e-2 |
| Layer 4 GDN input `x` | 5.74e-3 | 1.29e-2 |
| Layer 4 raw recurrence `o` | 2.53e-3 | 5.16e-4 |
| Layer 4 normalized `y` | 5.40e-3 | 4.97e-3 |
| Layer 4 projected GDN output | 9.19e-3 | 3.36e-3 |
| Layer 4 feed-forward output | 1.18e-2 | 6.88e-4 |

## Conditions

The prompt had 163,840 tokens, content SHA256
`8377a1053405efb5ca733be15d3e3a70d7586195a88c1db8b4655d6375a7cd94`, and
token-ID SHA256
`6d38b36ee0a8a2c33930db06c0db110cb510b446738640bf26891808990fc302`. The
paired run took 53.95 minutes. Minimum available memory was 6.67 GiB, peak swap
was 0.83 GiB, and sampled OOM kills were zero. Clocks were observed only;
energy was not measured. Raw captures and logs remain local-only. This is a
correctness diagnostic, not a performance result.
