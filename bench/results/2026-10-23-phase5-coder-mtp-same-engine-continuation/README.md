# Coder MTP same-engine continuation — Orin — 2026-10-23

This supervised correctness probe compared MTP off with window 4 on the
current integration binary and the pinned Coder IQ1_M artifact. Each private
engine received the same 512-token prompt, generated 12 tokens, then received
the prompt plus those generated tokens as a second request on the same engine
and generated eight more. The second request reused 523 prompt tokens.

Both arms produced identical token IDs for the initial response and the
continuation. The nine captured main-model fingerprint fields (GDN, PLE,
tail, dead, pooled, pooled-full, KV, PLE previous, and committed length)
matched at all six shared initial-response commit boundaries and all four
shared continuation boundaries, as well as at both request endpoints. MTP
accepted 6 of 9 offered drafts during the continuation, exercising rejected
draft rollback; its final committed state matched MTP off. The trace recorded
nine accepted draft tokens during the initial response. Draft-only and
stale-state fingerprints are intentionally excluded from the main-model
equality contract.

The compact tokens, endpoint fingerprints and per-boundary comparisons are in
[`analysis.json`](analysis.json).

This is one prompt and one pair of engine runs. It supports accepted-prefix
state equality through this observed rejection sequence, but does not cover
other rejection positions, long chains, cancellation during rejection,
multi-live batch decoding, or a performance effect. The 3,883 ms MTP-off and
2,300 ms MTP continuation decode times are single-run descriptive values and
are not a paired performance comparison.

The exact artifact is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`,
revision `5348543e0147355ac9cbcb031184a3546350988e`. The local model manifest
records IQ1_M shard SHA256 values `e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad`
and `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
The binary SHA256 was
`afc710def2ad1c0f0905afa015f5cae3e50063b29d7c4fdd62f186ab21a7358d`; its
shared C++ source revision was `7899a8c91bb7061eac3861d72070a17452fa9256`.

The supervisor completed in 101.5 seconds over 97 samples. Minimum physical
and admission availability were both 13.34 GiB, above the preserved 6 GiB
floor. Cgroup low/high/max/OOM/kill counters stayed zero. GPU clocks varied
from 306 to 1,300.5 MHz; EMC clock readback was denied. Energy was not
measured. Raw request logs and telemetry remain under
`/tmp/phase5-coder-mtp-continuation-2026-10-23/` and are not committed.

Reproduce from the repository root (the output directory must be new):

```sh
mkdir -p /tmp/phase5-coder-mtp-continuation
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/phase5-coder-mtp-continuation-supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 tools/integration/mtp_continuation_probe.py \
  --config bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/config.json \
  --engine build/integration/candidate/strata \
  --output /tmp/phase5-coder-mtp-continuation/run \
  --prompt-tokens 512 --initial-tokens 12 --continuation-tokens 8 --run
```

Phase 5 remains open for broader state-transaction coverage, adaptive-migration
drift, and multi-live batch state/output qualification.
