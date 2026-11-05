# 2K mixed-codec Coder retrieval state check

Date: 2026-11-05. Jetson Orin AGX, CUDA 12.6. Two fresh Strata/strict-NInfer
pairs used an exact 2,048-token prompt with 154 closed-ticket distractors and
an active ticket whose code was `73192`. The context reservation was 4,096
tokens. Prefix tracing was disabled; one full state fingerprint was captured
after request completion.

## Results

All four requests returned the exact retrieval answer `73192` in six token
IDs. Within each pair, tokens and all 11 final state fields matched across
backends, including MTP and stale-page hashes. Each backend also reproduced
its exact token sequence and final state across the two fresh pairs.

| Measure | Result |
| --- | --- |
| Prompt | 2,048 tokenizer-verified tokens |
| Context reservation | 4,096 tokens |
| Answer / output | `73192`; six identical token IDs in every arm |
| Final state | All fields equal across backends and repeated per backend |
| Supervisor | Both pairs passed; minimum available RAM 20.86 GiB |
| Swap / OOM | Peak sampled machine swap 1.80 GiB; no increase to existing OOM-kill count |

The same Coder IQ1_M shards, binary and static expert profile as the preceding
final-only reports were used. Binary SHA-256:
`df8e666b8d19dbdc5f687826b4d7187783f4c91aaf5ba2037497a65823d4be98`; profile
SHA-256: `c1e66c2e60ae8e7880befa303fb6bb79da1ccdd59895053eb95d433c648ef047`.
These sequential, state-hashed requests are correctness evidence only; their
timings are excluded. Clocks were dynamic, EMC readback was denied and energy
was not measured. See [`results.json`](results.json) and
[`repeat-results.json`](repeat-results.json).

Reproduce from the repository root:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-11-05-e5-coder-natural-prompt/retrieval-2k-final-only/supervisor \
  --sample-clocks --timeout 1800 -- \
  python bench/results/2026-11-05-e5-coder-natural-prompt/run_retrieval_final_pair.py \
  bench/results/2026-11-05-e5-coder-natural-prompt/retrieval-2k-final-only/run
```

This validates one retrieval task at one longer prompt size. It does not cover
other models, context lengths, adaptive residency, or performance. E5/E6/E7
remain open.
