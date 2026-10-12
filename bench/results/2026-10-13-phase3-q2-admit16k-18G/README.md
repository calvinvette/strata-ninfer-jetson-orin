# Q2_0 16K prompt admission at 18 GiB — Orin — 2026-10-13

This repeated the [16K Q2_0 admission workload](../2026-10-13-phase3-q2-admit16k-19G/README.md)
with the same candidate binary, exact formatted prompt, 32,768 configured
context, 3,000 requested expert slots, FP16 KV and one output token, under a
systemd `MemoryMax=18G` scope. The service completed one warm-up and one
measured request in the same process. Both read 16,384 prompt tokens with zero
reused tokens and returned `A`.

The six-GiB supervisor passed. Minimum host availability was 18,661,127,360
bytes (17.384 GiB); minimum effective cgroup headroom was 8,952,971,264 bytes
(8.338 GiB). The scope recorded zero OOM and OOM-kill events. The measured
request took 76.0 seconds; this single sample is descriptive, not a timing
comparison. No energy measurement or clock control was used. Instrumented
owner/state tracing was disabled for this admission cell.

This adds a successful 18-GiB cap point beside the successful 19-GiB run for
this exact workload. The effective headroom is not monotonic with the nominal
cap because page-cache and cgroup starting conditions vary. This is not a
general capacity boundary, quality result, ownership qualification or
performance claim. Raw workload, API response, capabilities, supervisor
memory/clock telemetry and engine log hash are retained; model artifacts
remain under `~/models/`.
