# Coder natural-prompt service and recurrent-state check

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This is a small E5
functional/state screen, not an answer-quality suite or performance result.

## Controls and task

The paired service arms used the same binary, Coder IQ1_M two-shard artifact,
pack, profile, cache options, four workers, prefill chunk 64 and 512-token
context. They used greedy sampling, `STRATA_PREFILL_CPU_SHARE=0`, prompt-cache
disabled and strict NInfer for the candidate. The model identity is pinned in
the [mixed-backend report](../2026-11-05-e5-mixed-static-one-token-pair/state-parity-8token-recheck/README.md).

The chat-formatted prompt was: “Solve this arithmetic problem: What is 2 + 2?
Respond with only the numeral.” It encoded to 32 prompt tokens. The expected
answer oracle requires exactly `4` after removing the generated `<|im_end|>`
stop marker. Each arm generated two tokens, `[19, 248046]`.

## Results

Both backends passed the exact answer oracle and returned identical token IDs
and accepted-prefix token sequences. Persistent-state hashes differed at both
accepted prefixes and at request completion.

Two fresh runs per backend captured the final GDN state at accepted length 33.
Within each backend, the two raw GDN captures were bit-identical. Across
Strata and strict NInfer, all 36 GDN layers differed: 28,205,015 of 29,417,472
float values, global relative L2 `0.0362582`. The first changed model layer
was layer 1 (`1.51e-9` relative L2); layer 2 was `7.36e-5`, and the maximum
per-layer relative L2 was `0.09134` at layer 23. The maximum absolute value
delta was `0.76329` at layer 25. The cross-backend result repeated exactly in
both paired captures.

The two Strata state dumps share SHA-256
`6be6e30a93d62a7c8591e5439223b4ffaac250fd5b8c926b318aa510c4384214`; both
strict-NInfer dumps share SHA-256
`e6959575aee54e414f53e3de36502f0412a6d2bcd9ea3ea72d0700c36d0d557a`.
The cross-backend per-layer comparisons are retained as JSON in each capture
directory; raw state arrays remain local because each is 113 MiB.

This shows deterministic recurrent-state drift despite identical answer tokens
for this one short arithmetic task. It does not establish a user-visible quality
regression or a useful numerical bound. The first synthetic-prompt diagnostic
found only `~1e-7` layer-0 operator/activation differences; the large recurrent
state movement here requires broader, layer-by-layer numerical analysis. No
latency is reported because state capture is intrusive and the request is too
short for a serving comparison.

Minimum available physical RAM was 20.44–20.59 GiB across the two supervised
GDN-captured pairs; the pre-existing cgroup OOM-kill count remained one in both.
Clocks were observed and dynamic, EMC readback was denied, and energy was not
measured. Raw command logs, memory samples and supervisor records are retained
in this directory. The 113 MiB per-arm GDN dumps remain local and are excluded
from Git; their comparison JSON and hashes are retained.

## Next E5 gate

Repeat accepted-prefix numerical state checks over varied natural short tasks
and longer answer/retrieval tasks. Add a declared state-drift contract before
accepting the NInfer backend for service use. Keep MTP and adaptive residency
out of this comparison until the static resident-backend state behavior is
understood. E5, E6 and E7 remain open.

## Held-out executable code task

Date: 2026-11-05. A second functional screen used the same Coder IQ1_M two-shard
model, pack, binary, static profile, cache and service settings. The prompt
asked for a Python `is_even(n)` function. Its 44-token chat-formatted prompt
was followed by a maximum of 64 generated tokens. The independent executable
oracle checked `0`, `1`, `2`, `3`, `-2` and `-3`.

Strata and strict NInfer each generated the same 21 token IDs and the exact
code `def is_even(n): return n % 2 == 0`; all six oracle cases passed. All 21
accepted-prefix token IDs matched, but the persistent-state fingerprints first
differed after the first accepted token and remained different at all 21
captured boundaries. Final GDN, PLE, tail, dead, pooled, pooled-full and KV
fingerprints differed. NInfer dispatched all seven observed mixed-codec
tuples. Each arm offered two speculative drafts and accepted zero, so this run
did not commit drafted tokens.

The supervised pair completed in 42.16 seconds with 21.08 GiB minimum
available physical RAM; the pre-existing cgroup OOM-kill count stayed at one.
Clocks were observed but uncontrolled, EMC readback was denied, and energy was
not measured. The request order was sequential (Strata then NInfer), and
hashing/trace instrumentation was enabled. The per-request timings are
diagnostic only and must not be read as a backend performance comparison. The
one initial launch attempt with `--spec 0` exited before model loading because
this native pack requires a verifier window of at least two; the recorded
result uses `--spec 2`.

This adds one executable code-quality point with exact answer-token parity,
while reinforcing that matching text does not imply matching recurrent state.
It neither sets a numerical drift tolerance nor establishes broader code
quality. Raw supervised logs and the state comparator output are in
`even-pair-retry/` and `supervisor-even-pair-retry/`.

### First accepted-token GDN state

A supervised follow-up captured both backends' raw GDN arrays at the first
accepted token of the same `is_even(n)` prompt (engine state boundary `L=44`).
Both emitted token ID `71093`. The 36 GDN state slices contain 29,417,472 FP32
values total. Strata slice 0 was bit-identical; slice 1 first differed at
relative L2 `1.71e-9`; slice 2 reached `9.32e-4`. Drift then grew across the
remaining recurrent state, reaching `3.03e-2` at slice 18 and a maximum
per-slice relative L2 of `9.19e-2` at slice 26. Overall, 28,242,042 values
(96.0%) differed and global relative L2 was `5.41e-2`. The maximum absolute
delta was `3.093` at slice 33. Slice numbers here are the serialized GDN
state ordinals, not a causal attribution to a specific operator.

The same binary, profile and cache were used in a sequential Strata-then-NInfer
service pair with greedy sampling and prefill CPU share disabled. The
supervisor passed in 23.29 seconds with 20.93 GiB minimum available physical
RAM; the pre-existing cgroup OOM-kill count stayed at one. Clocks were
observed but uncontrolled, EMC readback was denied, and energy was not measured.
Raw 113 MiB state arrays are local and excluded from Git. Their hashes, logs
and the per-slice comparison are retained under `even-gdn-pair-retry/`.

This confirms that substantial downstream recurrent-state divergence is
already present after the first generated token, even though that token and
the completed function match. It does not determine whether the difference
arises during prompt prefill, at a particular expert operator, or in a later
state update. An opt-in prefill-state hook did not produce a capture in this
service path and is not used as evidence. The numerical tolerance and user-
visible impact remain open.
