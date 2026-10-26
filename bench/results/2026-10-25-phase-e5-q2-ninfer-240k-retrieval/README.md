# Q2_0 near-256K retrieval — watchdog retry and parity

Date started: 2026-10-25 23:11:24 EDT. Host: Jetson AGX Orin, CUDA 12.6,
SM87. This is a functional state/parity check, not a performance estimate.
The first comparison began before midnight and failed its 60-second native
watchdog. A bounded retry on 2026-10-26 completed both arms. These are
functional checks; the retry's single sequential pair is not a performance
confirmation.

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

The initial run lasted 5,252.6 seconds (87.5 minutes), from 2026-10-25 23:11:24 to
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

## Bounded 300-second retry — completed 2026-10-26

The same workload and qualified binary were rerun with the experiment-only
`STRATA_WATCHDOG_S=300` setting. The setting was passed to both services through
the temporary run configuration; production defaults were unchanged. The
supervised run completed from 00:41:36 to 02:09:13 EDT (5,257.2 seconds).
Both arms captured the 2-token and 1-token verifier graphs. Strict NInfer
logged selection of its resident grouped Q2_0 dispatch at layer 0
(`CUDA Q2_0/Q2_0`, dimensions 2560/640).

Both services generated 47 tokens and returned the exact expected retrieval
and arithmetic answer. All generated token IDs matched, as did all nine final
state fields: GDN, PLE, tail, dead, pooled, pooled-full, KV and previous PLE
token state, plus final length. The checker reported no failures. Minimum
available physical/admission memory was 12,284,747,776 bytes (11.44 GiB), above
the preserved 6 GiB floor; cgroup low/high/max/OOM/OOM-kill counters remained
zero.

The one-run usage diagnostics were:

| Backend | Prompt processing | Prompt rate | Decode for 47 tokens | Decode rate |
| --- | ---: | ---: | ---: | ---: |
| Strata control | 2,545,701 ms | 94.39 tok/s | 15,239 ms | 3.08 tok/s |
| Strict NInfer | 2,513,170 ms | 95.61 tok/s | 12,094 ms | 3.89 tok/s |

This sequential pair describes 1.29% higher prompt rate and 26.00% higher
decode rate for NInfer in this run. It has one observation per backend, a fixed
control-then-candidate order, and dynamic clocks; these values are not medians,
an effect estimate, or a performance qualification. The checker records prompt
processing and decode durations, not streaming client TTFT. Drafts offered and
accepted were zero in both arms. Energy was not measured; raw tegrastats rail
readings are retained and are not process-attributed energy. Read-only CPU/GPU
clock samples are retained; EMC readback was unavailable.

The successful retry shows that the earlier 60-second no-progress watchdog was
too short for this request's post-verifier completion. It does not establish a
general watchdog setting or remove the need for other long-context quality and
performance cells. The model/tokenizer and prompt fixture are the same as the
128K report; the fixture SHA256 is
`c9ddd5d6f90f1799c1eebaac34f21842c243f19895c4373fcd42c33f46ce15a5`.
The source revision was `4785b32a211925a3d0353882677cc078b980ca37`.
The qualified server binary SHA256 remains
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
- `evidence/watchdog-300/`: exact retry configuration and results, both full
  engine logs, supervisor result/output, compressed physical-memory samples
  and raw tegrastats. The workload fixture is retained once at
  `evidence/workload.json` and has the SHA256 recorded above.

