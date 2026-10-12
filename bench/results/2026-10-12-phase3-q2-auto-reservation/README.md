# Q2_0 automatic cache reservation reconciliation — Orin — 2026-10-12

One fresh supervised request exercised the current auto-cache path with the
Q2_0 pack, a 512-token formatted prompt, one generated token, 8K configured
context, the default separate 3,072 MiB workspace hold, and the six-GiB host
floor. It passed and generated token ID 32. The candidate SHA-256 was
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.

Auto sizing reported 10,408 cache slots (13.40 GiB requested). Its trace emitted
a 500 MiB prefill-workspace reservation and a separate 3,072 MiB VRAM-slack
reservation. The unique requested-allocation owner ledger recorded a 350,079,744
byte prefill peak (333.8 MiB), 343,102,976 bytes for session state, 45,738,752
bytes for the verifier, 353,894,400 bytes for pageable expert staging, and the
1,485,606,400-byte service-lifetime weight arena. The observed prefill peak was
174,208,256 bytes below its planned hold. These figures are requested payloads;
they exclude driver-private and graph-pool backing and are not summed into a
physical-memory estimate. Minimum whole-board `MemAvailable` was 9,021,898,752
bytes (8.40 GiB), above the six-GiB floor, with no OOM events.

The first harness invocation failed before launching the engine because it
omitted chat-template rendering and prepared 2,017 tokens instead of 512. The
failed setup attempt is retained under `supervisor/`; the corrected run and raw
telemetry are under `retry/`. No model request ran in the failed attempt.

This closes one actual auto-cache reservation-to-requested-owner comparison.
It does not establish physical backing, a lower-bound capacity, pressure
behavior, or a general reservation margin. The three-GiB workspace slack
remains separate from physical-RAM headroom and unchanged.

Reproduce with:

```sh
python tools/integration/run_control.py --timeout 900 \
  --output /tmp/q2-auto-reservation/supervisor -- \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-12-phase3-q2-auto-reservation/reconcile.py \
  /tmp/q2-auto-reservation/run
```
