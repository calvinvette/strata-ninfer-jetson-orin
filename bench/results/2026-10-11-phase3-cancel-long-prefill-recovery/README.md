# Long-request disconnect and same-process recovery — Orin — 2026-10-11

The harness opened a streamed request for the exact 2,048-token `full-chunk`
workload, closed the client response one second after the server returned HTTP
headers, and then sent a separate short request through the same owned service
process. The engine log shows it finished reading the 2,048-token prompt, then
reported zero generated tokens and `cancelled`; the short request returned the
expected `Hello Orin!` response in 12.27 seconds. This confirms cleanup and
same-process recovery after a client disconnect on a long request. The log shows
the engine consumed the full prompt before observing cancellation, so this is
not evidence that active prefill work stops immediately when the client closes.

All 52 instrumented allocation/free events balanced, and the owner parser found
zero observed live host or device allocation bytes at teardown. The concurrent
instrumented CUDA requested-byte peak was 9,589,487,288 bytes; it excludes
untracked driver and graph-pool memory and is not a physical RAM total. The
six-GiB supervisor passed with minimum host availability of 14,313,365,504 bytes
(13.33 GiB). The measured scope emitted no tokens from the canceled request and
one successful short recovery response; it does not test state parity,
cancellation under memory pressure, task quality or throughput.

The reusable bounded runner is `tools/integration/cancel_long_prefill_recovery.py`.
The result, exact request, engine log, owner summary and supervisor telemetry are
retained alongside this report. Reproduce with:

```sh
python tools/integration/run_control.py \
  --timeout 1200 \
  --output bench/results/2026-10-11-phase3-cancel-long-prefill-recovery/supervisor -- \
  build/integration/venv/bin/python tools/integration/cancel_long_prefill_recovery.py \
  --config bench/results/2026-10-11-phase4-pool-workers-512-no-share/base-config.json \
  --long-workload bench/results/2026-10-09-phase3-fullchunk-2048/workloads.json \
  --output bench/results/2026-10-11-phase3-cancel-long-prefill-recovery/cancellation.json \
  --cancel-after-s 1.0
```
