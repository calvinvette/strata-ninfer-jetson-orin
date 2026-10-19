# IQ3_XXS/IQ4_NL-only service state diagnostic — Orin — 2026-10-19

The prior Q8_1 service pair set `STRATA_NATIVE_CPU_Q8_1_DOT=1`, which enabled
all supported CPU expert pairs. This follow-up uses the explicit selector
`STRATA_NATIVE_CPU_Q8_1_DOT=iq3_xxs/iq4_nl`; the new selector contract test
verifies that each pair-specific value changes only its matching format while
`1` keeps its broad legacy behavior. The selector applies to every eligible
CPU-owned expert of that format across the model, not to one layer only.

The model is the pinned IQ1_M two-shard Coder GGUF from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. All four arms used the same
current-source service binary (`1d0f7fc3…8225d`), prompt cache 0, spec 2,
suffix drafting 0, 8K context and a 28 GiB memory limit. Each served the same
512-token / 2,048-token / 512-token recovery / continuation sequence with 16
generated tokens per request. Every request recorded zero accepted drafts.
The run order was adaptive control, adaptive IQ3-only mirror, fixed control,
fixed IQ3-only mirror. Both controls and both mirror runs passed; all cgroup
memory event counters stayed at zero. Minimum host/admission availability was
14.37/14.37 GiB (adaptive control), 14.33/14.33 GiB (adaptive mirror),
14.45/14.45 GiB (fixed control) and 14.37/14.37 GiB (fixed mirror), above the
six GiB floor.

| Residency | Request | Different token IDs (of 16) | Persistent-state fields different (of 9) |
| --- | --- | ---: | ---: |
| Adaptive | Short | 10 | 7 |
| Adaptive | Long | 3 | 7 |
| Adaptive | Recovery | 0 | 6 |
| Adaptive | Continuation | 0 | 6 |
| Fixed | Short | 10 | 7 |
| Fixed | Long | 0 | 6 |
| Fixed | Recovery | 10 | 7 |
| Fixed | Continuation | 10 | 7 |

Thus the IQ3_XXS/IQ4_NL Q8_1 CPU route alone is sufficient to change committed
state and, for some requests, token IDs in this tested configuration. This
does not isolate a single layer or prove a broad quality defect; it shows why
the close operator match cannot be treated as service-state equivalence. The
experiment does not qualify CPU/GPU migration, answer quality, throughput or
energy. Clock frequencies were dynamic, and service timings are retained only
as run metadata.

Raw request IDs, accepted-prefix fingerprints, service logs, tegrastats,
memory samples and supervisor summaries are under `supervised/`. The exact
service harness, config, workload and model shard checksums are in `source/`.
Run `python3 analyze.py` to regenerate `analysis.json`. Binary and source
identities are in `artifact-identity.json`; the source overlay is hashed in
`source-overlay.sha256`.

The focused Orin tests include six synthetic dot/window checks and the new
pair-selector contract. Phase 5 remains open: the per-format service result
does not identify the full source of state drift or qualify a serving policy.
