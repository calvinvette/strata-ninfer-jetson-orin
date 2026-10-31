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

## Timeline-union follow-up

The retained Nsight SQLite exports were also reduced to the union of CUDA
kernel intervals. In the NInfer trace, summed kernel duration was 30.250 s and
the union of active intervals was 30.145 s; overlap therefore accounts for
105.1 ms (0.35% of summed duration). In the Strata trace, the corresponding
values were 32.039 s and 31.936 s, with 103.3 ms overlap. The NInfer D3, D4
and SwiGLU intervals do not overlap one another and total 287.1 ms, which is
0.95% of summed duration and 0.95% of the NInfer trace's GPU-active interval
union. This makes the small share robust to correcting for kernel overlap.

This is a share of observed GPU-active time over the warmup and measured
request, not a share of API wall time or an end-to-end speedup ceiling. CPU/GPU
overlap, profiler overhead, unclassified work, and the inability to split
Strata type-42 matrix operations by dense versus expert role remain. Eliminating
the identified NInfer kernels could recover at most their observed 287 ms from
this trace's GPU activity; request-level effect still requires unprofiled
paired measurements. The derivation is reproducible with
[`analyze_kernel_union.py`](analyze_kernel_union.py) against the SQLite exports
under `/tmp/e6-nsys-node-4k-tg128/`.

The trace supports a narrow explanation for the weak end-to-end result: even
though the isolated grouped operator can be faster, these identifiable NInfer
expert kernels are a small part of the GPU-active timeline for this short
service workload, while wait-flag, dequantization and other work remains. It
does not establish a request wall-time budget or the same kernel share for
longer prompts, other output lengths, cache maps or models. See
[`kernel-summary.json`](kernel-summary.json) for exact sums, binary/source
identity, request qualification, and limitations. The 17 MiB raw traces remain
under `/tmp/e6-nsys-node-4k-tg128/` and are not committed.
