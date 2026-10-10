# Traced API cancellation cleanup and recovery — Orin — 2026-10-10

The candidate server ran an owned loopback session with integration tracing,
automatic expert-cache sizing and the 512-token owned prefill workspace. The
existing real-model protocol harness passed all seven scenarios: three repeated
greedy requests, OpenAI streaming, Anthropic streaming, decode cancellation and
prefill cancellation. Each cancellation was followed by a successful one-token
request through the same service process. The engine started once and remained
available through both recoveries.

The supervisor observed minimum host `MemAvailable` of 8,217,530,368 bytes
(7.65 GiB), above the ordinary six-GiB floor. The owner parser found 32 observed
allocation events and 31 frees. Expert-cache (13,985,203,200-byte owner peak),
prefill (380,273,152-byte peak), MTP and verifier allocation identities had
zero live bytes at log end. Prefill also emitted 34 view events. The 235,033,088
bytes still live under the session owner belong to the still-running resident
server at log end; they are not evidence of a cancellation leak. The verifier
reported three graph instantiations, but their driver and graph-pool bytes are
not measured by this trace.

This qualifies API-level cancellation followed by service recovery for these
two short scenarios. It does not establish persistent-state parity after
cancellation, cleanup under actual physical pressure, graph memory accounting,
or recovery from an injected late workspace failure. Energy and GPU/EMC clocks
were unavailable. `supervisor/` retains process and physical-memory telemetry;
`server-run/` retains protocol responses, engine/server logs and the exact
server configuration; `owner-accounting.json` summarizes the instrumented
allocation events. `run_cancel_recovery.py` reproduces the bounded run using a
separate model config and output path.
