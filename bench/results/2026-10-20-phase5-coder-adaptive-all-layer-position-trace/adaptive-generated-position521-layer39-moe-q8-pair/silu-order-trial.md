# Rejected global SwiGLU expression trial

The CPU Q8_1 path was temporarily changed from `(g * (1 / (1 + exp(-g)))) * u`
to `(g / (1 + exp(-g))) * u`, rebuilt into `native_expert_parity`, and tested
on two same-input owner-switch rows. The worktree was restored to the original
reciprocal expression and the parity target rebuilt afterward.

| Row | Reciprocal CPU expression | Division CPU expression |
| --- | --- | --- |
| Layer 39, expert 90, position 521 | 3/60 hidden Q8_1 block scales differ; final CPU/GPU outputs differ in 7,677/7,680 words (relative L2 `1.20273e-4`) | All 60 hidden blocks and all 7,680 outputs match CUDA bit-for-bit |
| Layer 31, expert 22, position 519 | All 60 hidden blocks and all 7,680 outputs match CUDA bit-for-bit | 3/60 hidden scales differ; final outputs differ in 7,677/7,680 words (relative L2 `1.32e-4` in the recorded parity run) |

The division trials also disagreed with the parity harness's independent hidden
reconstruction, which still encodes the reciprocal expression; that check
would need to be updated if the operation contract changed. The direct CUDA
hidden-block and final-output comparisons show the important cross-row tradeoff:
neither one global host expression preserves both previously exact cases. The
trial is rejected as a global fix. No source change from it remains.

The current reciprocal path's three scale discrepancies at layer 39 cause a
measured layer-41 raw state relative-L2 delta of `7.27893e-4` after position
521 and `7.38754e-4` after position 522 in this adaptive pair; delayed control
is bit-identical. These two values characterize this trace only and do not
establish a long-chain bound.
