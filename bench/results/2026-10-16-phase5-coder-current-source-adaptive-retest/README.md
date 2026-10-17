# Current-source Coder IQ1_M adaptive-state retest — Orin — 2026-10-16

This randomized one-pair correctness retest ran the Coder IQ1_M same-service
sequence on the current candidate binary: a short 512-token request, a 2,048-
token request, the original short request again, then one more identical short
request. Each request generated 16 tokens. The arms were a delayed-adaptation
control (`--adapt-every 100000`) and cadence-4 adaptive updates limited to eight
expert swaps (`--adapt-every 4 --adapt-swaps 8`). Both used MTP off, FP16 KV,
accepted-only usage scheduling, the same expert profile and cache settings.
Arm order was randomized with seed 20261030; cap-8 ran first. This is
correctness/state evidence, not a timing comparison.

The model was `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, IQ1_M,
pinned at revision `5348543e0147355ac9cbcb031184a3546350988e`. The runner
checked both GGUF shard hashes before launch. The service binary SHA256 was
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`; repository
HEAD at run time was `cdf652387995922921f7190b30e06e789b43937f`. Models remained
under `~/models/strata-orin-validation/`.

The initial 512-token and recovery 512-token outputs matched across arms. The
2,048-token response differed at 3/16 positions. The subsequent identical
short continuation differed at all 16 positions: cap-8 did not reproduce the
delayed control's continuation. Within the cap-8 service, the recovery output
matched its initial short output, but five persistent fingerprints (`gdn`,
`tail`, `pooled`, `pooled_full`, `kv`) had changed; the next continuation then
diverged. The delayed control retained the initial state fingerprints and
returned the same 16 tokens on all three short requests. This confirms that an
immediate matching recovery response does not prove state recovery.

The cap-8 arm passed all 15 adaptive refill-byte and all 15 residency-table
checks. Its layer-0 trace showed no owner changes in the first seven captured
rows and no layer-0 activation changes between initial and recovery short
requests. This limited capture does not localize the state cause. Together
with prior all-layer traces, the result supports route-dependent numerical
state sensitivity, but does not prove a complete causal path or a remedy.

Both supervised arms passed under separate 28-GiB scopes. Minimum host and
effective admission availability were 14.15 GiB for cap-8 and 14.48 GiB for the
delayed control. Sampled cgroup `low`, `high`, `max`, `oom` and `oom_kill`
events were zero. Clocks were observed dynamically; no timing or energy claim
is made. `verification.json` summarizes the checks and `SHA256SUMS.txt` covers
the runner, commands, raw request/state captures, service logs and telemetry.

Reproduce on Orin from the repository root with:

```sh
python3 bench/results/2026-10-16-phase5-coder-current-source-adaptive-retest/run_pair.py \
  --output bench/results/2026-10-16-phase5-coder-current-source-adaptive-retest/reproduction \
  --seed 20261030 --run
```

This one-pair current-binary retest corroborates the seven-pair adaptive
recovery finding; it does not replace that confirmation. Adaptive cap-8 remains
unqualified for state recovery, and Phase 5 remains open.

## Current-binary all-layer follow-up

A second randomized pair captured dispatch inputs, expert IDs and route owners
across all 48 layers for the same short/long/short/continuation sequence. It
used seed 20261031, with delayed control first, and the same binary
(`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`), model,
KV and swap settings as the preceding current-source pair. The capture limit
was 4,096 rows per service: the first three 22-row request groups are complete
at all layers, and the continuation group covers its first 19 rows per layer
(20 on layers 0–15). The recorded continuation token and state comparisons
still cover all 16 generated tokens.

In the initial short request, the first owner difference was at layer 1,
capture row 10, while the activation and expert IDs matched. Experts 26 and 95
changed between primary VRAM and CPU ownership. At the next layer's same row,
all 2,560 activation values differed while expert IDs still matched. On the
long request, four experts changed CPU-to-primary-VRAM ownership at layer 1,
capture row 22, again on matching activation and IDs; the next layer's
activation differed. The short recovery repeated the same pattern at layer 1,
capture row 44, before the next-layer activation difference.

Within the cap-8 service, initial and recovery short requests returned the same
16 tokens but had different state fingerprints and different layer-1 owners at
the first captured row; layer-2 activation already differed there. The delayed
control had matching state, tokens, activations, expert IDs and owners between
those short requests. Cap-8 still passed all 15 swap-byte and all 15 residency
checks. These captures strengthen the route/state mechanism evidence on the
current binary. They do not establish that ownership changes are the only
cause, and they do not constitute a numerical fix or performance result. The
row-level analysis is `all-layer-pair/comparison.json`; `analyze_all_layers.py`
validates the alignment and reproduces its summary.

Both all-layer services passed supervision. Minimum host/admission availability
was 14.41 GiB for delayed control and 14.45 GiB for cap-8, with zero cgroup
memory events. The trace adds correctness evidence only; Phase 5 remains open.
