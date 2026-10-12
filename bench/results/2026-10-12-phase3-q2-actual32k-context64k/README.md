# Q2_0 32K prompt at 64K context reservation — Orin — 2026-10-12

This extends the cache/context admission screen with the same exact 32,768-token prompt under a 65,536-token configured context at 3,000 and 5,000 requested cache slots. Each independent process ran under a transient 22-GiB `MemoryMax` scope and the standard six-GiB effective-headroom supervisor. Models and packs remain in `~/models/`. The PLE pack, model revision and expert profile are the same artifacts listed in the [Q2_0 identity record](../2026-10-11-phase3-q2-admission/artifact-identities.json); the prompt SHA-256 is `705dea47aafbfc991d0616621f3a13bf0136a43c546d60c7693c2efdced4d3a3`.

Both cells completed all 32,768 prompt tokens and generated token ID 32 with no cgroup OOM kills. The explicit 3,072 MiB workspace reserve, prefill chunk 512, MTP/speculation window 2, and prompt cache 6 were used. The runner disabled CPU prefill sharing and stage pinning and enabled state and owner tracing. Exact arguments are retained in each `workload.json`.

| Requested cache | Minimum host availability | Minimum effective cgroup headroom | Requested device peak | Prompt-stage time | File-cache hits |
|---:|---:|---:|---:|---:|---:|
| 3,000 slots | 16.43 GiB | 7.47 GiB | 7,884,921,344 B (7.34 GiB) | 173,319.4 ms | 54/480 |
| 5,000 slots | 13.89 GiB | 9.68 GiB | 10,649,721,344 B (9.92 GiB) | 166,051.2 ms | 111/480 |

Both owner ledgers recorded 304 allocations and 303 frees, with only the 1,485,606,400-byte service-lifetime weight arena left live at log end. These requested owner bytes do not include every driver-private or graph-pool allocation. The higher effective cgroup headroom in the 5,000-slot run does not mean that cache is more memory-efficient: host availability fell by 2.53 GiB, and sequential file-cache and cgroup accounting differ between runs.

The two runs emitted the same token ID and used the same prompt, but their final persistent fingerprints differed in GDN, tail, pooled, KV, and pooled-full state; 35 of 37 recorded GDN hashes (global plus per-layer records) differed. No timing or quality comparison is claimed. The 3,000-slot point passed only 1.47 GiB above the supervisor floor, so it is a narrow admitted cell, not a general supported-capacity limit.

[`state-comparison.json`](state-comparison.json) contains both workload, memory and owner summaries. Each `cache*-supervisor/` retains host/cgroup/clock telemetry; each `cache*-run/` contains the engine log, token/prompt data and parsed owner ledger. The reproduction runner and per-cache configs are included. This adds one context-reservation × actual-long-prompt interaction point; broader capacity and quality qualification remain open.
