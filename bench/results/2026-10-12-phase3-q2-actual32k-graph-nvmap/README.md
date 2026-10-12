# Q2_0 actual 32K prompt graph interval — NVMap trace — Orin — 2026-10-12

Three independent processes sampled the Tegra NVMap IOVMM client table while the exact 32,768-token Q2_0 prompt ran at 65,536-token configured context, 5,000 expert-cache slots, prefill 512, speculation window 2, and the existing 3,072 MiB workspace reserve. Each used a transient 20-GiB cgroup scope and the standard six-GiB supervisor. Model files remained under `~/models/`.

Every request passed and generated token ID 32. All three final persistent fingerprints and all 36 per-layer GDN hashes matched. Each owner trace recorded four successful runtime graph instantiations (three verifier windows and one commit graph), matched by four owner events. The owner ledgers each recorded 304 allocations and 303 frees, with only the 1,485,606,400-byte service-lifetime weight arena live at log end.

| Run | Minimum host availability | Minimum effective cgroup headroom | NVMap bytes before first graph | NVMap bytes after fourth graph | Interval increase |
|---|---:|---:|---:|---:|---:|
| 1 | 13.84 GiB | 8.08 GiB | 13,454,663,680 | 13,526,646,784 | 71,983,104 B |
| 2 | 13.86 GiB | 8.49 GiB | 13,454,663,680 | 13,526,646,784 | 71,983,104 B |
| 3 | 13.81 GiB | 8.55 GiB | 13,454,663,680 | 13,526,646,784 | 71,983,104 B |

The repeated 71,983,104-byte (68.65 MiB) process-owned increase brackets the initial verifier-graph interval during this actual long-prompt request. It includes adjacent synchronous allocations. It is not an isolated graph executable size, a graph-disabled differential, or total physical memory. These three processes strengthen the evidence for this exact model/configuration but do not price other graph paths; non-NVMap and driver-private backing remain unmeasured. No timing, energy, or default-change claim is made.

Each `repeat-*/` directory retains its config, raw NVMap samples, engine log, workload, owner summary, and supervisor telemetry. The executable SHA-256 is `bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.
