# Q2_0 residency-change retrieval and persistent-state check — Orin — 2026-10-14

This same-service sequence tests whether adaptive expert residency changes that
alter persistent fingerprints also affect a bounded retrieval task. It used
the Q2_0 shards and runtime pack already under
`/home/calvin/models/strata-orin-validation/`, the current diagnostic engine
(`857a3fab...`), 3,000 expert-cache slots, FP16 KV, a 3-GiB workspace reserve,
16,384 maximum context and prompt cache disabled. The exact prompts were 7,498
and 15,003 tokens. The sequence was 8K → 16K → 8K recovery, first with MTP
off, then with MTP window 4 and accepted-only adaptation. No models or build
products were added to the repository.

All six answers matched the independent three-code oracle exactly and in order:
`MAPLE-ORBIT-731`, `COBALT-HARBOR-284` and `VELVET-COPPER-956`. Each answer
contained 41 generated token IDs and ended with the protocol stop token
`<|im_end|>`; quality scoring removes only that terminal control token from the
diagnostic tokenizer decode. Accepted-prefix tracing covered every published
token ID. MTP-off and MTP4 had matching task answers and matching persistent
fingerprints at each corresponding request. MTP4 accepted 30/34, 30/32 and
28/32 offered drafts at 8K, 16K and recovery.

Within each MTP arm, the recovery answer and token IDs matched the first 8K
request, but final persistent fingerprints did not. The GDN, PLE, tail, pooled,
pooled-full and KV fields differed after the intervening 16K request. This is a
direct state-drift finding associated with the adaptive residency sequence;
the retrieval oracle did not detect task-level degradation for these prompts.
It does not establish a broad quality budget, exact recurrent-state
equivalence, or acceptable drift for other tasks. The captured logs also show
that adaptive swap choices changed; they do not isolate a single numerical
cause.

The supervised run lasted 1,566.9 seconds under a 28-GiB cgroup ceiling. It
retained 16.883 GiB minimum physical availability and 7.043 GiB minimum
admission availability, above the six-GiB floor. Sampled cgroup low/high/max,
OOM and OOM-kill counters stayed zero. The minimum admission margin was about
1.04 GiB. Clock sampling was read-only; EMC access was denied and energy was
not process-attributed. The per-request prompt and decode times are retained
in `trace-rerun/results.json`; they are descriptive, not a paired performance
claim.

A same-day delayed-swap control repeated the sequence with
`--adapt-every 100000`, keeping the adaptive policy configured but placing its
update threshold beyond these request lengths. No adaptive choice batches were
emitted. All six replies again matched the marker oracle, accepted-prefix token
traces matched published IDs, and both MTP arms recovered the exact initial
8K persistent-state fingerprint after the 16K request. This contrast supports
adaptive swaps as the trigger for the recovery-state drift in this Q2_0
sequence. It does not identify which numerical operation differs between
residency paths. The control lasted 1,658.0 seconds, retained 16.800 GiB
minimum host availability and 6.445 GiB minimum admission availability, and
had zero sampled cgroup pressure/OOM events. It is one controlled sequence per
setting, not timing qualification.

The same sequence was also repeated with an arithmetic retrieval task. The
7,515- and 15,020-token prompts requested the three planted codes and the sum
of their numeric suffixes. All six requests returned the exact oracle answer
`EARLY=MAPLE-ORBIT-731, MIDDLE=COBALT-HARBOR-284, LATE=VELVET-COPPER-956,
SUM=1971`; the independent check is `731 + 284 + 956 = 1971`. Each completion
contained 48 token IDs, all covered by accepted-prefix tracing. MTP4 accepted
33/37 offered drafts in each request. Corresponding MTP-off and MTP4 states
matched, but within each arm the 8K recovery differed from the first 8K state
in GDN, PLE, tail, pooled, pooled-full and KV fields. Thus this bounded
retrieval-plus-arithmetic task also passed despite the state drift. The run
took 1,686.9 seconds, retained 16.776 GiB minimum host availability and 6.868
GiB minimum admission availability, and had zero sampled cgroup pressure/OOM
events. Raw data are under `trace-arithmetic/` and
`supervisor-arithmetic/`. The strict run result is false only for recovery
state equality; answer quality, MTP parity and accepted-prefix token checks
all pass. These few prompts do not establish broad task quality.

The first harness run is retained under `trace/` and `supervisor/`; it stopped
after the first request because the parser expected a separate final-state log
record. The corrected full run is under `trace-rerun/` and `supervisor-rerun/`.
The run-control process returned 1 because its original strict result required
both canonical text equality before stop-token normalization and identical
recovery state. The corrected analysis preserves raw text and raw traces,
normalizes the terminal stop token, and reports task-quality and state-drift
checks separately. Its strict combined `passed` field remains false because
the state fingerprints differ on recovery. The delayed-swap control is
retained under `trace-delayed/` and `supervisor-delayed/`; its strict combined
check passes.

Reproduction uses the local model/config and workload paths recorded by the
driver in `residency_quality_sequence.py`. The exact config and prompt workload
SHA256 values are listed in the Phase 7 Q2_0 report manifest; model shard
identity and byte sizes are documented in that report as well. The first
attempt is retained as a harness failure and is not pooled with the corrected
run.
