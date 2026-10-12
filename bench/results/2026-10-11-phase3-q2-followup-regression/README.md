# Current Q2_0 Phase 3 follow-up regression — Orin — 2026-10-11

The current candidate reran the artifact-aware Q2_0 PLE parity test and a
focused Phase 3 memory/owner regression after the latest cancellation and
staging evidence. The serial CTest selection passed 19/19, including
`ple_parity`, shared-memory budget arithmetic, cache allocation/refusal,
conversation reservations and snapshots, VMM, graph tracing, and state/cache
ownership checks. Integration Python unittest discovery passed 106/106.

The tested `strata` binary SHA256 is
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`; the
`ple_parity` binary SHA256 is
`021239e6fa46ba81b1d1c011b10a71a6386ae420d14cc25cc496a8558efaed30`.
CTest ran serially from `build/integration/candidate`; Python used
`python -m unittest discover -s tools/integration -p 'test_*.py'`.

This was a software regression run without a physical-memory supervisor or
model-serving request, so it makes no new pressure, capacity, or performance
claim. The prior [Q2_0 admission screen](../2026-10-11-phase3-q2-admission/README.md)
and [18-second cancellation/recovery screen](../2026-10-11-phase3-q2-cancel-prefill128-recovery18s3/README.md)
remain separate measured evidence. Phase 3 remains open for broader physical
backing, pressure, graph-pool, and transfer/admission coverage.
