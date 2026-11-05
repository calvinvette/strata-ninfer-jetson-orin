# ISTA IQ3_S `is_prime` teacher-forced scoring — Orin — 2026-11-05

This scores the same 91-token `is_prime(n)` answer that both ISTA IQ3_S
backends generated and that passed the 11-case executable oracle. The answer
was teacher-forced after its exact 50-token chat prompt. Strata and strict
NInfer covered all 140 next-token targets, including every answer token, using
the actual ISTA IQ3_S GGUF, matching `iq3-s-pack`, and static 512-slot profile.

The score files were byte-identical at the logger's precision (target
log-probabilities to nine decimals, top-k values to six; this does not establish
bitwise-equal logits). For the 91 answer targets, both recorded total log
probability `-1.116922995`; target log-probability deltas were zero at that
precision, top-1 agreement was 100%, and top-10 overlap was 100%. Both arms
logged 16/480 resident hits. This scoring parity coexists with the persistent
state mismatch reported in the [long-task report](../ista-is-prime/README.md).

The memory supervisor passed in 115.1 seconds with minimum available RAM of
19.77 GiB; sampled swap peaked at 1.84 GiB, the existing OOM-kill counter
stayed at one, clocks were dynamic, EMC readback was denied and energy was not
measured. Instrumented timings are excluded from performance claims. A first
launch failed before model startup because the helper read the prompt from the
wrong result field; the corrected fresh retry is the measurement reported here.
Raw logs and telemetry remain in adjacent local directories. Model, binary and
profile hashes are recorded in [`results.json`](results.json).
