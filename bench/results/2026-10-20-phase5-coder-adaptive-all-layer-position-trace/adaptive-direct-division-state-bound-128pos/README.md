# 128-token direct-division adaptive recovery pair — Orin — 2026-10-22

This randomized, supervised same-binary pair extended the pinned Coder IQ1_M
`short-512 → long-2048 → short-512` sequence to 128 generated tokens per
request. It used seed `20261045` (delayed control then adaptive),
`STRATA_NATIVE_CPU_Q8_1_DOT=all`, and raw committed layer-32 GDN captures at
positions 515, 534, 574 and 638. The direct-division binary SHA256 was
`25c0b6b2a3c275044fdaae8604d01c8ea52336e20a767ffaaa02ad5e0ed0b8dc`. The model
is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M; shard hashes are in
`campaign.json`.

The delayed-control arm was exact in all six accepted GDN state records and
all 128 initial/recovery generated token IDs. Its adaptive counterpart was
exact at position 515. At position 534, recurrent/convolution relative L2 was
0.00527/0.01052. Across the 128 recovery IDs, 73 differed, beginning at
output index 47. At position 574 the relative-L2 deltas were 0.31063/0.65311;
at position 638 they were 0.45374/0.88351. Because token choices had diverged
by the later endpoints, those final state deltas include different accepted
token histories and are not a pure state-transaction error measurement. All
raw state records matched the service accepted-prefix hashes.

The paired runs took 625.8 seconds (adaptive) and 631.7 seconds (delayed).
Minimum host/admission availability was 14.29/14.25 GiB, above the 6-GiB floor;
no cgroup memory events were observed. Dynamic CPU/GPU clocks were sampled
without control; EMC was unavailable and energy was not measured. This is a
correctness campaign, not a performance comparison.

Compared with the 64-token same-day direct-division pair, this run shows that
matching all 64 outputs in that shorter request sequence does not establish a
128-token recovery bound. The longer recovery first diverges at output 47,
although the same 128-token delayed control is exact. A targeted [first-drift
boundary capture](first-drift-boundary/README.md) found recurrent/conv relative
L2 of 0.01355/0.00964 at position 557 and 0.01319/0.00986 at position 558,
before the first differing output (index 47, `449` versus `264`); consumed
token IDs through index 46 still match. The small but nonzero layer-32 state
difference therefore precedes the first changed token, though it does not
identify the earlier layer or operation responsible. Later endpoint deltas
remain confounded by changed token histories. Phase 5 remains open.

Per-arm `gdn-commit-state-summary.json` verifies service hashes. `analysis.json`
records generated token IDs, prompt fingerprints and settings. Raw state arrays,
logs and supervisor telemetry remain local. `SHA256SUMS` records compact
report inputs.
