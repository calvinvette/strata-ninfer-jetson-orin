# E6 Q2_0 multi-layer MoE bundle attempt

This paired 160K diagnostic reused the held-out Q2_0 retrieval workload and
captured every residual boundary at generated token position `163849`. It also
requested one packed MoE record each for layers 1, 7 and 8.

## Result

Both arms generated the exact expected answer, all 47 token IDs matched, and
the resident expert maps matched. Persistent state did not: GDN, tail, pooled,
pooled-full and KV hashes differ. The boundary files contain the requested
position for all 47 layers in each arm. Neither arm produced its requested
MoE bundle, so this attempt does not localize the active-expert arithmetic.
The reason the bundle writer did not emit a file remains unresolved; the
capture harness now reports this as a failed diagnostic instead of treating it
as a pass.

The supervisor completed after `3235.9 s`. Minimum available host memory was
`7.04 GiB`, peak observed swap was `6.01 GiB`, and sampled cgroup OOM-kill
counters remained zero. This is correctness diagnosis only, not a performance
measurement or qualification.

## Identity

- Model: `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0`, two GGUF shards, local model root
  `~/models/strata-orin-validation/Q2_0/`.
- Prompt: 163,840 tokens; prompt content SHA256
  `8377a1053405efb5ca733be15d3e3a70d7586195a88c1db8b4655d6375a7cd94`;
  token IDs SHA256
  `6d38b36ee0a8a2c33930db06c0db110cb510b446738640bf26891808990fc302`.
- Selected output token position: `163849`.
- Engine binary SHA256: `3c6cefa6e96ad5f3fee42776957e440b66a3104e3d18d9bddf40686084c0330b`.
- The binary contains the temporary near-target position logger used to
  investigate the missing bundle. It differs from committed `verify.cpp` only
  by that diagnostic logging block; rebuild before using it for later
  comparisons.
- Both arms used the same staged retrieval configuration and `--spec 2`.

Raw logs, boundary files, residency maps and result JSON remain in this
directory and are intentionally not committed.
