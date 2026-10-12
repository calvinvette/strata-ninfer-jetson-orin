# Q2_0 graph backing at 64K context, compared with 32K — Orin — 2026-10-12

Three 64K-context and three 32K-context Q2_0 spec4 service startups ran on the same day, with the same candidate binary, model revision, 256-slot cache, 512 prefill setting, 31-token API prompt, and 24-token response. Each request passed under the six-GiB supervisor. The minimum host availability across all six runs was 19.36 GiB. Each process produced three successful runtime graph-instantiation calls matched by three integration owner events.

For each context, NVMap IOVMM client samples formed stable plateaus before and after capture. The graph interval increased by exactly 48,709,632 bytes in every process: 20 or 21 stable samples before the first graph event, then at least 371 stable samples after the final event. The measured interval includes graph capture/instantiation and adjacent synchronous device allocations; it is not an isolated executable size.

| Configured context | Stable pre-graph NVMap | Stable post-graph NVMap | Interval increase | Session owner peak | Verifier owner peak |
|---:|---:|---:|---:|---:|---:|
| 32,768 | 6,005,686,272 B | 6,054,395,904 B | 48,709,632 B | 991,516,160 B | 57,658,880 B |
| 65,536 | 6,870,433,792 B | 6,919,143,424 B | 48,709,632 B | 1,856,067,072 B | 57,855,488 B |

Doubling configured context increased the pre-graph NVMap plateau and device requested-allocation peak by the same 864,747,520 bytes. The instrumented session owner increased by 864,550,912 bytes and the verifier owner by 196,608 bytes; those owner deltas sum exactly to the observed NVMap delta. This attributes the context-related backing change to those measured owners for this setup. It does not price other graph shapes or non-NVMap allocations.

The request latency varied between startups and is descriptive only: graph capture and NVMap sampling were enabled, clocks were dynamic, and no timing comparison or energy claim is made. One initial 64K harness invocation failed before server startup because the script looked for its config in the wrong directory; it remains under `repeat1/supervisor/`. The corrected successful run is under `repeat1/supervisor-retry/`.

[`context-comparison.json`](context-comparison.json) contains the six samples' summaries and exact deltas. The 64K-context runs and their configurations, owner summaries, NVMap traces and supervisor telemetry are in this directory. The same-day 32K controls and their raw data are in [`../2026-10-12-phase3-q2-graph-context32k-spec4/`](../2026-10-12-phase3-q2-graph-context32k-spec4/). Model checksums and revision are retained in the referenced [Q2_0 artifact record](../2026-10-11-phase3-q2-graph-context32k-spec4-confirm3/artifact-identities.json); model files remain in `~/models/`.
