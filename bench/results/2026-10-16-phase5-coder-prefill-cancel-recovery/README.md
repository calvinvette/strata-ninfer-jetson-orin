# Coder IQ1_M long-prefill cancellation and recovery — Orin — 2026-10-16

This supervised Phase 5 check canceled a streaming request during a long
prefill, then checked same-service recovery and compared the recovered
persistent state with a fresh-service request.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. Its shard SHA256 values are
`e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad` and
`316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
MTP uses the base `Qwen/Qwen3.8-Flash-Next` revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`; this is not a Coder-specific MTP
checkpoint. The run used repository commit `58d789ec3670` and candidate binary
SHA256 `dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`.

The workload was the existing 7,501-token retrieval prompt at 8,192 context,
with the established Coder IQ1_M profile, FP16 KV, MTP4, cadence-4 accepted-only
adaptation and 3,000 requested expert-cache slots (3,903 actual slots). The
client closed the stream one second after response headers. The engine recorded
64 of 7,501 prompt tokens read in 8.50 seconds, zero generated tokens and zero
checkpoints, then reported cancellation. The delay between client close and
engine cancellation means this tests an early-prefill cancellation point, not
arbitrary positions throughout prefill.

The same service stayed alive and returned exactly `Hello Orin!`. A fresh
service returned the same text and matched all 11 recorded persistent-state
fields at accepted prefix `L=24` (GDN, PLE, tail, pooled, pooled-full, KV, MTP,
stale, dead, and PLE predecessor state). This is one functional cancellation
and recovery point, not repeated cancellation qualification or a performance
measurement.

The run lasted 73.6 seconds under a 28-GiB systemd scope. Across 71 one-second
samples, minimum host and admission availability was 13.29 GiB; cgroup
`low`/`high`/`max`/`oom`/`oom_kill` counters remained zero. Dynamic observed
GPU clocks ranged from 306 MHz to 1,300.5 MHz and CPU clocks from 729.6 MHz to
2,201.6 MHz. EMC clock readback was denied, and energy was not attributed to the
requests. Raw telemetry and both service logs are retained here.

Reproduce on Orin1 from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-16-phase5-coder-prefill-cancel-recovery/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 tools/integration/cancel_long_prefill_recovery.py \
  --config bench/results/2026-10-16-phase5-coder-prefill-cancel-recovery/config-8192.json \
  --long-workload bench/results/2026-10-16-phase5-coder-prefill-cancel-recovery/workload-7501.json \
  --output bench/results/2026-10-16-phase5-coder-prefill-cancel-recovery/result.json \
  --cancel-after-s 1 --compare-recovery-state
```

The focused harness tests passed 4/4. This adds Coder IQ1_M early-prefill
cancellation evidence; Phase 5 remains open.
