# Q2_0 spec4 graph-owner trace at 64K context — Orin — 2026-10-13

Three fresh Q2_0 serving processes repeated the same supported short graph
request (31 formatted prompt tokens, 24 generated tokens) at a 65,536-token
configured context, 3,000 expert-cache slots and CLI speculation 4. All three
requests passed and returned the same text. Each process instantiated two
verifier graphs and the commit graph. The model artifacts remained in
`~/models/strata-orin-validation/`.

The root-readable NVMap IOVMM client table was sampled at a requested 2-ms
interval. Actual median intervals were 2.463–2.481 ms, with occasional gaps up
to 22.4 ms. The three-process campaign ran in a 28-GiB systemd scope with the
six-GiB admission floor. Minimum host availability was 16.31 GiB and effective
headroom was 16.31 GiB; OOM counters stayed zero. No clock controls were
changed; EMC clock readback was unavailable.

The first verifier event had 20-ms event-centered NVMap process-owner deltas
of 6,291,456, 6,356,992 and 8,454,144 bytes. The second event was exactly
22,896,640 bytes in all three processes. No instrumented ordinary device
allocation/free events fell within these windows. That second-event bracket is
close to the 23,117,824-byte spec2 result at the same 64K context. The count of
successful verifier graph instantiations differed (two at spec4, three at
spec2), and the 20-ms brackets remain owner-counter changes, not isolated
graph-pool bytes; adjacent runtime/driver and unwrapped allocations may
contribute. The native graph-disabled control is still unsupported, so this
trace does not close graph-memory qualification.

[`analyze.py`](analyze.py) aligns graph events and NVMap samples and compares
the later verifier event with the [64K spec2 trace](../2026-10-13-phase3-q2-graph-fine-nvmap-context64k/README.md).
[`analysis.json`](analysis.json), per-process results/configurations, all three
NVMap samples, and supervisor evidence are retained. Engine logs are ignored by
Git and their SHA256 identities are in [`ENGINE_LOG_SHA256.txt`](ENGINE_LOG_SHA256.txt).
[`SHA256SUMS.txt`](SHA256SUMS.txt) verifies committed files. Energy was not
measured.
