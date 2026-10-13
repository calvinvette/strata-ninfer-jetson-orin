# Long-context retrieval plus arithmetic task — Phase 7

This quality check used one opt-in IQ1_M profile at 32,768 configured context:
Q6_K warp-dequant, accepted-only MTP4 adaptation at cadence 4, FP16 KV, 3,000
requested expert-cache slots (3,903 actual slots), eight workers and dynamic
clocks. The model and auxiliary files remained under `~/models/`. The candidate
engine SHA256 is
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`.

The held-out prompt contained 30,040 formatted tokens with three independent
codes placed near 10%, 50% and 90%. The request asked for each code exactly
once, in order, and for the sum of their numeric suffixes. The response was
`EARLY=MAPLE-ORBIT-731, MIDDLE=COBALT-HARBOR-284, LATE=VELVET-COPPER-956, SUM=1971`.
An independent arithmetic check confirms 731 + 284 + 956 = 1,971. It used 48
completion tokens and zero cached prompt tokens. A short same-service request
then returned `RECOVERED`.

The warmup used 512 prompt tokens. The long request took 1,238.87 seconds
(prompt processing 1,235.04 seconds); the supervised process completed in
1,300.87 seconds including service startup, warmup and recovery. Minimum host
and effective availability were both 12.75 GiB under the 28-GiB cgroup limit
and six-GiB floor. Cgroup `high`, `max`, `oom` and `oom_kill` counters stayed
zero. Frequencies were observed under dynamic policy; EMC readback was denied
and energy was not measured or attributed. This is one prompt and one profile,
not a general quality score, 32K capacity guarantee, or statistical repeat.

The first attempt is retained in `attempt-01-token-count-mismatch/`. It
completed the long request, but the driver discarded the response because the
workload expected 30,032 tokens after the question was extended; engine usage
reported 30,040. It is excluded from task scoring. The corrected repeat set the
expected count to 30,040 and passed the response and recovery checks.

Both attempts retain their workload, config, result, service logs and
supervisor telemetry. `quality-review.json` independently checks each answer
field and the arithmetic oracle.
