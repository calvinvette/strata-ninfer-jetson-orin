# Q2_0 32K prompt at 64K context, 20-GiB scope, 5,000 slots, prefill 256 — Orin — 2026-10-12

This is the 256-token prefill-chunk point in a fixed 20-GiB cgroup scope, paired for configuration with the [prefill-512 run](../2026-10-12-phase3-q2-actual32k-context64k-20G-cache5000/README.md). Both used the same exact 32,768-token prompt, 65,536-token configured context, 5,000 requested expert-cache slots, 3,072 MiB workspace reserve, model and PLE artifacts, and two-token speculation window. The Q2_0 artifacts remain in `~/models/`.

The 256-token run passed all prompt positions and generated token ID 32. It stayed above the six-GiB supervisor floor with 8.65 GiB minimum effective cgroup availability and 14.00 GiB minimum host availability; no cgroup OOM or OOM-kill events occurred. The same prompt and output token do not imply same numerical state: final persistent fingerprints and all 36 GDN per-layer hashes differ from the 512-token run, consistent with the previously measured chunk-dependent state drift. No independent quality oracle was run here, so neither chunk's state is designated more accurate.

| Measure | Prefill 256 | Prefill 512 control |
|---|---:|---:|
| Minimum host availability | 15,028,854,784 B (14.00 GiB) | 14,893,555,712 B (13.87 GiB) |
| Minimum effective cgroup availability | 9,286,901,760 B (8.65 GiB) | 10,067,988,480 B (9.38 GiB) |
| Unique requested device peak | 10,565,479,936 B (9.84 GiB) | 10,649,721,344 B (9.92 GiB) |
| Prefill owner's requested peak | 265,800,704 B (253.5 MiB) | 350,079,744 B (333.8 MiB) |
| Prompt-stage time | 250,101.6 ms | 164,134.2 ms |

The smaller chunk reduced the observed prefill-owner peak by 80.4 MiB and total unique requested device peak by 80.5 MiB. Effective cgroup availability was 0.73 GiB lower despite slightly higher host availability and slightly lower requested device peak; this demonstrates that these sequential scope/page-cache samples cannot attribute physical-memory differences to chunk size. Prompt-stage times are descriptive sequential observations, not a paired performance estimate. No default or supported configuration changes.

Owner tracing reported 304 allocations and 303 frees, with only the 1,485,606,400-byte service-lifetime weight arena live at log end. Requested bytes exclude driver-private and graph-pool backing. Raw engine, cgroup/host samples, tegrastats, workload, and parsed owner ledger are retained. The executable SHA-256 is `bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.
