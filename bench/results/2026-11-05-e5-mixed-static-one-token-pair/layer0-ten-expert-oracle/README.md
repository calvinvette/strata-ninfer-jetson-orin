# Ten-expert layer-0 service oracle

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This diagnostic checks
all ten routes from the exact Coder IQ1_M service activation at layer 0,
position 2, token ID 3. It is functional and numerical evidence, not a
throughput or task-quality benchmark.

## Ownership and numerical result

The request used token IDs `1,2,3`, a static profile, and a runtime cache with
391 loaded slots. The routed IDs were `143,175,252,25,54,240,35,204,19,246`.
Four rows were primary GPU/foresight owned (experts 25, 54, 35, 19); six were
CPU owned (143, 175, 252, 240, 204, 246). The owner map was the same for
Strata and strict NInfer. No route was PCIe or peer owned.

For the four GPU-owned rows, Strata's service output matched the native CUDA
oracle bit-for-bit. NInfer's output differed from Strata/native CUDA by
relative L2 `7.64e-8`–`9.16e-8`. For all six CPU-owned rows, Strata and NInfer
service outputs matched bit-for-bit; the CPU outputs differ from the native
CUDA oracle by relative L2 `0.79%`–`1.21%`, which reflects comparing different
execution owners and is not an NInfer kernel discrepancy. Against an FP64
full-projection reference, both service paths have median relative L2 about
`1.15%` (range about `1.05%`–`1.24%`). That reference uses unquantized
activation/intermediates and is descriptive; it does not define an acceptance
threshold.

The generic layer-0 NInfer resident-dispatch log does not mean all ten selected
rows used NInfer. This exact service row had four GPU-owned rows and six CPU
rows. A follow-up forced `--pcie-frac 1.0`, but the active `--mmap-experts`
source had no pinned device complement: the six misses remained CPU owned, as
confirmed by the owner trace and CPU-output capture. See the [PCIe-share
follow-up](pcie-frac-1/README.md).

## Reproduction and evidence

The oracle used the exact captured service activation and GGUF expert weights,
GGML weight dequantization, the native CUDA grouped expert oracle, and an FP64
full projection. The machine-readable comparison includes row-level IDs,
profile ranks, owners, hashes and numerical summaries. Raw activation/weight
captures and temporary dequantized files are not included in Git. The owner and
oracle runs passed the memory supervisor; their records are
[`owner-supervisor.json`](owner-supervisor.json) and
[`oracle-supervisor.json`](oracle-supervisor.json). This is a single token at a
single layer and does not close mixed-codec state parity or task-quality gates.
