# Q2_0 three-cycle service reload and teardown check — Orin — 2026-10-15

This Phase 7 lifecycle check ran three fresh loopback Strata services with the
Qwen3.8-Flash-Next-GSQ-RCO Q2_0 model and accepted-only MTP4 at 8,192 configured
context. Each cycle completed a distinct 512-token warmup and a 7,498-token
three-marker retrieval request. All measured responses returned the three
expected codes once and in order, used 41 completion tokens, and had identical
answer text across all three starts. Before the next cycle, the harness verified
the listener had closed and no new Strata engine process remained. All three
cycles passed.

The Strata binary SHA-256 was
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`. The
28-GiB supervisor sampled once per second for 545 records over 573.0 seconds.
Minimum host/admission availability was 16.85/6.90 GiB. Sampled cgroup `low`,
`high`, `max`, `oom` and `oom_kill` counters remained zero. GPU observations
ranged from 306 MHz to 1,300.5 MHz. No clock controls were changed; EMC
readback was unavailable and energy was not request-attributed.

The first attempt used the inherited 48-token generation cap. The model stopped
normally after its 41-token answer, but the generic API checker classified that
as an incomplete workload and halted the sequence after cycle 1. That attempt
is retained under `campaign.json/` and did not indicate a listener or process
leak. The successful retry used an explicit 41-token cap and is under
`campaign-retry/`. Both attempts and the per-second memory samples are retained;
the memory JSONL is gzip-compressed. `SHA256SUMS.txt` covers the saved files.

This checks sequential load/request/teardown for one Q2_0 profile and one
retrieval task. It does not test simultaneous services, long-duration reload
stress or other model formats.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase7-q2-teardown3/supervisor-retry \
  --timeout 2400 --interval 1 --sample-clocks -- \
  python3 tools/integration/repeated_service_teardown.py \
  --config bench/results/2026-10-15-phase7-q2-teardown3/config.json \
  --workloads bench/results/2026-10-15-phase7-q2-teardown3/workload-41.json \
  --warmup-workloads bench/results/2026-10-15-phase7-q2-teardown3/warmup.json \
  --output bench/results/2026-10-15-phase7-q2-teardown3/campaign-retry \
  --cycles 3 --first-port 18860
```
