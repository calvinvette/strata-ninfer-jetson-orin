# Adaptive swap byte verification — Orin — 2026-10-14

This diagnostic checks whether adaptive refills leave the expected expert bytes
in each GPU cache slot. The opt-in `STRATA_VERIFY_ADAPT_SWAPS=1` hook waits for
the copy-completion events, copies each incoming slot back to host memory, and
compares it byte-for-byte with the stable source blob before releasing that
source. A mismatch prints the layer, expert and slot and aborts the diagnostic
run. The default path does not perform these reads or comparisons.

The rebuilt Orin CUDA service completed the same accepted-only IQ1_M
short→long→short sequence used in the recovery regression: 512, 2,048 and 512
prompt tokens, 16 generated tokens, MTP off and MTP4 in separate services,
3,903 cache slots and adaptation every four accepted tokens. At each apply
point, 96 incoming blobs were verified. Each arm had 11 verification points
and 1,017 blobs checked; no byte mismatch occurred. Both arms still reproduced
the within-service short-answer and persistent-state recovery drift. MTP0 and
MTP4 remained equal request-by-request. Thus the recorded refill bytes were
correct, while the recovery signal persisted after the residency changes.
This does not identify which arithmetic or state-computation route causes the
drift.

The supervisor reported 13.29 GiB minimum host availability and 13.19 GiB
minimum admission availability. Across 364 samples, cgroup `high`, `max`,
`oom` and `oom_kill` event deltas stayed zero. The 28-GiB memory ceiling and
six-GiB physical-headroom floor were respected. The run took 383.6 seconds.

The CUDA build completed on Orin. The changed `generate.cpp` also compiled and
linked into the `strata` service on maestro1 using the pinned HIP toolchain;
`native_expert_parity` remained built, and the HIP service `--help` check
passed. This is x86 compile/link evidence only, not HIP device-runtime
qualification. SYCL uses a separate generation source and is unaffected by
this file change.

The instrumented Orin service binary hash is in `binary-sha256.txt`. Raw
requests, service logs, memory samples, supervisor result, backend build log,
help output and hashes are retained here. The harness reports failure because
the expected before/after recovery equality assertion still fails; all six
requests completed and the failure is the known numerical/state regression,
not a swap-byte or memory failure.
