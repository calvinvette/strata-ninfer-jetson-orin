# Same-day multiply-by-sigmoid comparison — Orin — 2026-10-22

This randomized, supervised same-binary pair repeated the pinned Coder IQ1_M
`short-512 → long-2048 → short-512` sequence (64 generated tokens each),
comparing accepted-only cap-8 adaptation with delayed control. It used seed
`20261044`, `STRATA_NATIVE_CPU_Q8_1_DOT=all`, and captured raw committed
layer-32 GDN state at positions 515, 534 and 574. The repository head at
launch was `99bcd795c9a49492fbe2b7e6a391f75d459f0619`; binary SHA256 was
`cec6d32851037316b7aa8b90115974fbd3793d6d960cea17723a5a0b3b95ac78`. Relative
to the direct-division binary, the only source change was the CPU SwiGLU
expression in `src/kernels/cpu/native_expert.cpp`: `g * (1 / (1 + exp(-g))) * u`
in place of `(g / (1 + exp(-g))) * u`. The model is
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M; both shard hashes are in
`campaign.json`.

The adaptive and delayed arms both passed their run supervisors and raw-state
service-hash checks. They took 372.4 and 371.9 seconds. Minimum
host/admission availability was 14.21/14.30 GiB, above the 6-GiB host floor;
no cgroup memory events were observed. Dynamic CPU/GPU clocks were sampled
without control. EMC frequency was unavailable and energy was not measured.
These are correctness runs, not performance results.

The delayed-control arm reproduced initial recurrent and convolution state
bit-for-bit at all three endpoints and matched initial/recovery generated IDs
64/64. Under adaptive swaps, relative-L2 drift grew as follows:

| Accepted position | Recurrent state | Convolution history | Initial/recovery generated IDs |
| --- | ---: | ---: | ---: |
| 515 | 0.00166049 | 0.00735400 | 64/64 match overall |
| 534 | 0.02559047 | 0.02522823 | 64/64 match overall |
| 574 | 0.52432613 | 0.91576904 | 40/64 differ overall |

All six raw records matched the service's accepted-prefix hashes. This
reproduces the earlier 2026-10-20 multiply-expression result on the same
hardware and request sequence.

The paired [direct-division run](../adaptive-direct-division-state-bound-64pos/README.md)
used the same seed, model, requests, capture endpoints and controls on the same
date, with the same arm order. It had zero token differences and recurrent /
convolution relative-L2 drift of 0.01435191 / 0.02023753 at position 574. The
control states are exact in both expression pairs. Together with the captured
single-row operator oracle, this isolates expression ordering in the CPU
SwiGLU path as the cause of this scenario's adaptive recovery regression. It
does not bound other models, quantizations, CPU/GPU operators, longer chains or
other state paths, and does not establish a throughput effect. The source is
restored to direct division and no default or public configuration changed.
Phase 5 remains open for broader held-out and long-chain validation.

`gdn-commit-state-summary.json` contains the raw state measurements and
service-hash checks; `analysis.json` records all 64 generated IDs per request,
model/prompt identity and settings. Raw arrays, logs and supervisor telemetry
remain local; `SHA256SUMS` records the compact report inputs.
