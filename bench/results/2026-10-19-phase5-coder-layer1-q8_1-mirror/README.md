# Layer-1-only Q8_1 mirror service diagnostic — Orin — 2026-10-19

This experiment narrows the CPU Q8_1 diagnostic to one model layer. The opt-in
selector `STRATA_NATIVE_CPU_Q8_1_DOT=iq2_s/q2_0@layer=1` changes the CPU route
only for CPU-owned IQ2_S/Q2_0 experts on zero-based layer 1. The pinned Coder
IQ1_M pack records GGML types 22/42 on that layer, which resolve to IQ2_S/Q2_0.
All other layers and format pairs retain their usual path. The production
default remains unchanged.

The exact model was
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M, with two shard hashes in
`model-sha256.txt`. All four arms used the same Orin service binary
(`79368f55…e900`) and ran short-512, long-2048, short-512 recovery and one short
continuation. Each response emitted 16 tokens. The profile used 3,000 expert
slots, 64-token prefill chunks, 8K context, no prompt cache, `--spec 2`, and
dynamic clocks. Every run recorded zero accepted drafts, so each of the 64
accepted-prefix records per arm is a regular committed output token.

| Residency | Request | Token IDs changed (of 16) | Final state fields changed (of 9) | First differing committed prefix |
| --- | --- | ---: | --- | --- |
| Adaptive | Short | 0 | GDN, tail, pooled, pooled-full, KV | Commit 1: GDN, pooled, pooled-full, KV |
| Adaptive | Long | 3 | GDN, PLE, tail, pooled, pooled-full, KV, PLE-prev | Commit 1: GDN, pooled, pooled-full, KV |
| Adaptive | Recovery | 10 | GDN, PLE, tail, pooled, pooled-full, KV, PLE-prev | Commit 1: GDN, pooled, pooled-full, KV |
| Adaptive | Continuation | 0 | GDN, tail, pooled, pooled-full, KV | Commit 1: GDN, pooled, pooled-full, KV |
| Fixed | Short | 0 | GDN, tail, pooled, pooled-full, KV | Commit 1: GDN, pooled, pooled-full, KV |
| Fixed | Long | 3 | GDN, PLE, tail, pooled, pooled-full, KV, PLE-prev | Commit 1: GDN, pooled, pooled-full, KV |
| Fixed | Recovery | 0 | GDN, tail, pooled, pooled-full, KV | Commit 1: GDN, pooled, pooled-full, KV |
| Fixed | Continuation | 0 | GDN, tail, pooled, pooled-full, KV | Commit 1: GDN, pooled, pooled-full, KV |

All 16 accepted-prefix states differed for every matched request. This shows
that a layer-1-only CPU arithmetic change is sufficient to perturb persistent
state immediately in this workload. Under adaptive residency, the later short
recovery also changed 10/16 token IDs. Under fixed residency, recovery token
IDs matched even though every committed state differed. The experiment
localizes a sufficient perturbation; it does not establish a complete cause
for adaptive-swap drift, assess answer quality, or qualify CPU/GPU migration.

All four supervised processes passed under the 28-GiB cap with zero cgroup
pressure/OOM events. Minimum host and admission availability ranged from
14.26 to 14.38 GiB, above the six-GiB floor. Clock frequencies were dynamic;
EMC readback was unavailable and process energy was not measured. Each arm ran
once, so timings are not used as performance comparisons.

`service-test/scoped/` retains raw service logs, accepted-prefix traces,
supervisor samples and per-arm analyses. The cross-arm analyzer additionally
compares every committed state directly. The source overlay and exact binary
identity are recorded alongside the 7/7 focused Q8_1 CTest results. Exact-source
maestro1 HIP and SYCL builds and successful CLI checks are recorded in
`backend/maestro1/`; they are not accelerator runtime tests. Phase 5 remains
open: this diagnostic is not a quality or migration qualification.

Verify the retained service artifacts from `service-test/` with
`sha256sum -c SHA256SUMS`. Verify the backend logs from
`backend/maestro1/logs/` with `sha256sum -c SHA256SUMS`.
