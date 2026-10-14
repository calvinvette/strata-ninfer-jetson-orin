# Q2_0 prefill cancellation and MTP-state recovery parity — Orin — 2026-10-14

This Phase 5 follow-up extends the 8K Q2_0 MTP4 prefill-cancellation check
with a direct comparison of the recovered service's final persistent state
against a fresh-service reference. The model and runtime assets were already
under `/home/calvin/models/strata-orin-validation/`. The service used 3,000
expert-cache slots, FP16 KV, a 3-GiB workspace reserve, 16,384 context, MTP4,
accepted-only adaptive swaps at cadence 4 and prompt cache 6. Prompt cache was
enabled for this diagnostic because the engine emits final state fingerprints
only when prompt caching is active. Both services used the same configuration.
The measured long request rendered to 8,192 tokens; the recovery request was
`Reply with exactly: Hello Orin!`.

The client closed the long stream 15 seconds after response headers. The engine
summary reported cancellation after 1,024 of 8,192 tokens were read and before
any generation. The lower-level batched-read trace says 8,185 tokens, which
conflicts with its two 512-token progress markers and the request summary; the
exact cancellation position is therefore unresolved, but the service did
report cancellation before decode. It recovered with `Hello Orin!`. After the
service stopped and released its model allocations, a fresh service answered
the same short prompt. The final
fingerprints at `L=24` matched for all 11 fields: GDN, PLE, tail, dead, pooled,
pooled-full, KV, MTP, stale, and the PLE previous-token pair. Two independent
post-fix FP16 sequences passed this comparison. A third post-fix sequence with
int8 KV also matched all fields.
An additional no-cache run (`--prompt-cache 0`, the original service setting)
also canceled and recovered with the exact `Hello Orin!` answer. State hashes
are not emitted in that mode, so it confirms default-path API recovery rather
than state equality.

The first state-comparison runs exposed the defect: before the fix, two
identical cancellation/recovery sequences matched the fresh reference in all
target-state fields but differed in the MTP draft-state hash
(`e3e2ea36bed73025` versus `18a52622e24764b6`). `MtpDrafter` now clears its
QSA KV/index state when the serving request starts a new sequence (`resume=0`),
matching the target session reset boundary. Conversation-cache resumes continue
to restore the saved draft KV prefix through the existing `kv_restore` path.
The post-fix runs matched the full state. This fixes the tested stale draft
state path; it does not qualify other MTP windows, KV formats, long cancellation
prefixes, or concurrent requests.

The two passing FP16 runs took 59.7 and 62.3 seconds; the int8 run took 56.8
seconds, each under a 28-GiB cgroup ceiling. Minimum host/admission availability
was 16.68/14.69 GiB for the first FP16 run, 16.77/15.45 GiB for the second
FP16 run, and 16.78/16.31 GiB for int8. No sampled cgroup pressure or OOM
events occurred. The no-cache API recovery run retained 16.69 GiB minimum
host/admission availability. GPU clocks varied from 306 to 1,300 MHz; EMC clock
access was denied. Energy was not request-attributed. The service binary SHA256 was
`e84dc9af72bd46ceb1f6fc1643aa5b97cd8c6fbf815b99b8163092806c84da9c`.
Model, pack, tokenizer and initial expert-profile hashes are in
`model-checksums.txt`. The draft-state clearing cost was not isolated; this is
correctness evidence, not a timing claim, and no performance profile was
promoted. MTP remains opt-in.

After the source change, the artifact-aware Q2_0 PLE oracle passed all seven
stages for three tokens (worst relative L1 `1.148e-7`), selected Phase 3 CTests
passed 15/15, and integration Python discovery passed 141/141. The full native
build passed. Full CTest reported two optional IQ skips and two fixture failures:
`expert_parity` and `pool_test` could not open the absent
`build/integration/candidate/pack/full/experts.bin`; the other 115 runnable
tests passed. Current-source HIP and SYCL service targets and CLI smoke checks
have since passed on maestro1; see the separate
[backend build report](../2026-10-14-phase8-mtp-reset-backends/README.md).
These x86_64 compile/load checks do not establish accelerator runtime behavior
and do not close Phase 8. They do not expand Phase 3's support scope. All raw
attempts, service logs, supervisor samples and result records are retained here. The
first attempt omitted the prompt-cache prerequisite for state hashing; two
valid pre-fix comparisons captured the MTP mismatch; attempts 04 and 05 are
the passing FP16 runs, `attempt-06-int8` is the passing int8 run, and
`attempt-07-no-cache` is the default-path API recovery run. No model or build
product was added to Git.
