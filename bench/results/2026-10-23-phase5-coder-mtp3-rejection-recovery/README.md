# Coder MTP3 rejection and recovery — Orin — 2026-10-23

This current-source probe compared MTP off with MTP window 3 on the Coder
IQ1_M model. Each arm used one engine for three requests: a 512-token prompt
with 12 generated tokens, an eight-token continuation, then an eight-token
post-continuation recovery request. The harness recorded accepted-prefix
traces and main-model state fingerprints at each request boundary.

MTP3 offered/accepted 10/7 drafts in the initial request, 6/5 in the
continuation, and 6/4 in recovery. Thus it rejected three drafts initially
and one in the continuation before recovery. MTP-off and MTP3 outputs matched
for all three requests. State fingerprints matched at every position captured
by both arms: six shared boundaries in the initial request, four in the
continuation and four in recovery. All endpoint fingerprints also matched.
This adds one MTP3 rejection-and-recovery case, not a long-chain bound,
cancellation test or multi-live qualification.

The supervised run lasted 111.7 seconds. Minimum physical and admission
availability were both 13.337 GiB, above the preserved 6 GiB floor. All
sampled cgroup low/high/max/OOM/kill counters remained zero. Clocks were
observed but not controlled; EMC clock readback was denied. Energy was not
measured. Raw request logs, state hashes and supervisor telemetry are retained
beside this report.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M. Model
shard identities are in [`model-sha256.txt`](model-sha256.txt); engine source,
probe source and binary identities are in [`engine-source-revision.txt`](engine-source-revision.txt),
[`probe-source-revision.txt`](probe-source-revision.txt),
[`probe-script-sha256.txt`](probe-script-sha256.txt) and
[`binary-sha256.txt`](binary-sha256.txt). The configuration is copied to
[`config.json`](config.json). MTP runtime/model data remain under
`~/models/strata-orin-validation/`.

The continuation probe now accepts `--mtp-window {2,3,4}`; window 4 remains
the default. Its focused tests pass 7/7. Reproduce with new output paths:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/phase5-coder-mtp3-supervisor --timeout 1800 --interval 1 \
  --sample-clocks -- \
  python3 tools/integration/mtp_continuation_probe.py \
  --config bench/results/2026-10-23-phase5-coder-mtp3-rejection-recovery/config.json \
  --engine build/integration/candidate/strata \
  --output /tmp/phase5-coder-mtp3-run --prompt-tokens 512 \
  --initial-tokens 12 --continuation-tokens 8 --recovery-tokens 8 \
  --mtp-window 3 --require-rejection --run
```

Phase 5 remains open for other rejection points and longer/adaptive chains,
cancellation, multi-live state correctness and graph/MTP interaction.
