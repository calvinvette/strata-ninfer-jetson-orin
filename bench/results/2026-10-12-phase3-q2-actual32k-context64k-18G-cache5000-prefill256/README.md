# Q2_0 32K prompt at 64K context, 18-GiB scope, 5,000 slots, prefill 256 — Orin — 2026-10-12

This repeats the [20-GiB prefill-256 cell](../2026-10-12-phase3-q2-actual32k-context64k-20G-cache5000-prefill256/README.md) at an 18-GiB transient cgroup `MemoryMax`, retaining the standard six-GiB effective-headroom supervisor. Model and PLE artifacts remain in `~/models/`. The prompt, cache size, context, prefill chunk, speculation window, workspace reserve and executable were unchanged.

The full 32,768-token prompt completed and generated token ID 32. Minimum effective cgroup availability was 6,971,543,552 B (6.49 GiB), only 527,593,408 B (0.49 GiB) above the supervisor floor. Minimum host `MemAvailable` was 14,877,433,856 B (13.86 GiB). There were no cgroup OOM or OOM-kill events. This is a narrow pass for this exact configuration, not a supported general memory limit.

The final persistent fingerprint and all 36 per-layer GDN hashes exactly match the 20-GiB / prefill-256 control. Owner tracing recorded 304 allocations and 303 frees, with only the 1,485,606,400-byte service-lifetime weight arena live at log end. Requested device peak was 10,565,479,936 B (9.84 GiB); it is not total physical or driver-private backing. No timing comparison is claimed.

The previous 18-GiB / 3,000-slot / prefill-512 cell safely aborted at the six-GiB guard, while this 5,000-slot / prefill-256 cell passed narrowly. The runs differ in both cache and chunk and in cgroup/page-cache charging; this does not isolate either factor or establish monotonic capacity behavior. Preserve the raw supervisor samples, engine log, workload and owner summary for any future paired design.
