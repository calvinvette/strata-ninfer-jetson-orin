# Direct-division adaptive recovery rerun — Orin — 2026-10-22

This randomized, supervised same-binary pair repeated the pinned Coder IQ1_M
`short-512 → long-2048 → short-512` sequence (64 generated tokens each),
comparing accepted-only cap-8 adaptation with delayed control. It used seed
`20261044`, `STRATA_NATIVE_CPU_Q8_1_DOT=all`, and captured raw committed
layer-32 GDN state at positions 515, 534 and 574. The repository head at
launch was `99bcd795c9a49492fbe2b7e6a391f75d459f0619`; the binary SHA256 was
`25c0b6b2a3c275044fdaae8604d01c8ea52336e20a767ffaaa02ad5e0ed0b8dc`. The model
is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M; both shard checksums are in
`campaign.json`.

Both arms passed their run supervisors. The adaptive and delayed arms took
372.4 and 371.4 seconds. Minimum host/admission availability was 14.23/14.27
GiB, above the 6-GiB host floor; sampled cgroup memory events were zero. Dynamic
CPU/GPU clocks were sampled without control; EMC frequency was unavailable.
Energy was not measured. These are correctness runs, not performance results.

The delayed-control arm reproduced initial recurrent and convolution state
bit-for-bit at all three endpoints, and its initial/recovery generated token
IDs matched 64/64. The adaptive arm was bit-identical at endpoint 515; by 534,
recurrent/convolution relative L2 was 0.00527/0.01052; by 574 it was
0.01435/0.02024. At endpoint 574, 786,431/786,432 recurrent values and all
30,720 convolution-history values differed. Nevertheless, initial and
recovery generated token IDs matched 64/64 in this run. All six raw state
records in each arm matched the service's accepted-prefix hashes at all three
positions.

For context, the earlier 2026-10-20 adaptive run using the multiply-by-sigmoid
CPU expression had 40/64 initial/recovery token IDs differ and at endpoint 574
recurrent/convolution relative L2 of 0.5243/0.9158. That cross-day comparison
is suggestive, not a controlled attribution: this pair shows a large
improvement under the direct-division build, but the earlier run differed in
binary and date. The remaining raw state drift means this does not establish a
long-chain bound or close Phase 5. Repeat the expression comparison in a
same-day build pair before attributing the improvement or changing defaults.

`gdn-commit-state-summary.json` contains the paired layer-32 measurements;
per-arm summaries also validate service hashes. `analysis.json` records the
64 generated IDs, model/prompt identity and run settings. Raw arrays, service
logs, supervisor telemetry and exact checksums are retained locally. No model,
binary or raw large capture is added to Git.
