# Current-source Coder IQ1_M 128K retrieval and recovery — Orin — 2026-10-15

This supervised Phase 7 check used the `IQ1_M` variant from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, pinned to local Hugging
Face snapshot revision `5348543e0147355ac9cbcb031184a3546350988e`. At 131,072
configured context, the exact formatted prompt contained 120,149 tokens. The
three planted codes were returned exactly once and in order. A following
request on the same service returned exactly `RECOVERED`.

The request generated 41 tokens. MTP drafted 33 and accepted 28. Engine
prefill took 6,074.8 seconds at 19.8 tokens/s; decode took 4.75 seconds at
8.6 tokens/s. The full supervised process took 6,147.7 seconds including
startup, warmup and recovery. This is one retrieval and recovery point for
this model and profile, not a general quality result or comparison between
quantizations or inference engines.

The candidate binary SHA256 is recorded in `binary-sha256.txt`; it was built
from Strata source commit `c55e8475`. The profile is Q6_K warp-dequant,
accepted-only MTP4 at cadence 4, FP16 KV, 3,000 requested expert slots (3,903
actual), eight workers and prefill chunk 64. The two model shard hashes and
snapshot provenance are recorded in `model-sha256.txt` and `model-source.txt`.
All model files remain under `~/models/strata-orin-validation/`.

The successful process ran under `MemoryMax=28G` and the six-GiB host
availability guard. Across 5,837 one-second samples, minimum host and
admission availability was 10.20 GiB. The leaf scope peaked at 10.91 GiB;
`low`, `high`, `max`, `oom` and `oom_kill` counters stayed zero. Clock and
tegrastats observations are retained; clocks remained dynamic and untouched.
EMC readback was denied and energy was not request-attributed.

An earlier attempt in `run/` was interrupted by supervisor signal 15 after
6,349.5 seconds, at 117,056 of 120,149 prompt tokens. Its partial artifacts
are preserved but excluded. The passing retry is `run-attempt2/`, with its
supervisor telemetry in `supervisor-attempt2/`.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m-128k/supervisor-attempt2 \
  --timeout 10800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q6-recall/run_recall_case.py \
  --config bench/results/2026-10-15-phase7-current-source-coder-iq1m-128k/config-131072-attempt2.json \
  --workload bench/results/2026-10-15-phase7-current-source-coder-iq1m-128k/workloads/workload-131072.json \
  --warmup-workload bench/results/2026-10-15-phase7-current-source-coder-iq1m-128k/warmup-512.json \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m-128k/run-attempt2
```

The answer, request artifacts, both attempts, telemetry, configuration, model
hashes and binary identity are retained here. Phase 7 remains open for
independent repetitions, broader task quality, sustained service, concurrency
and other support boundaries.
