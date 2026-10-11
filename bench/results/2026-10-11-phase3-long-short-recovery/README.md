# Long-prefill followed by short-request recovery — Orin — 2026-10-11

One owned IQ1_M Coder service process handled a 2,048-token prompt with eight
generated tokens, then a distinct 172-token prompt with eight generated tokens.
The harness issued a distinct exact-length warmup for each workload before the
two measured requests. The long request passed at 2,048 prompt tokens and the
short follow-up passed at 172; both generated all eight tokens and reported
`cache_n=0`, so the second request did not reuse a prompt cache entry. The
engine emitted separate end-of-request state fingerprints for both warmups and
both measured requests. This checks ordinary post-long-request reuse of the
same service process; it does not exercise cancellation or compare state against
an independent oracle.

The supervisor passed with minimum physical host availability of
14,392,639,488 bytes (13.41 GiB), above the preserved six-GiB floor. Engine
owner tracing recorded 52 allocations and 52 frees, with zero observed live
requested bytes at teardown for host and device owners. The CUDA peak of
9,589,487,288 bytes is only the sum of concurrently live instrumented requested
allocations; it excludes graph pools, views and uninstrumented or driver memory
and is not a physical-memory total. No virtual ranges were part of this run.

This is a single process block and an API/recovery check, not a timing,
capacity, long-context quality, cancellation-under-pressure or numerical
state-parity qualification. All raw requests, engine log, owner summary and
supervisor telemetry are retained beside this report. Reproduction:

```sh
python tools/integration/run_control.py \
  --timeout 1200 \
  --output bench/results/2026-10-11-phase3-long-short-recovery/supervisor -- \
  build/integration/venv/bin/python tools/integration/api_control_block.py \
  --config bench/results/2026-10-11-phase4-pool-workers-512-no-share/base-config.json \
  --workloads bench/results/2026-10-11-phase3-long-short-recovery/workloads.json \
  --output bench/results/2026-10-11-phase3-long-short-recovery/requests.json \
  --warmup-workloads bench/results/2026-10-11-phase3-long-short-recovery/warmup-workloads.json \
  --variant candidate --rounds 1
```
