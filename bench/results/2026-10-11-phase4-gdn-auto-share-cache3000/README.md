# Default CPU prefill-share repeatability check — Orin — 2026-10-11

This three-process diagnostic repeats the 512-token/eight-output IQ1_M
accepted-prefix workload with eight expert-pool workers, MTP enabled, and the
runtime's default automatic CPU/GPU prefill-sharing policy. The fixed requested
expert-cache budget was 3,000 slots; all runs admitted 3,903 slots. Each process
used a distinct 512-token warmup, then captured per-commit token IDs and full
persistent-state fingerprints. The six-GiB `MemAvailable` supervisor passed
its floor in all runs; its minimum sample was 14,251,544,576 bytes (13.27 GiB).

All three requests completed eight tokens with identical output SHA256
`2ed88de1bf58d540c8b5b14e8089f461c8cad3ad16050b2af4a599a4d914900e`, and the
accepted token IDs were identical at all five verifier boundaries. However,
the accepted-prefix state hashes differed across all three processes, starting
at the first recorded committed boundary (`position=511`, `L=512`) and continuing
through the final boundary. The harness correctly marked both measured-state
and accepted-prefix parity false. This reproduces state drift under the default
automatic policy even though generated tokens happen to match for this short
workload.

At the same 3,903 actual slots and worker count, the matched
[fixed 0.5-share run](../2026-10-11-phase4-gdn-fixed-share-half-cache3000/README.md)
and [share-disabled run](../2026-10-11-phase4-gdn-no-share-cache3000/README.md)
each matched all state and accepted-prefix hashes across three processes.
Their final committed states differ from one another in GDN, PLE, tail, dead,
pooled, pooled-full, KV, MTP and stale-state fields. Thus the three policies provide evidence
of policy-dependent recurrent state; this test does not identify which state is
more accurate or establish answer quality. The earlier fixed-share attempt at
a 5,000-slot budget is excluded because actual cache capacity varied between
its processes.

Prompt/decode timings are retained in `experiment/results.json` but are not
interpreted: state tracing synchronizes and copies state, and the automatic
policy failed the required state-repeatability gate. No prefill-sharing default
is changed. The raw experiment result, base configuration, supervisor result
and sampled memory trace are retained here. Model artifacts remain under
`~/models`; checksums and engine identity are included in the run metadata.
