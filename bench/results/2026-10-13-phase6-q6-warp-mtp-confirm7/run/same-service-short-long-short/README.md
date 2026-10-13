# Same-service accepted-only short/long/recovery check

This diagnostic sent the 512-token tail of the held-out incident prompt, the
full 2,048-token prompt, then the same 512-token tail again through one service
process. Each request generated 16 tokens. MTP-off and MTP4 used separate fresh
services, the current candidate binary, accepted-only adaptation every four
published tokens, and accepted-prefix plus persistent-state tracing.

The sequence completed without an engine or memory failure (minimum available
host memory was 13.244 GiB), but the test's equality gate failed: the first and
last short outputs differed in 14 of 16 token IDs, starting at token 0, under
both MTP settings. At each position in the sequence, MTP-off and MTP4 still
matched token IDs and all nine persistent-state fields. The final state of the
short recovery request differed from the first short request under each
setting, consistent with the different generated tokens. This does not by
itself demonstrate state leakage; adaptive residency can change which compute
path evaluates an expert and can change rounding.

The [delayed-swap control](../same-service-short-long-short-delayed/trace/results.json)
repeated the sequence with accepted-only tracking still on but
`--adapt-every 100000`. It passed all six cross-MTP request output/state checks
and exact first-versus-recovery output and state checks for both MTP settings.
Its six-GiB-floor supervisor retained 13.295 GiB minimum host availability with no
OOM events. This links the observed variation to swaps taking place during
the short/long/short sequence, but does not identify the CPU/GPU arithmetic or
individual residency transition responsible. Both runs are correctness
diagnostics with tracing overhead; the held-out incident prompt is a diagnostic
input, not a task-quality benchmark.

The failed run's supervisor record is retained in `supervisor/`; its
`status: fail` represents the intentionally strict output/state assertion, not
an OOM or process crash. The passing delayed control is under
`../same-service-short-long-short-delayed/`.
