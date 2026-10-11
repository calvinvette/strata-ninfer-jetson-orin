# Q2_0 spec4 graph-owner and NVMap check at 32K configured context — Orin — 2026-10-11

This adds a Q2_0 graph-memory point at `--max-context 32768` with `--spec 4`,
matched to the existing 256-slot cache, 512-token prefill setting, artifacts and
six-GiB supervisor used by the context32k/spec2 check. The request itself was
31 prompt tokens and 24 generated tokens; this is configured-context startup
accounting, not a 32K ingestion, quality or capacity test.

The first request passed. The six-GiB physical-availability supervisor recorded
22,507,008,000 bytes (20.96 GiB) minimum `MemAvailable`. The owner trace balanced
302 allocations and frees, with zero requested live bytes at log end. Its
successful graph events were two `verifier` instantiations and one
`verifier-commit-graph`. The independent Driver wrapper also observed three
successful `cudaGraphInstantiate` calls; all three timestamps aligned with the
owner events.

For the engine PID, 20 consecutive 100 ms NVMap samples immediately before the
first graph call were stable at 6,005,686,272 bytes. Twenty samples after the
last successful call were stable at 6,054,395,904 bytes. The stable-to-stable
increase was 48,709,632 bytes (46.45 MiB) across the capture/instantiate
interval and adjacent synchronous allocations. It is not an isolated graph
executable size. At this setting, the observed session owner requested
991,516,160 bytes (945.1 MiB), the expert cache 353,894,400 bytes, the verifier
57,658,880 bytes, and verifier mapped-host backing 742,976 bytes; these are
separate requested-owner counters, not a combined physical-memory total.

This fills the 32K-configured/spec4 graph-attribution cell. The corresponding
32K/spec2 report observed four successful calls and a 72,425,472-byte NVMap
interval, while the earlier 4K/spec4 report observed three calls and a
48,709,632-byte interval. The call sequences differ, so these deltas cannot be
divided into per-graph costs or attributed to context alone. Legacy session
graphs, other graph pools and non-NVMap allocations remain unpriced.

The model request stayed loopback-only. Q2_0 shards and prepared packs remain in
`~/models/strata-orin-validation/`; exact artifact identities are retained in
`artifact-identities.json`. `run_graph_probe.py` and `server-config.json` record
the invocation. `nvmap-clients.jsonl`, `nvmap-analysis.json`, `engine.log.txt`,
`owner-summary.json`, and `supervisor/` retain raw observations and analysis.
