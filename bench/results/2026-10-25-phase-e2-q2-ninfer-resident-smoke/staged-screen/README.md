# Q2_0 bounded expert staging screen

Date: 2026-10-25, Jetson AGX Orin, CUDA 12.6, SM87. This screen exercised the
existing Strata pinned-complement and bounded staging owner with the NInfer
Q2_0 grouped adapter. It did not add another allocator or memory authority.

## Setup

All services used the same source and Release executable, 8K context, 3,000
profile-filled GPU slots, the same model/PLE/profile/tokenizer, prefill 128,
eight workers, FP16 KV, MTP inactive (`0 of 0` accepted drafts) and the same
55-token prompt plus 29-token output. Each fresh service ran one warmup then one
measured request. Every start used the same resident GPU map hash
`a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`.
Measured output hashes all matched
`18e649c52e8a6a942bfb6c486a4da267fc7ca05faaf55c831ea4b35372df848e`.

Each arm reserved a 1-GiB host complement with
`--resident-budget-gib 1`. `STRATA_RESIDENT_HEADROOM_GIB=9` preserved the
six-GiB host floor plus the separate three-GiB workspace reserve. Logs showed
about 17.1 GiB physically available after startup and the 1-GiB complement was
page-locked and mapped. The CPU-miss control used `--pcie-frac 0`; the staged
candidate used `--pcie-frac 0.55`, strict NInfer, and the existing automatic
copy-kernel staging mode. The direct-mapped mode was measured separately in
[direct-screen](../direct-screen/README.md).

## CPU miss versus copied NInfer staging

| Pair | Prompt latency, CPU / staged | Decode latency, CPU / staged | Client total, CPU / staged | Extra GPU offloads |
| --- | ---: | ---: | ---: | ---: |
| 1 | 5.738 / 5.786 s | 3.055 / 3.282 s | 8.796 / 9.071 s | 0 / 106 |
| 2 | 5.892 / 5.880 s | 3.091 / 3.291 s | 8.985 / 9.173 s | 0 / 106 |
| 3 | 5.895 / 5.857 s | 3.098 / 3.288 s | 8.996 / 9.148 s | 0 / 106 |

Median paired change for copied NInfer staging versus CPU misses was −0.20%
prompt latency, **+6.47% decode latency**, +2.10% client total time, and −0.02%
client TTFT. Positive latency change is slower. Although `pcie_frac` requested
55% of eligible misses for the GPU, the bounded 1-GiB complement supplied only
106 of 13,920 routed expert slots (0.8%) on the measured request. This count
comes from Strata's `pcie_frac` offload counter. Orin shares physical memory, so
it does not represent traffic over a separate PCIe link. This identifies low
staged coverage at this resource budget; it does not demonstrate a staging
speedup. The NInfer adapter was exercised through the existing grouped staged
pointer batch, and request completion plus the source's offload counter
confirmed that staged GPU work occurred.

## Direct-mapped mode

The direct-mapped screen used three fresh NInfer services with the same 1-GiB
pinned complement and `--pcie-mode direct`. All requests completed with the same
text and resident map. Each measured request reported 106 `pcie_frac`-selected
GPU expert entries (0.8% of routed work). Orin shares physical memory; these are
not transfers over a discrete PCIe link. Median prompt/decode/client/TTFT was
5.877/3.296/9.179/5.970 seconds. Those values are descriptive: the direct-only runs followed the
CPU-versus-copy screen and were not randomized as paired blocks against it.
They show that the mapped alias path is functional on this Orin, but no clear
performance advantage over the copy-kernel path or CPU fallback.

## Decision and limitations

The integration can reuse Strata's existing bounded `GpuPlanSink` descriptors,
pinned complement, staging ring, device aliases and stream ownership. The
adapter groups all entries sharing an expert pointer and processes those rows
with one grouped dispatch; no second expert cache or memory ledger was added.
At 1 GiB, only a small share of routed misses reached the GPU, while the decode
and client results regressed versus CPU misses. Keep CPU fallback as the default
for misses. Larger pinned complements and stage-depth/worker sweeps remain open;
they require a fresh memory-admission check and must retain the 6+3-GiB reserve.
The direct-mapped result is not a paired performance comparison. No actual GPU
clock readback, energy measurement, Nsight kernel breakdown or independent
quality evaluation was available.

`results.json`, per-run logs, launch configurations and resident maps are kept
beside this report. The runner is
[`run_staged_miss_screen.py`](../run_staged_miss_screen.py). Models remain under
`~/models/`.
