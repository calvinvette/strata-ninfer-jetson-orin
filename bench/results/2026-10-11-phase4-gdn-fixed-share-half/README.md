# Fixed 0.5 CPU prefill-share diagnostic at a 5,000-slot request — Orin — 2026-10-11

Three independent eight-worker IQ1_M Coder runs used the same 512-token/eight-
output workload and fixed `STRATA_PREFILL_CPU_SHARE=0.5`. The requested
expert-cache setting was 5,000, but actual admission varied: 6,519, 6,088 and
6,519 slots. Output text hashes matched; accepted-prefix state fingerprints and
commit state did not match across processes. The screening harness therefore
returned failure and correctly withheld paired timings because actual cache
capacity and persistent state were not held constant.

All three API requests themselves completed. The six-GiB supervisor retained
the run, with 8.11 GiB minimum host availability. This is a failed comparison
cell caused by unequal admitted cache size and state drift, not evidence of an
engine crash, memory-floor breach or performance effect. The later matched
3,903-slot three-process comparison is documented in the
[fixed-share cache-3000 control](../2026-10-11-phase4-gdn-fixed-share-half-cache3000/README.md).
