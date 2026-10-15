# Current-source Coder IQ1_M sustained service — Orin — 2026-10-15

This Phase 7 run repeats the sustained cache-reuse test on the current service
binary (`57b2222…`, source commit `b99b26a2`) and the Coder GGUF shard hashes
listed in `model-sha256.txt`. It used the opt-in profile from the current-source
8K/16K/32K checks: Q6_K warp-dequant, accepted-only MTP4 at cadence 4, FP16 KV,
3,000 requested expert-cache slots (3,903 actual), eight workers, prefill
chunk 64 and dynamic clocks.

After a 512-token warmup, the service completed a fresh 7,498-token retrieval
precondition with zero cached prompt tokens; all three planted markers were
present exactly once. It then ran the requested 2,400-second cache-reuse loop.
All 1,586 streamed requests completed, returned all three markers exactly
once, and reused 7,491 prompt tokens. There were no failed or incorrect
requests. The measured loop was 2,400.10 seconds. Descriptive median/p95 client
request times were 1.552/1.588 seconds and median/p95 time to first visible
token was 0.245/0.246 seconds. These successive cache-reuse requests are a
service-soak series, not independent samples for statistical inference.

The run was supervised at `MemoryMax=28G` with the six-GiB host-availability
guard. Across 2,690 memory samples, minimum host and admission availability
were 13.30 GiB, maximum cgroup use was 10.68 GiB, and `high`, `max`, `oom` and
`oom_kill` counters stayed zero. `tegrastats` recorded `tj` from 49.3 to
73.3 °C. From 14:40 through 15:11, 32 complete minute bins (31 minutes
between endpoints) stayed within 71.1–73.3 °C. Observed GPU frequency ranged 306 MHz
to 1.3005 GHz and CPU frequencies 729.6 MHz to 2.2016 GHz. Clocks were not
changed; EMC readback was denied; rail power was not attributed to the process
and is not an energy-per-token result.

This refreshes sustained-service evidence for this exact binary, profile and
model identity. It does not cover concurrent requests, other models or a
general thermal/performance guarantee, and does not close Phase 7.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m-soak/supervisor \
  --timeout 3000 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q6-recall/run_sustained.py \
  --config bench/results/2026-10-15-phase7-current-source-coder-iq1m-soak/config-8192.json \
  --workload bench/results/2026-10-15-phase7-current-source-coder-iq1m-soak/workload-8192.json \
  --warmup-workload bench/results/2026-10-15-phase7-current-source-coder-iq1m-soak/warmup-512.json \
  --duration-seconds 2400 \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m-soak/run
```

The per-request quality/cache records, telemetry, engine log, supervisor
result, model hashes and binary identity are retained here.
