# Delayed-control versus adaptive prompt-tail trace — Orin — 2026-10-20

This randomized pair used the same current binary (`c374cf6d5b6b3b416d16e49b0c5e1a7ea351dee6c69d23d2eff19685cd1db2d0`), Coder IQ1_M model shards, 512→2,048→512 request sequence, and positions 505 and 506 as the parent trace. The delayed arm used cadence 100,000/cap 96; the adaptive arm used cadence 4/cap 8. Each arm ran in its own service under a 28 GiB supervisor. No continuation request was added, so the capture contains one initial and one recovery row per selected position and layer.

The [campaign record](campaign.json) passed in randomized order, delayed-control then adaptive-cap8. Delayed-control took 185.6 seconds and retained 14.27 GiB minimum host/admission availability. Adaptive took 181.2 seconds and retained 14.19 GiB. Both arms had zero cgroup memory events. The adaptive arm passed 11 swap-byte and 11 residency-table checks.

| Arm | Position | First owner difference | First activation difference | First expert-ID difference | Layer-26 activation differences |
| --- | ---: | ---: | ---: | ---: | ---: |
| Delayed control | 505 | none | none | none | 0/2,560 |
| Delayed control | 506 | none | none | none | 0/2,560 |
| Adaptive cap 8 | 505 | 1 | 26 | 27 | 2,560/2,560; max abs 0.00978; relative L2 0.00482 |
| Adaptive cap 8 | 506 | 1 | 26 | 31 | 2,560/2,560; max abs 0.00260; relative L2 0.00105 |

The delayed arm also returned the same 16 generated token IDs and matched all
recorded terminal state fingerprints after recovery. The adaptive arm returned
the same 16 token IDs but differed in GDN, tail, pooled, full-pooled and KV
state fingerprints. This matched the earlier result: text parity alone did not
mean persistent-state parity.

Thus the captured layer-26 delta reproduces in the adaptive arm and is absent
in the tested delayed-control pair. The result supports an association with
the adaptive configuration in this workload; it does not isolate which
adaptive operation or earlier accepted-state transition causes the difference.
The trace is a correctness diagnostic, not a quality or performance comparison.

`delayed-control/dispatch-analysis.json` and `adaptive-cap8/dispatch-analysis.json`
compare the initial and recovery route records within each arm. Raw dispatch
rows and supervisor memory/clock samples are retained under each arm directory.
The comparison used the IQ1_M shards from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, located outside Git in
`~/models/strata-orin-validation/Coder-GGUF/IQ1_M/`.

Phase 5 remains open.
