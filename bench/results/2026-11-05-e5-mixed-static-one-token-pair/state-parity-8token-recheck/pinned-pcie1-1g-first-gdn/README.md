# First-token GDN dump with static pinned PCIe experts

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This is an accepted-prefix
state diagnostic for Coder IQ1_M; it is not a performance or task-quality
measurement.

## Setup

Strata and strict NInfer ran the token-ID prompt `1,2,3` with greedy decoding,
one generated token, MTP-2, CPU prefill sharing disabled, the same 391-slot
profile/cache, `--resident-budget-gib 1`, `--pcie-frac 1.0`, and adaptation
disabled (`--adapt-every 0 --adapt-swaps 0`). The 1 GiB resident complement was
page-locked with `STRATA_RESIDENT_HEADROOM_GIB=6`. Both generated token `4`.
The GDN arrays were dumped at the first accepted-token boundary (state length
3). Each raw dump is 113 MiB and remains in `/tmp/e5-coder-pinned-first-gdn/`.

## GDN state comparison

The dump contains 36 serialized GDN state slices and 29,417,472 FP32 values.
Slice 0 is bit-identical. Slice 1 is the first difference (relative L2
`1.14e-5`, maximum absolute delta `9.99e-5`); slice 2 reaches `2.56e-3` and
slice 3 `4.84e-3`. Global relative L2 is `1.08e-2`; 28,575,908 values differ
(97.14%). The largest slice relative L2 is `2.06e-2` at serialized slice 27,
with maximum element error `0.2883`. Slice numbers are from the serialized GDN
state layout; this comparison does not by itself assign a causal operator or
model-layer mapping.

The owner capture from the paired eight-token run confirms four resident GPU
rows and six PCIe rows, with no CPU result for that dispatch. The all-ten-row
operator oracle is in the [staged mixed-codec report](../../layer0-ten-expert-oracle/pcie-frac-1-pinned1g/README.md).
The state dump shows that matching the first token and matching each isolated
expert to its kernel oracle do not guarantee exact recurrent state. A next
trace should compare the first divergent GDN input/output stage and the
preceding layer output under this same static pinned profile.

The guarded pair retained at least 19.16 GiB available RAM; sampled cgroup
OOM-kill count remained one. Hash/state instrumentation was enabled, so timing
fields in service results are excluded. Clocks and energy were not qualified.
The per-slice comparator summary, service logs and memory samples are saved
here; raw GDN arrays are excluded from Git.
