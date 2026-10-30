# 65K prompt-position state checkpoints

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is an instrumented,
same-process state diagnostic, not a performance or quality result.

## Setup

One current-source strict-NInfer process handled two identical requests using
the same 65,536-token prompt, temperature 0, 32-token generation limit and
131,072-token context. Prompt cache and PCIe staging were disabled. The CUDA
executable was built from the current worktree with SHA-256
`91314049e2ce76215f474dceaef43d2094f6b2fb2bb8e125fbb197d0ec30c4d8`.
Full tracing was disabled. The opt-in request-reset and prompt-boundary hashes
were enabled, along with prefill state captures requested at 8,192, 16,384,
32,768, 49,152 and 65,536 tokens. The internal prompt boundary is position
65,535; the requested 65,536 checkpoint therefore did not emit a separate
record. The existing prompt-boundary hook captured the final prompt state at
65,535.

## Result

Both requests passed and reported 65,536 prompt tokens and 32 generated tokens.
Immediate post-reset fingerprints matched. The compact sampled hashes also
matched at every emitted prefill checkpoint:

| Prompt position | GDN | PLE | QSA tail | QSA dead | QSA pooled full | PLE previous tokens |
| ---: | --- | --- | --- | --- | --- | --- |
| 8,192 | `96a8debe9d965ae8` | `c776a56826340f95` | `f72d24ad104300b7` | `ba4d730b89d297e5` | `fa799ae60931ddd9` | `2438,2438` |
| 16,384 | `328e2676e400a9d1` | `f3c2ee38d86342d6` | `051ca71af2f472ae` | `ba4d730b89d297e5` | `9921898cc04b7463` | `2438,2438` |
| 32,768 | `c75fa822b67da359` | `27a38a0dfacc2f59` | `d91c3b627f7270a5` | `ba4d730b89d297e5` | `f2ff962795faea17` | `2438,2438` |
| 49,152 | `d4080d435b7a0c5c` | `e563933fa32c4e8b` | `2fc6f5ee91b66772` | `ba4d730b89d297e5` | `94bf2ed1420a4c0a` | `2438,2438` |

The final prompt-boundary hashes at position 65,535 reproduced the earlier
same-process repeat: request 1 had GDN `85907b6a2b85d24e`, pooled
`daf9928c718c7b33`, KV `0552810263e21418` and pooled-full
`f2e8d94d3fe3944a`; request 2 had GDN `5c793b8a70da9a04`, pooled
`768df0029b886add`, KV `a9df73b118768bd5` and pooled-full
`ed5187a71d99941c`. PLE, QSA tail, MTP, stale, dead and PLE previous-token
hashes matched at the boundary.

## Interpretation and limits

Reset and sampled state match through 49,152 tokens, while the final boundary
diverges in GDN, pooled state and KV. The earliest divergence is therefore
bracketed after the 49,152 checkpoint and at or before prompt boundary 65,535;
these samples do not localize it more closely. The 65,536 target did not emit
because the internal boundary is 65,535, which the separate boundary hook
captured. Captures synchronize the device and copy state to host, so they may
change scheduling. This run does not identify an operation or qualify
performance. Continuous clocks, energy and memory telemetry were not
collected. E6/E7 remain open.

Raw logs and response bodies remain under
`/tmp/e6-65k-ninfer-prefill-checkpoints/`.
