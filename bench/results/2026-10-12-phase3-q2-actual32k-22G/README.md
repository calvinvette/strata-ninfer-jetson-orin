# Q2_0 actual 32K prompt under 22-GiB cgroup cap — Orin — 2026-10-12

Two sequential cache-capacity runs ingested the same exact 32,768-token prompt
and generated one token under transient `MemoryMax=22G` scopes and the standard
six-GiB effective-headroom supervisor. Both passed without OOM kills. The
prompt SHA-256 was
`705dea47aafbfc991d0616621f3a13bf0136a43c546d60c7693c2efdced4d3a3`; both
arms emitted token ID 32. Context was set to 32,800, prefill chunk to 512,
MTP/speculation to two, prompt cache to six, and the explicit workspace
reserve remained 3,072 MiB. Models and packs remained in `~/models/`.

| Requested cache | Device cache owner peak (B) | Device requested peak (B) | Minimum effective cgroup availability | Minimum physical availability | Prompt time (descriptive) | File hits |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3,000 slots | 4,147,200,000 | 7,021,083,648 | 10,763,792,384 B (10.02 GiB) | 18,245,808,128 B (16.99 GiB) | 168,881.7 ms | 54/480 |
| 5,000 slots | 6,912,000,000 | 9,785,883,648 | 10,650,206,208 B (9.92 GiB) | 15,872,004,096 B (14.79 GiB) | 165,047.1 ms | 111/480 |

Each owner trace recorded 304 allocations and 303 frees. The 1,485,606,400-byte
weight arena was the only requested allocation live at log end; prefill,
session, verifier and pageable host staging owners returned to zero. Device
and host owner records are reported separately. These requested bytes are not
a complete physical memory ledger; graph-pool, driver-private and uninstrumented
allocations remain unpriced.

This is an admission/ownership comparison, not a timing result. The arms ran
sequentially, and their final persistent state differs: GDN, KV, tail, pooled,
and pooled-full hashes differ; 35 of 36 per-layer GDN hashes differ. Both
emitted the same token ID, but that does not establish state or quality parity.
This repeats the unresolved cross-cache state mismatch seen in the earlier
Q2_0 32K screen. Do not treat the prompt-time difference as a cache benefit.

The `supervisor/` directory retains the initial setup-only invocation with an
incorrect runner argument order; it did not start the model. The successful
5,000-slot run and its supervisor are retained in `retry-run/` and
`retry-supervisor/`; the successful 3,000-slot run is in `run-cache3000/` and
`cache3000-supervisor/`. The original command configuration is
`2026-10-12-phase3-q2-actual32k-22G-config.json`; the 3,000-slot variant is
`config-cache3000.json`. The executable SHA-256 is
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.

The 5,000-slot run took 190.76 seconds and the 3,000-slot run 198.25 seconds,
with dynamic CPU/GPU/EMC clocks. No paired timing, performance, quality or
cache-interchangeability claim is made. Energy was not measured.
