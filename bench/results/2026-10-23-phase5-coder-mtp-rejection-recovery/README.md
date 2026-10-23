# Coder MTP rejection and recovery — Orin — 2026-10-23

The extended same-engine probe compared MTP off with window 4 on the pinned
Coder IQ1_M model. Each arm ran three requests on one engine: a 512-token
prompt with 12 generated tokens; that prompt plus the first output with an
eight-token continuation; then the full updated conversation with an
eight-token post-continuation recovery. The second MTP request was required to
reject at least one proposed draft.

The requirement was met: MTP accepted 6 of 9 drafts and rejected three. Both
arms produced identical token IDs on all three requests. The nine main-model
state fingerprints matched at all shared accepted-prefix boundaries: six in
the initial request, four in the rejection continuation, and three in the
post-rejection recovery. Endpoint fingerprints matched after each request.
The recovery request therefore confirms matching output and state after the
rejected-draft request on this prompt. Draft-only and stale-state hashes are
not part of the main-model equality contract.

This is one deterministic prompt pair on one binary. It does not qualify
other rejection points, longer adaptive chains, cancellation during a
rejected round, multi-live batch decoding, or performance. The measured decode
times are single-run descriptors only. Full token hashes, state comparisons,
artifact identities, and telemetry summary are in [`analysis.json`](analysis.json);
raw request logs and supervisor samples remain local under
`/tmp/phase5-coder-mtp-rejection-recovery*`.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` revision
`5348543e0147355ac9cbcb031184a3546350988e`, with IQ1_M shard hashes
in `analysis.json`. The binary SHA256 is
`afc710def2ad1c0f0905afa015f5cae3e50063b29d7c4fdd62f186ab21a7358d`; shared
C++ source revision is `7899a8c91bb7061eac3861d72070a17452fa9256`.

The supervisor completed in 114.0 seconds over 111 samples. Minimum physical
and admission availability were 13.37 GiB, above the preserved 6 GiB floor;
cgroup low/high/max/OOM/kill counters stayed zero. GPU clocks varied from 306
to 1,300.5 MHz, EMC readback was denied, and energy was not measured.

Reproduce from the repository root (both output paths must be new):

```sh
mkdir -p /tmp/phase5-coder-mtp-rejection-recovery
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/phase5-coder-mtp-rejection-recovery-supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 tools/integration/mtp_continuation_probe.py \
  --config bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/config.json \
  --engine build/integration/candidate/strata \
  --output /tmp/phase5-coder-mtp-rejection-recovery/run \
  --prompt-tokens 512 --initial-tokens 12 --continuation-tokens 8 \
  --recovery-tokens 8 --require-rejection --run
```

The harness now captures request counters at every stage, compares the third
request's state and output, and can require an observed rejected draft. Its
focused tests passed 12/12 and the full Python integration suite passed
166/166. Five current-build CUDA CTests also passed: accepted-window, GDN
recurrent parity, GDN parity, graph registry lifecycle, and captured-graph
trace. The CTest supervisor retained 23.73 GiB minimum host availability and
recorded zero cgroup memory events. Phase 5 remains open for broader adaptive
and multi-live qualification.
