# Q2_0 near-256K retrieval parity — watchdog failure

Date started: 2026-10-25 23:11:24 EDT. Host: Jetson AGX Orin, CUDA 12.6,
SM87. This is a functional state/parity check, not a performance estimate.
The comparison began before midnight and continued into 2026-10-26; retain
that timing when assessing the paired measurement protocol.

## Workload and configuration

The fixture contains a 240,286-token formatted prompt and expects the held-out
retrieval/arithmetic answer in 47 generated tokens. The configured context
capacity is 262,144. Both arms use the Q2_0 artifact and PLE pack, 3,000 static
expert slots, FP16 KV, prefill 128, eight workers, and MTP disabled. Adaptive
swaps are disabled. The only configured difference between the sequential
fresh services is Strata versus strict NInfer expert execution.

The exact workload and runtime configuration are retained in `evidence/`.
Model hashes are unchanged from the [128K functional report](../2026-10-25-phase-e5-q2-ninfer-128k-retrieval/README.md).

## Interim result

The Strata control reached verifier position 240,331 and captured its 2-token
and 1-token verifier graphs. It did not produce a completed response or final
state fingerprint. The native 60-second watchdog stopped the engine at stage
`decode -1` after no progress. The captured control log is preserved in
`evidence/strata-control.log`.

The strict-NInfer arm reached the same point and failed the same way. Both
services exited with signal 6 after the watchdog reported stage `decode -1`,
no progress for 60 seconds, and verifier position 240,331. Each arm captured
the 2-token and 1-token verifier graphs. The NInfer log confirms that the
resident grouped Q2_0 dispatch was selected. Neither arm returned a completed
response or final state fingerprint; token and state parity are therefore
unavailable. This is a shared near-cap request failure, not a parity pass or a
measured backend regression.

The run lasted 5,252.6 seconds (87.5 minutes), from 2026-10-25 23:11:24 to
2026-10-26 00:38:57 EDT. Minimum available physical/admission memory was
12,124,082,176 bytes (11.29 GiB), above the preserved 6 GiB floor, with zero
cgroup low/high/max/OOM/OOM-kill events. Clock sampling was read-only; EMC
readback was unavailable. Energy was not attributed; raw tegrastats rails are
retained. The control and NInfer arms crossed midnight, so this is not a
same-day paired performance measurement.

The stop report showed all 27 expert-pool jobs complete, all eight workers
parked, and the verifier GPU flags served. That narrows the stall to work after
the verifier window, but does not identify whether final state hashing,
commit completion, or another post-window step is responsible. The native
watchdog defaults to 60 seconds and accepts `STRATA_WATCHDOG_S`; a follow-up
uses a bounded 300-second allowance to distinguish a slow finalization from a
deadlock. No runtime default is changed by that experiment.

The qualified server binary SHA256 was
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75`.

## Evidence files

- `evidence/config.json`: exact service arguments and environment.
- `evidence/workload.json`: prompt fixture and expected answer.
- `evidence/strata-control.log`: control engine output, including watchdog
  stall report.
- `evidence/ninfer-control.log`: strict-NInfer output and matching stall report.
- `evidence/results.json`: arm failures and missing parity fields.
- `evidence/supervisor-result.json`, `supervisor-stdout.txt`, and
  `supervisor-stderr.txt`: run status and wrapper output.
- `evidence/memory.jsonl.gz` and `evidence/tegrastats.txt`: losslessly
  compressed physical-memory samples and raw platform telemetry.

