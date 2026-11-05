# Arithmetic task final-state recheck

Date: 2026-11-05. Jetson Orin AGX, CUDA 12.6. This repeats the existing
32-token chat-formatted `2 + 2` Coder prompt with only a final state fingerprint
enabled. Accepted-prefix tracing and GDN dumps were disabled.

## Result

Two fresh Strata/strict-NInfer pairs both returned the exact answer `4` and
token IDs `[19, 248046]`. In each pair, the complete final state fingerprint
matched across backends, including GDN, PLE, QSA tail, pooled/dead indexes,
KV, MTP and page-tail `stale` hashes. The same token and full final-state
fingerprints repeated for each backend across the two pairs. This revises the
interpretation of the earlier per-token traced run, where accepted-prefix
state hashes and raw GDN arrays differed. The trace helper synchronizes and
copies state after each committed token; the final-only check runs after
generation. This supports an instrumentation or scheduling effect as a
possible explanation, but does not prove its cause or validate intermediate
state between tokens.

| Measure | Result |
| --- | --- |
| Exact answer | Both arms returned `4` in both pairs |
| Token IDs | `[19, 248046]` in all four requests |
| Final persistent state | All 11 fields equal across backends and repeated within each backend |
| Supervisor | Both pairs passed; minimum available RAM 20.94 GiB |
| Swap / OOM | Peak sampled machine swap 1.18 GiB; pre-existing OOM-kill count stayed at 1 |

The request is too short for performance measurement; its service timings are
excluded. Clocks were sampled dynamically, EMC readback was denied, and energy
was not measured. The binary SHA-256 is
`df8e666b8d19dbdc5f687826b4d7187783f4c91aaf5ba2037497a65823d4be98`; the
profile SHA-256 is
`c1e66c2e60ae8e7880befa303fb6bb79da1ccdd59895053eb95d433c648ef047`.
Machine-readable outputs are in [`results.json`](results.json) and
[`repeat-results.json`](repeat-results.json).

Reproduce from the repository root with:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-11-05-e5-coder-natural-prompt/arithmetic-final-only/supervisor \
  --sample-clocks --timeout 1800 -- \
  python bench/results/2026-11-05-e5-coder-natural-prompt/run_arithmetic_final_pair.py \
  bench/results/2026-11-05-e5-coder-natural-prompt/arithmetic-final-only/run
```

This is one short task family and one profile. It does not close E5's broader
mixed-codec quality/state matrix, define an intermediate-state tolerance, or
provide performance evidence.
