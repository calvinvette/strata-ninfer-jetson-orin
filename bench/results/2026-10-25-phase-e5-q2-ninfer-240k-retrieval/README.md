# Q2_0 near-256K retrieval parity — in progress

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

The strict-NInfer arm is still running. Current supervisor telemetry through
2026-10-26 00:10 EDT shows a minimum of 11.29 GiB available physical memory,
above the preserved 6 GiB floor, and zero cgroup OOM events. No paired parity
conclusion is available until the strict-NInfer arm completes and, if needed,
the control arm is retried with the native watchdog setting understood.

## Evidence files

- `evidence/config.json`: exact service arguments and environment.
- `evidence/workload.json`: prompt fixture and expected answer.
- `evidence/strata-control.log`: control engine output, including watchdog
  stall report.

