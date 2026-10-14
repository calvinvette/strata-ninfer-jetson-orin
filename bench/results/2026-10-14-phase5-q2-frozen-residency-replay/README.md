# Q2_0 frozen-residency replay — Orin — 2026-10-14

This same-service adaptive sequence followed by a fresh static-profile replay
checks whether the final resident expert set alone reproduces the previously
observed short/long/short persistent-state change. It used the existing Q2_0
model shards and runtime pack under `/home/calvin/models/strata-orin-validation/`,
3,000 expert-cache slots, FP16 KV, a 3-GiB workspace reserve, 16,384 maximum
context, prompt cache disabled, and MTP window 2. The exact short and long
prompts contained 7,515 and 15,020 tokens. An independent retrieval/arithmetic
oracle expected `EARLY=MAPLE-ORBIT-731, MIDDLE=COBALT-HARBOR-284,
LATE=VELVET-COPPER-956, SUM=1971`.

The supervised retry completed all five requests (adaptive 8K → 16K → 8K,
then two 8K requests on a fresh service loaded from the profile saved at
adaptive shutdown). All five returned the exact expected answer with the same
48 generated token IDs. Within adaptive mode, the first and recovery short
requests had equal answers but differed in six of nine persistent-state
fingerprints. In the frozen-profile service, the two repeated short requests
matched in answer and all nine fingerprints. The first frozen result matched
the adaptive recovery answer, but not its final fingerprints. This points to
adaptive updates during a request/sequence as necessary for the observed
state difference in this bounded case; the saved final residency set alone
was insufficient to reproduce it. It does not identify the numerical cause,
prove deterministic state equivalence across service starts, or qualify
adaptive swapping broadly.

The engine binary SHA256 was `857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`; model, runtime pack, tokenizer and initial expert-profile hashes are in `model-checksums.txt`. The saved profile was 196,632 bytes with SHA256
`a7c817fb4b646d166c0e1e35138dc3f32ceff547c65e601fa927e94b3dc0bd05`.
The run took 1,462.0 seconds under the 28-GiB cgroup ceiling, retained 17.85
GiB minimum host availability and 7.00 GiB minimum admission availability,
and reported no cgroup pressure or OOM events. GPU clocks varied from 306 to
1,300 MHz; EMC clock access was denied. Energy was not request-attributed.

The first launch did not start because the configured context was too small;
a retry exposed a harness type error after its first valid adaptive request.
Both are retained as `run/`, `run-retry1/`, and supervisor directories and are
excluded from the result. The passing complete run and raw traces are in
`run-retry2/` and `supervisor-retry2/`. No model or build product was copied
into the repository. Models remain under `~/models/`.
