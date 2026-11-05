# Coder mixed-codec PCIe execution check with pinned complement

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This is a one-token
functional and numerical check of the mixed-codec NInfer grouped path for both
resident and staged experts. It is not a throughput, sustained-state, or
answer-quality benchmark.

## Setup

Paired Strata and strict-NInfer `StrataEngine` services used Coder IQ1_M, token
IDs `1,2,3`, greedy output, one generated token, the same 391-slot static
profile and cache, `--pcie-frac 1.0`, and `--resident-budget-gib 1`. The
resident-budget option pinned a 1 GiB expert complement; the environment set
`STRATA_RESIDENT_HEADROOM_GIB=6`, preserving the required host headroom. Both
arms executed successfully and generated token `4`.

At layer 0 / position 2, the same ten experts were selected in the same order.
The owner trace assigned four resident/foresight rows (experts 25, 54, 35, 19)
to primary VRAM and six misses (143, 175, 252, 240, 204, 246) to PCIe. No row
was CPU- or peer-owned. The CPU-output capture has no rows at this position.
The independently captured pre-expert activation hash is identical in both
arms and matches the earlier service row: `b48f8a59fa63987bf62d3c69b1115606dc9fe9352ed7714e120668af3c271489`.

## Oracle result

For all ten rows, Strata's captured expert outputs match the native CUDA grouped
oracle bit-for-bit. Strict NInfer's outputs differ from that oracle by relative
L2 `7.64e-8`–`9.24e-8` across the ten rows, with no invalid values. This includes
all six PCIe-owned misses, establishing that strict NInfer's supported mixed
codecs traverse the grouped GPU path for those staged rows in this request.
The service logged all seven observed mixed-codec tuple dispatches. The previous
`--pcie-frac 1.0` check without a pinned complement left misses on CPU; the
1 GiB bounded pinned complement is what made these routes PCIe-eligible.

The guarded service pair retained at least 18.62 GiB available RAM, well above
the 6 GiB floor; the existing cgroup OOM-kill counter stayed at one. The
separate ten-row oracle run retained at least 24.12 GiB. Clocks and energy were
not measured. Raw activation and expert-part dumps remain under `/tmp` and are
not committed. Compact results and supervisor records are included here.

This confirms the one-token PCIe execution boundary only. It does not prove
accepted-prefix or final-state parity over longer requests, task quality,
performance benefit, multi-codec sustained stability, or that a generally
useful pinned budget should be enabled by default.
