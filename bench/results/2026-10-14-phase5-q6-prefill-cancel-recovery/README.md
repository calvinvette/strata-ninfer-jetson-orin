# IQ1_M long-prefill cancellation and recovery

This supervised check exercised accepted-only MTP4 termination during a real
long prompt, then sent a short request through the same service process. It
passed both steps. The 7,498-token retrieval request was disconnected one
second after the stream opened. The engine had completed its first 64-token
prompt chunk at 9.709 seconds and logged the request as canceled with zero
generated tokens. The service then returned the exact recovery response
`Hello Orin!` in 11.09 seconds and remained alive through the check.

The run used the Phase 7 IQ1_M Coder artifact, Q6_K warp dequant, accepted-only
adaptive swaps at cadence 4, MTP4, FP16 KV, requested cache 3,000 (capability
report: 3,903 actual slots), 8K context reservation and the existing prompt
cache setting of six slots. It ran on Orin with dynamic clocks. The harness
enabled trace logging for cancellation diagnosis, so these times are not
performance measurements. The request canceled before generation; accepted-
prefix parity and per-layer persistent state were not dumped in this run.
The base IQ1_M model shard checksum is
`e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad`; the PLE
shard checksum is
`316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.

`run_control.py` passed inside a 28-GiB systemd scope. Minimum host availability
and minimum effective admission headroom were both 12.95 GiB, above the six-GiB
floor. The supervisor returned zero; no OOM event or kill was recorded. Raw
request, server, engine, memory and tegrastats logs are retained in this folder.

This adds one long-prefill MTP4 cancellation/recovery cell for the IQ1_M profile.
It does not cover cancellation at multiple prefill positions, mid-chunk
termination, decode cancellation, allocation failure, alternate cache/context
settings, state-bit parity after cancellation or broader API quality. Phase 5
remains open.

Reproduce under the same supervisor settings with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output bench/results/2026-10-14-phase5-q6-prefill-cancel-recovery/supervisor \
    --timeout 900 -- \
    python3 tools/integration/cancel_long_prefill_recovery.py \
      --config bench/results/2026-10-14-phase7-q6-recall/config-8192.json \
      --long-workload bench/results/2026-10-14-phase7-q6-recall/workloads/workload-8192.json \
      --output bench/results/2026-10-14-phase5-q6-prefill-cancel-recovery/result.json \
      --cancel-after-s 1.0
```
