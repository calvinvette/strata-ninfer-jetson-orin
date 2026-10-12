# Q2_0 graph-owner trace at 64K context — Orin — 2026-10-13

Three fresh Q2_0 serving processes repeated the supported short graph request
(31 formatted prompt tokens and 24 generated tokens) with a 65,536-token
configured context, 3,000 expert-cache slots and CLI speculation 2. The model
files stayed under `~/models/strata-orin-validation/`. Each request passed,
returned the same text, and recorded three verifier graph instantiations and
one commit-graph instantiation.

The root-readable NVMap IOVMM client table was sampled at a requested 2-ms
interval. Actual median intervals were 2.469–2.478 ms, with occasional gaps up
to 22.6 ms. The full three-process campaign ran under one systemd scope capped
at 28 GiB, with the six-GiB admission floor. Minimum host availability was
16.39 GiB and minimum effective headroom was 13.22 GiB; OOM and OOM-kill
counters remained zero. No clock controls were changed; EMC readback was
unavailable.

At the second verifier-graph event, the 20-ms event-centered process-owner
delta was exactly 23,117,824 bytes in all three runs, matching the 8,232-token
context result. At the third verifier event, the 64K-context deltas were
6,356,992, 8,454,144 and 22,831,104 bytes; the 8,232-context result was
22,831,104 bytes in all three runs. No instrumented ordinary device
allocation/free events occurred within those windows. The variation prevents a
stable context-based graph-memory estimate. These are NVMap owner brackets,
not isolated executable or pool bytes; adjacent runtime/driver activity and
unwrapped private allocations remain possible. The equivalent graph-disabled
native control remains unsupported, so this does not close graph-memory
qualification.

[`analyze.py`](analyze.py) aligns graph events with NVMap samples and compares
the 64K results to the existing [8,232-context trace](../2026-10-13-phase3-q2-graph-fine-nvmap/README.md).
[`analysis.json`](analysis.json), each request/result/configuration, all three
NVMap samples, supervisor telemetry and command records are retained. Per-run
engine logs are ignored by Git and their SHA256 identities are in
[`ENGINE_LOG_SHA256.txt`](ENGINE_LOG_SHA256.txt); [`SHA256SUMS.txt`](SHA256SUMS.txt)
verifies committed files. No energy measurement was made.
