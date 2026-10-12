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
  --output /tmp/q2-auto-reservation/run
```

## Randomized automatic-cache × context screen

To separate context reservation from dynamic available-memory variation, six
fresh processes were randomized across 8K and 64K configured contexts (three
per cell, seed `202610126`). Each used the same candidate, formatted prompt
(`9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`), one
generated token and 3,072 MiB workspace slack. All six passed and selected token
32. Minimum whole-board availability was 7.32 GiB. Every cell emitted the same
500 MiB prefill hold and 3,072 MiB slack hold; actual prefill-owner requested
peak was 350,079,744 bytes (333.8 MiB) in every process.

| Configured context | Auto cache slots, three processes | Median cache request | Session request | Median unique device-request peak | Minimum availability |
| ---: | --- | ---: | ---: | ---: | ---: |
| 8,192 | 11,153 / 11,002 / 10,996 | 15,209,164,800 B (14.16 GiB) | 343,102,976 B | 17,433,692,672 B | 7.32 GiB |
| 65,536 | 10,035 / 9,941 / 9,921 | 13,742,438,400 B (12.80 GiB) | 1,856,067,072 B | 17,480,159,744 B | 7.40 GiB |

The session owner grew by 1,512,964,096 bytes (1.41 GiB), and the median cache
request fell by 1,466,726,400 bytes (1.37 GiB). The median device requested
peak differed by 46,467,072 bytes (44.3 MiB). This is consistent with the
auto-cache sizing using the remaining budget after context-sized session
allocation. The small residual and within-cell cache-slot variation remain
subject to live allocator and platform state. These are unique requested
allocation identities, not physical backing; the run makes no capacity or
performance claim.

`campaign.py` preserves the randomized fresh starts and supervisor records.
`analyze.py` checks prompt/binary/output identity, repeat counts, the six-GiB
floor, cgroup OOM event counters, whole-slot cache sizes and prefill-hold
coverage. All six runs had zero cgroup OOM events. Reproduce with:

```sh
python bench/results/2026-10-12-phase3-q2-auto-reservation/campaign.py \
  --output /tmp/q2-auto-reservation-randomized-screen
python bench/results/2026-10-12-phase3-q2-auto-reservation/analyze.py \
  --campaign /tmp/q2-auto-reservation-randomized-screen/campaign.json \
  --output /tmp/q2-auto-reservation-summary.json
```
