# Q2_0 fine NVMap sampling around graph instantiation — Orin — 2026-10-13

Three fresh Q2_0 service processes repeated the supported short request used
for the earlier captured-graph owner checks: 31 prompt tokens, 24 generated
tokens, 3,000 expert-cache slots, CLI speculation 2, and an 8,232-token
configured context. The model and PLE files stayed under `~/models/`; their
shard identities are recorded in the [held-out transfer report](../2026-10-13-phase3-q2-mapped-pread-16k-heldout/README.md).
Each request passed with the same completion text. Each process recorded three
verifier graph instantiations and one commit-graph instantiation.

The root-readable NVMap IOVMM client table was sampled at a requested 2-ms
interval. Actual median sample intervals were 2.471–2.477 ms, with occasional
longer gaps. The independent 28-GiB systemd supervisors retained the six-GiB
floor, measured 17.85–17.87 GiB minimum host/effective headroom, and recorded
zero OOM events.

At the two later verifier-graph events, the NVMap process-owner counter rose by
exactly 23,117,824 bytes and 22,831,104 bytes in all three runs, respectively,
within a 20-ms event-centered bracket (samples at least 10 ms before and after
the graph event). No instrumented ordinary device allocation/free event was
logged in those windows. Immediate nearest-sample deltas were smaller and
varied by sample phase, from zero to about 2.1 MB. The first verifier and
commit-graph events are only 7.5 ms apart, so their 20-ms brackets overlap and
cannot be separated this way. These repeatable event-aligned changes narrow
the prior coarse 71,983,104-byte interval, but remain platform-owner brackets;
they do not prove isolated executable or graph-pool size, and uninstrumented
driver/runtime allocations may fall in the same windows. The native route still
does not support an equivalent graph-disabled control, so Phase 3 graph-memory
qualification remains open.

[`analyze.py`](analyze.py) aligns graph events, NVMap samples, owner traces and
supervisor memory records. [`analysis.json`](analysis.json) and all three raw
sample sets are retained here. The initial probe attempt stopped on a Python
indentation error before starting a model process; that harness failure is
preserved under `supervisor/`. The corrected run and two repeats passed under
`supervisor-retry/` and each `repeat-*/supervisor/`. No clock controls were
changed; energy was not measured.
