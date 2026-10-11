# MTP weight ownership follow-up — Orin — 2026-10-10

The opt-in owner trace previously reported MTP's logical payload snapshot but
omitted its model-weight backing from the unique-allocation ledger. The CUDA/HIP
implementation now records owned dense and routed-expert allocations, optional
Q4_0 projection copies, the draft-head subset and its vocabulary map. Frees are
recorded only after successful `cudaFree`; shared Drafter objects that borrow
the base weights emit no duplicate owner events. These diagnostics do not
change admission, allocation sizes, or runtime dispatch.

The updated ARM64 CUDA binary passed the existing Q2_0 one-token load/bind
admission cell with integration tracing under the six-GiB supervisor. It emitted
token ID 32; the one-token limit still leaves zero draft rounds. Minimum host
`MemAvailable` was 16,146,083,840 bytes (15.04 GiB).

The owner parser counted 266 allocations and 266 frees, with zero observed live
bytes at process exit. It attributed the following requested CUDA allocations
to the MTP loader:

| Owner | Requested bytes | Size |
| --- | ---: | ---: |
| Dense and routed-expert base blobs | 823,887,872 | 785.7 MiB |
| Draft vocabulary map and head subset | 187,511,436 | 178.8 MiB |
| MTP state/scratch arena peak | 12,977,872 | 12.4 MiB |

The dense blob was 116,099,072 bytes (110.7 MiB), the routed experts were
707,788,800 bytes (675 MiB), the draft vocabulary map was 425,196 bytes, and
the draft-head allocation was 187,086,240 bytes (178.4 MiB). These sums are
requested payload observations, not allocator backing or total physical memory.
The MTP logical payload snapshot remains 1,024,377,180 bytes and includes
objects outside these specific allocation records. CUDA graph/driver memory
remains unpriced.

The [raw supervised run](supervisor/result.json), integration records in
`supervisor/stderr.txt`, and [parsed owner accounting](owner-accounting.json)
are retained here. The model shards, pack, expert profile and MTP runtime remain
under `~/models/strata-orin-validation/`.

The modified implementation SHA256 is
`f7d43ed3b3082d02b13af5d7135b93dbbdfe30c3865c7397e687bed01bd26e05`; the
updated `MtpDrafter` header SHA256 is
`a2960ceea7ee0492f8e165cb9297f7cbf337281508a9dd7c3598f4f97b9c5790`. The
native CUDA `strata` binary SHA256 is
`1b2e01fbde747bf25f4527e38fc087a2a6f33468bf7b1e3f83aa6870109e2c15`. The root
CMake target compiles the CUDA version. The changed source and header were
copied to their exact paths in the isolated maestro1 validation checkout,
digests verified there, and the HIP `strata` executable rebuilt with one job.
Its binary SHA256 is
`2f0b046fc6e0c7744f385841b8d59564fba1a74152ece7836fd6c02fb461e6a8`; its
source hashes, compiler output and pass marker are retained under
[maestro1-hip](maestro1-hip/). The SYCL implementation has its own
`sycl/src/core/mtp.cpp` and header and is untouched. No HIP GPU runtime result
is claimed.
