# Near-limit Coder MTP rejection and recovery — Orin — 2026-10-23

This supervised current-binary probe compared MTP off and window 4 on the
pinned Coder IQ1_M model with a 7,498-token prompt and 8K configured context.
Each engine ran three sequential requests on the same session: 12 generated
tokens, then eight more with the conversation prefix, then an eight-token
recovery continuation. Adaptive swaps were disabled by the accepted-prefix
harness. The 28 GiB cgroup and six-GiB physical headroom guard remained active.

The MTP initial request offered 15 drafts, accepted six and rejected nine.
The two subsequent requests exercised continuation after that rejected
suffix. MTP-off and MTP-window-4 token IDs matched in all three requests.
Main-model fingerprints matched at every shared accepted-prefix boundary and
at each request endpoint: six initial boundaries, three continuation
boundaries and four recovery boundaries. MTP also rejected five drafts during
the final recovery request; this test did not include a fourth request after
that later rejection.

The run completed in 516.9 seconds over 489 memory samples. Minimum physical
and admission availability were 13.32 GiB, with zero cgroup low/high/max/OOM/
kill events. GPU clocks were dynamic; EMC readback was denied. Energy was not
measured. Timings are not a paired performance estimate. Exact prompt/output
hashes, accepted-prefix comparisons, model/binary identities and telemetry
summary are in [`analysis.json`](analysis.json). Raw logs remain under
`/tmp/phase5-coder-mtp-long-rejection-recovery-guardfix*`.

The first run of this case is retained in the analysis as a failed guard
variant. That guard required a rejection specifically in the middle request;
the initial request had nine rejected drafts while the middle request accepted
all six. Its outputs and state comparisons still matched, but the guard made
the supervisor command exit nonzero. The guard now requires a rejection in
either of the first two requests, ensuring a subsequent recovery request.

The artifact is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. IQ1_M shard SHA256 values,
current binary SHA256 and source revision are recorded in `analysis.json`.

Reproduce from the repository root with new output directories:

```sh
mkdir -p /tmp/phase5-coder-mtp-long-rejection-recovery
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/phase5-coder-mtp-long-rejection-recovery-supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 tools/integration/mtp_continuation_probe.py \
  --config bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/config.json \
  --engine build/integration/candidate/strata \
  --output /tmp/phase5-coder-mtp-long-rejection-recovery/run \
  --prompt-tokens 7498 --initial-tokens 12 --continuation-tokens 8 \
  --recovery-tokens 8 --require-rejection --run
```

This adds one near-limit, single-live accepted-state transaction case. It does
not bound other prompts, longer chains, adaptive migration, cancellation or
multi-live batch behavior; Phase 5 remains open.
