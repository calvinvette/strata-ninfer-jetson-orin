# Layer-27 owner transition and layer-28 state — Orin — 2026-10-20

This randomized same-service pair used three repeated 512-token requests,
12 generated tokens each, no prompt cache, and the tested layer-specific Q8_1
selector through layer 24. Both arms returned the same token IDs for all three
requests. The pinned model is Coder IQ1_M, revision
`5348543e0147355ac9cbcb031184a3546350988e`; the service binary SHA256 is
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`.
Delayed control ran before adaptive. Both supervised arms passed with zero
cgroup memory events; minimum host/admission availability was 14.10 GiB for
adaptive and 14.11 GiB for delayed control.

At position 511, layer 27 routes the same token (271) to the same ten experts
with identical router weights in every request. Its 2,560-value input is also
bit-identical across all three requests in each arm and matches the input used
by the independent native expert parity run. Only expert 175 changes owner in
the adaptive arm: CPU on request 1, then CUDA on requests 2 and 3. The dispatch
encoding is negative for CPU and non-negative for CUDA. Request 1's captured
expert row matches the CPU oracle bit-for-bit; requests 2 and 3 match the CUDA
oracle bit-for-bit. The CPU and CUDA rows differ in all 2,560 values (relative
L2 `0.01294`). The shared-expert output remains exact, while the combined MoE
output changes in all 2,560 values on the owner transition. Delayed control
keeps expert 175 CPU-owned and its expert row, shared output and combined MoE
output remain bit-identical across all three requests.

This directly verifies an owner-dependent layer-27 numerical contribution for
this activation. The layer-28 intermediate trace shows `x` is the first changed
field on the initial-to-intermediate transition: all 2,560 values differ
(relative L2 `9.3027e-4`). The following fields and committed GDN state differ
too (786,199/786,432 recurrent and 10,240/30,720 convolution-history values);
the raw state hash matches service GDN ordinal 21 for all three records. The
intermediate-to-recovery layer-28 intermediates and committed state are exact.
Delayed control's layer-28 intermediates and state are exact across both
transitions. Together, these observations trace this sample from a layer-27
owner change to the next layer's changed input and committed state. They do
not prove this is the sole source of all accepted-state drift or establish a
general drift bound. Phase 5 remains open.

Reproduce the row/oracle join with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer24-short-short-short-no-cache-layer27-state28-pair/compare_repeated_layer27.py

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_layer26_gdn_intermediates.py \
  --run bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer24-short-short-short-no-cache-layer27-state28-pair/adaptive-cap8/result \
  --layer 28 --positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer24-short-short-short-no-cache-layer27-state28-pair/adaptive-layer28-intermediate-analysis.json
```

The same-input operator oracle was run from the captured layer-27 input with
`native_expert_parity`, model shard
`~/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf`,
expert 175 and layer 27. Raw route, input, expert-part, combined-output, GDN,
accepted-state and supervisor captures are retained with the comparison JSON.
