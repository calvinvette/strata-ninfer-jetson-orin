# Q2_0 resident expert kernel share diagnostic

Date: 2026-10-31. Device: Jetson AGX Orin Developer Kit (aarch64, SM87,
CUDA 12.6). Nsight Systems 2024.5.4 profiled one warmup and one measured
NIMBUS retrieval request per backend, each with a 512-token prompt and 32-token
cap. Both used the same 4K cache and 8K service profile; the NInfer arm was
strict. The exact requested answer prefix passed in all four requests.

The first graph-level trace hid CUDA graph node kernels and is excluded. The
second collection used `--cuda-graph-trace=node`, which exposed the resident
expert kernels. Tracing nodes adds substantial overhead, so none of the
profiled request times are performance measurements. Each process trace
contains both the warmup and measured requests.

## GPU kernel inventory

| Kernel activity | Strata summed duration | Strict NInfer summed duration |
| --- | ---: | ---: |
| All CUDA kernel events | 32.039 s | 30.250 s |
| `wait_flag_ge_kernel` | 8.781 s | 8.156 s |
| Dequant helper type 11 | 3.649 s | 3.431 s |
| Dequant helper type 23 | 2.518 s | 2.379 s |
| Dequant helper type 12 | 1.211 s | 1.142 s |
| `mul_mat_q` type 42 | 6.450 s | 6.117 s |
| NInfer grouped D3 | — | 132.1 ms (6,144 launches) |
| NInfer grouped D4 | — | 132.1 ms (6,144 launches) |
| NInfer grouped SwiGLU quantization | — | 22.9 ms (6,144 launches) |

The three identified NInfer kernels sum to 287.1 ms, or 0.95% of all CUDA
kernel-event duration summed in the NInfer trace. This is **not** 0.95% of
request wall time: kernel events can overlap, and this aggregate covers both
the warmup and measured request. The Strata trace's type-42 matmul events are
not isolated into dense and resident-expert contributions by this profile.

The trace supports a narrow explanation for the weak end-to-end result: even
though the isolated grouped operator can be faster, these identifiable NInfer
expert kernels are a small part of the total GPU kernel activity for this
short service workload, while wait-flag, dequantization and other work remains.
It does not establish a causal wall-time budget or the same kernel share for
longer prompts, other output lengths, cache maps or models. See
[`kernel-summary.json`](kernel-summary.json) for exact sums, binary/source
identity, request qualification, and limitations. The 17 MiB raw traces remain
under `/tmp/e6-nsys-node-4k-tg128/` and are not committed.
