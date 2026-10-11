# Q2_0 decode cancellation/recovery with a 20 GiB cgroup cap — Orin — 2026-10-11

The same Q2_0 streamed decode-disconnect and same-process recovery workload as
the 22 GiB follow-up passed under a 20 GiB `MemoryMax` scope. The client saw
text, closed the stream during decode, and the service returned exactly
`Hello Orin!` on the following request. All 302 traced allocation/free pairs
balanced. Minimum physical `MemAvailable` was 21.45 GiB; the minimum effective
availability was 16.30 GiB.

The cap was not approached in this run: peak scope usage was 3.70 GiB, leaving
16.30 GiB effective cgroup capacity. This is an admitted capped control, not a
pressure result. The separate [22 GiB run](../2026-10-11-phase3-q2-decode-cancel-22G/README.md)
encountered higher effective cgroup usage and is the pressure-relevant decode
cancellation result. The same Q2_0 artifacts and candidate binary were used;
the model files remain under `~/models/strata-orin-validation/`.
