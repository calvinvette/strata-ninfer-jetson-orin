# Coder layer-0 PCIe-share owner diagnostic

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This is a functional
owner-routing diagnostic for Coder IQ1_M, not a timing or quality benchmark.

## Setup and result

A paired `StrataEngine` request used prompt IDs `1,2,3`, greedy sampling, one
generated token, the existing 391-slot static profile/cache, and the exact same
model and runtime options for Strata and strict NInfer. Both arms added
`--pcie-frac 1.0`; CPU prefill sharing remained disabled. The owner capture
selected the same ten layer-0 experts at position 2 in both arms:
`143,175,252,25,54,240,35,204,19,246`.

The final owner trace was four primary-VRAM/foresight rows (experts 25, 54, 35,
19), six CPU rows (143, 175, 252, 240, 204, 246), and zero PCIe or peer rows.
The companion CPU-output capture independently confirms that all six misses
were produced by the CPU pool in both arms. The service outputs diverged at the
one generated token (Strata `4`, strict NInfer `5`); that remains a separate E5
state/quality issue, and this one-token probe does not explain it. The summary
contains route/owner and per-row output hashes; raw captures remain in
`/tmp/e5-coder-layer0-owner-pcie1/`.

## Interpretation and limits

`--pcie-frac 1.0` did not create PCIe execution for this request. The
`--mmap-experts` source was not backed by a pinned device complement. In
`src/core/expert_source.cpp`, `pcie_layer()` requires a ready pinned complement
and device alias; the routing planner also checks that each selected blob is
pinned before assigning owner kind 1. Thus this result documents unsupported
coverage for this source/configuration; it is not a negative result for NInfer
compute. A mixed-codec staged-miss experiment needs a bounded pinned source
path first, with Orin shared-memory headroom and transition peaks admitted.

The guarded run passed with minimum available RAM 20.74 GiB and no increase in
the pre-existing cgroup OOM-kill count (1). Clocks and energy were not measured.
See [`comparison.json`](comparison.json) and the supervisor memory record.
