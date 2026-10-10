# Long-request then short-request recovery — Orin — 2026-10-10

The supervised candidate server handled a 3,522-token prompt with a 256-token
generation cap, then handled a separate 18-token prompt and one-token response
through the same running server and engine. Both returned HTTP 200; the long
request reached its requested output cap (`finish_reason=length`) in 44.78 s,
and the short follow-up completed in 2.01 s. The server started its engine once
and remained healthy through both requests. This is one recovery smoke, not a
latency comparison or quality test.

The six-GiB physical-memory supervisor passed with minimum `MemAvailable` of
8,389,455,872 bytes (7.81 GiB). The engine reported a 512-token prefill chunk
and an 8,192-token context. Integration events show prefill buffers, the
expert-cache allocation and MTP buffers released during orderly server
shutdown. Those owners were provisioned for the running service; the trace
does not establish per-request deallocation or identify a transient peak unique
to the long request. The short request's success after the long one is the
recovery criterion exercised here.

The harness uses the local IQ1_M candidate config, automatic expert-cache
sizing, an owned 512-token prefill workspace and loopback-only API access.
`experiment/` retains the exact modified server config, request summaries and
engine/server logs. `supervisor/` retains physical/cgroup memory samples and
tegrastats. The harness and artifacts are local integration evidence; no
production default or protocol behavior changed.
