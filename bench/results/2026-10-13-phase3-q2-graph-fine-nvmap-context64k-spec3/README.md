# Q2_0 spec3 graph-owner trace at 64K context — Orin — 2026-10-13

Three fresh Q2_0 serving processes ran the same supported short request
(31 formatted prompt tokens and 24 generated tokens) with a 65,536-token
configured context, 3,000 expert-cache slots and CLI speculation 3. All
requests passed with identical text. Each process instantiated three verifier
graphs and one commit graph. Model files remained under ~/models/strata-orin-validation/.

The root-readable NVMap IOVMM client table was sampled at a requested 2-ms
interval. Actual median intervals were 2.475–2.487 ms, with occasional gaps
up to 24.7 ms. The campaign ran under a 28-GiB systemd cap and the six-GiB
admission floor. Minimum host availability was 16.22 GiB and effective
headroom 16.22 GiB; OOM counters remained zero. No clock controls were changed;
EMC clock readback was unavailable.

The second verifier event had an identical 23,781,376-byte 20-ms event-centered
NVMap process-owner delta in all three runs. The third event was also identical
at 22,831,104 bytes. No instrumented ordinary device allocation/free events
fell within these windows. The second-event bracket is close to spec2
(23,117,824 bytes) and spec4 (22,896,640 bytes) at the same context. The
third-event bracket contrasts with spec2's variable 6.36–22.83 MB range. These
are NVMap owner-counter brackets, not isolated graph-pool bytes; adjacent and
unwrapped runtime/driver activity remain possible. A graph-disabled native
control is unsupported, so graph-memory qualification remains open.

The analyze.py tool aligns the events and compares spec2 at the same context.
analysis.json, per-process results/configurations, NVMap samples and supervisor
records are retained. Engine logs are ignored by Git and their hashes are in
ENGINE_LOG_SHA256.txt. SHA256SUMS.txt verifies committed files. Energy was not
measured.
