# Same-binary MTP × prompt-length interaction — planned Orin campaign

This is the follow-up required because the prior seven-pair 512-token and
7,501-token confirmations used different Strata binary hashes. Those results
remain valid within their individual campaigns, but they cannot establish the
workload interaction.

## Design

Use a blocked 2×2 design on one Orin build and one model/artifact set:

| Factor | Levels |
| --- | --- |
| MTP | off; window 3 with the same int8 KV format |
| Formatted prompt length | 512 tokens; 7,501 tokens in an 8,192-token context |

Both configs use Q2_0, int8 KV, 3,000 requested expert slots, eight workers,
fixed expert residency, no prefix cache, and the same prefill chunk and CPU/GPU
sharing policy. Only the MTP arguments and verifier window may differ. Pin
source commit `c55e84756e5497e1e1fd9805e815db5859dfa959` and candidate binary
SHA256 `57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`.
The engine binary, model and pack digests, tokenizer/template, context,
generation policy and all non-MTP arguments must match across all 40 measured
requests.

Run a three-pair screen on the existing short and near-limit prompts, then a
seven-pair confirmation with newly generated held-out prompts at the same exact
formatted lengths. Generate those inputs with
`python3 bench/results/2026-10-16-phase6-q2-int8-mtp3-workload-interaction/prepare_confirmation.py`.
Within each workload block, randomize which MTP arm runs
first. Randomize the order of workload blocks. Each arm gets a fresh service,
the same one-request warmup, a 28-GiB cgroup scope, one-second telemetry, and
the six-GiB physical-availability floor. Do not launch while another model
campaign owns Orin.

## Analysis contract

Require exact prompt usage, all planted markers once and in order, the
independent short-task suffix sum, same-pair answer equality, actual int8 KV and
cache capacity, and zero cgroup pressure/OOM events. Retain failed cells.
Summarize prompt/decode rates, client TTFT and total request time from all
seven independent paired processes at each prompt length, with medians,
per-block paired changes, bootstrap intervals and sample counts. Report p95
latency descriptively with its seven-request sample count. Record actual clocks,
thermal range, host availability, cgroup use, swap and named rail readings;
label rail energy as board-rail diagnostics, not request-attributed energy.

Estimate the interaction on log response ratios: within each workload, take
the paired candidate/baseline ratios; then compare the median log ratio at
7,501 tokens with the median log ratio at 512 tokens. Bootstrap whole paired
processes independently within each workload. This is a two-level interaction
estimate for these prompts and profile, not a general response surface or a
default-selection claim. Keep the screen separate from held-out confirmation.

## Current status

The randomized three-pair screen completed all 12 arms and passed analysis with
six complete workload pairs and no rejected cells; results and the screen-only
interaction estimates are in [README.md](README.md). Confirmation attempt 1's
short-task responses failed the independent suffix-sum oracle because its
prompt did not explicitly request that arithmetic; those cells are excluded.
The corrected seven-pair-per-workload confirmation completed all 28 arms in
`confirm-2/`. Independent analysis passed 14 pairs with no rejected cells. Its
workload-specific effects and bootstrap interaction intervals are in
[README.md](README.md); the MTP × prompt-length result does not promote a
default, and Phase 6 remains open for other interactions. Attempt 1 remains
preserved and excluded because its short prompt did not ask for the independent
suffix-sum task.
