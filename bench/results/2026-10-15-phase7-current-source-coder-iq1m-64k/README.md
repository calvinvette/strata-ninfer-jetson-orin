# Current-source Coder IQ1_M 64K retrieval and recovery — Orin — 2026-10-15

This supervised Phase 7 run tested the `IQ1_M` variant from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, pinned to local Hugging
Face snapshot revision `5348543e0147355ac9cbcb031184a3546350988e`. At 65,536
configured context, the exact formatted prompt contained 60,079 tokens. The
three codes placed near 10%, 50% and 90% appeared once and in order; the model
returned their exact suffix sum `1971`. An independent arithmetic review
verified the codes and sum, and a following request on the same service
returned exactly `RECOVERED`. The request had zero cached prompt tokens.

The service generated 48 tokens. MTP drafted 39 and accepted 34. Engine
prefill time was 2,641.6 seconds at 22.7 tokens/s; decode took 4.0 seconds at
12.0 tokens/s. The full supervised process took 2,719.3 seconds, including
startup, warmup and recovery. This is one current-source functional quality
and recovery point for this model/profile. It is not a paired quantization or
inference-engine comparison and does not establish general 64K quality.

The run used the candidate binary whose SHA256 is in `binary-sha256.txt`,
built from Strata source commit `c55e8475`. The opt-in profile was Q6_K
warp-dequant, accepted-only MTP4 at cadence 4, FP16 KV, 3,000 requested expert
slots (3,903 actual), eight workers, prefill chunk 64 and dynamic clocks.
Model shard hashes are in `model-sha256.txt`; full repository and snapshot
provenance are in `model-source.txt`. Model files stayed under
`~/models/strata-orin-validation/`.

The process ran under `MemoryMax=28G` with the six-GiB host-availability guard.
Across 2,574 one-second samples, minimum host and effective admission
availability was 11.56 GiB. Peak use in the experiment's leaf cgroup was
12.78 GiB; `low`, `high`, `max`, `oom` and `oom_kill` counters stayed zero.
Read-only telemetry observed CPU frequencies from 729.6 to 2,201.6 MHz, GPU
frequencies from 306 to 1,300.5 MHz, and `tj` from 47.2 to 57.4 °C. No clocks
were changed. EMC readback was denied, and energy was not request-attributed.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m-64k/supervisor \
  --timeout 7200 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-15-phase7-q2-quality-64k/run_quality_task.py \
  --config bench/results/2026-10-15-phase7-current-source-coder-iq1m-64k/config-65536.json \
  --workload bench/results/2026-10-15-phase7-current-source-coder-iq1m-64k/workloads/workload-65536.json \
  --warmup-workload bench/results/2026-10-15-phase7-current-source-coder-iq1m-64k/warmup-512.json \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m-64k/run

python3 bench/results/2026-10-15-phase7-q2-quality-64k/review_arithmetic.py \
  bench/results/2026-10-15-phase7-current-source-coder-iq1m-64k/run/result.json
```

The answer, independent arithmetic review, configuration, request logs,
telemetry, supervisor samples, model hashes and binary identity are retained
here. `SHA256SUMS.txt` covers all artifacts except itself. Phase 7 remains open
for independent repetitions, wider task quality, concurrency and the other
support boundaries in the matrix.
