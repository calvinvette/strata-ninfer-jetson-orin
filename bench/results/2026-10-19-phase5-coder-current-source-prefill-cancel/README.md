# Current-source Coder IQ1_M MTP4 prefill cancellation and recovery — Orin — 2026-10-19

This supervised Phase 5 run repeated a measured mid-prefill cancellation on
the current candidate binary, then compared recovered state with a fresh
service. The workload was the exact 7,501-token Coder retrieval prompt at
8,192 context. The tested profile used IQ1_M, FP16 KV, MTP4, accepted-only
adaptation cadence 4 and 3,000 requested expert-cache slots.

The client disconnected after 30 seconds. The engine had read 512 of 7,501
prompt tokens, generated zero tokens, and logged the request as canceled. The
same service then returned `Hello Orin!`; a fresh service returned the same
answer. All 11 persistent-state fingerprints matched at `L=24`, including
GDN, PLE, tail, pooled, pooled-full, KV, MTP draft state, stale/dead state and
PLE predecessor state. Independent review is in `verification.json`.

The candidate binary SHA256 was
`b09ed0b5774de235d145bff869950730a78cbf5ddc6b4057098d70b981130eaa`, built
from engine source commit `b6ea61888cb1ffb0bf92e79217d6a88d46178111`. The
model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, IQ1_M, pinned at
revision `5348543e0147355ac9cbcb031184a3546350988e`. MTP uses the base
`Qwen/Qwen3.8-Flash-Next` revision `de4b8e4d43b917e7706784d8bb445c9af86a3540`;
artifact hashes are in `artifacts.json`. All model/runtime files remain under
`~/models/strata-orin-validation/`.

The supervised 28-GiB scope completed in 73.9 seconds. Across 71 samples,
minimum host/admission availability was 13.16/9.80 GiB, above the six-GiB
floor. Cgroup low/high/max/OOM/OOM-kill counters were zero. Clocks were
observed dynamically; EMC readback was denied and energy was not attributed.
The raw engine/reference logs, configs and telemetry are retained here.

The first attempted invocation is retained under `supervisor/`; it stopped
before model startup because the config path was incorrect. The successful
rerun is under `supervisor-retry/`. Neither prelaunch command error is model
runtime evidence.

Reproduce from the repository root on Orin:

```sh
mkdir -p /tmp/strata-coder-prefill-current
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/strata-coder-prefill-current/supervisor --timeout 1800 \
  --interval 1 --sample-clocks -- \
  python3 tools/integration/cancel_long_prefill_recovery.py \
  --config bench/results/2026-10-15-phase7-current-source-coder-iq1m/config-8192.json \
  --long-workload bench/results/2026-10-16-phase5-coder-prefill-cancel-recovery/workload-7501.json \
  --output /tmp/strata-coder-prefill-current/result.json \
  --cancel-after-s 30 --compare-recovery-state

python3 bench/results/2026-10-19-phase5-coder-current-source-prefill-cancel/verify.py \
  --result /tmp/strata-coder-prefill-current/result.json \
  --supervisor /tmp/strata-coder-prefill-current/supervisor
```

This confirms one current-source cancellation point and recovery sequence. It
does not qualify every prefill boundary, other KV formats or performance; the
separate adaptive CPU/GPU migration state divergence remains unresolved.
Phase 5 remains open.
