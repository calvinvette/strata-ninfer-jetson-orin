# ISTA IQ3_S `is_even` teacher-forced scoring — Orin — 2026-11-05

This scores the validated 21-token `is_even(n)` answer after its exact 44-token
prompt on the actual ISTA-DASLab IQ3_S GGUF model with the matching `iq3-s-pack`
and the same static 512-slot profile as the two service parity pairs. Each
backend teacher-forced all 64 next-token targets through the verifier; target
IDs were checked against the exact input sequence.

Strata and strict NInfer wrote byte-identical score records (SHA-256
`ba4bad06c25b2346084e7f1adbe3c4f980826852946cf95f47fafcafaf4d5250`) at the
instrumentation's precision: target log-probabilities to nine decimal places
and top-k values to six. The 21 answer targets had recorded total log
probability `-0.119250531`, with zero target-logprob delta at that precision,
100% top-1 agreement and 100% top-10 overlap. Both arms logged 16/480 resident
hits. These cache counters do not by themselves prove every remaining route's
owner.

The memory supervisor passed in 62.1 seconds with minimum available RAM of
19.71 GiB; clock observations were dynamic, EMC readback was denied, energy was
not measured, and the existing OOM-kill counter stayed at one. This is one
bounded teacher-forced scoring result, not bitwise logit parity or a general
quality tolerance. Instrumentation and the fixed request order exclude timing
from performance claims. Raw run logs and telemetry remain in adjacent local
directories. Model, binary and profile hashes are in [`results.json`](results.json).
