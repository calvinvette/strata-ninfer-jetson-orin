# Q2_0 CPU/GPU expert operator parity — Orin — 2026-10-14

This diagnostic checks whether changing an expert between a GPU cache hit and a
CPU miss can introduce numerical differences relevant to the adaptive-swap
state-drift investigation. It uses the current Q2_0 model artifact and the
existing `native_expert_parity` test, which extracts expert 7 from each selected
GGUF layer and compares the CPU and CUDA expert routes on the same seeded input.

The Release CUDA target rebuilt successfully from the current checkout. The run
used the Q2_0 shard already under `~/models/strata-orin-validation/Q2_0/` and
sampled layers 0, 1, 2, 3, 20 and 47. It passed with zero failures. CPU/GPU
whole-expert output relative L1 ranged from `9.85e-8` to `1.06e-7`. CPU and GPU
routes each differed from the floating reference by `1.13e-2` to `1.27e-2`,
which the test attributes to their represented activation contract. GPU decode
matched ggml dequantization exactly for the checked matrices, and decode-once
matched per-entry kernels bitwise.

The diagnostic was extended to count bitwise-different output words. Across the
six samples, 5,561–5,679 of 7,680 words differed (72.4–74.0%) while relative L1
stayed near `1e-7`. This confirms widespread low-magnitude rounding differences
for the seeded inputs; a strict state fingerprint can observe such differences
even when the relative operator delta is small. It remains an operator-level
finding, not evidence that these particular differences caused the service
state drift.

These are seeded operator-level inputs, not captured service activations or the
specific experts selected by the adaptive trace. The test reports relative L1,
not bitwise equality; it therefore establishes a small nonzero CPU/GPU
calculation difference for this sample, but does not prove that this difference
caused the observed service state drift. It also does not measure performance.
The next diagnostic should compare CPU and GPU expert outputs on captured
service activations and the actual experts selected/evicted in the controlled
sequence, before attributing the drift to the expert path.

Command:

```sh
build/integration/candidate/native_expert_parity \
  ~/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf \
  0 1 2 3 20 47
```

The raw stdout is in [stdout.txt](stdout.txt). Model shard checksums are
retained in the prior [Q2_0 artifact identity manifest](../2026-10-11-phase3-q2-actual32k/artifact-identities.json).
The executable and raw-output SHA256 values are in [SHA256SUMS](SHA256SUMS).
The diagnostic change only reports CPU/GPU bitwise differences; it does not
change either computation or the parity pass criterion.
