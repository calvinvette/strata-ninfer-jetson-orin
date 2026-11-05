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
