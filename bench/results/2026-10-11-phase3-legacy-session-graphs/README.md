# Legacy session-graph runtime attempt — Orin — 2026-10-11

The available Orin artifact is the native IQ pack in
`~/models/strata-orin-validation/pack`. I attempted a bounded loopback API
protocol run with the current candidate while omitting `--native`, reducing
speculation to one token, and keeping the 3,000-slot request and six-GiB host
headroom guard. The engine rejected the configuration before loading weights:
the native pack requires `--native SHARD1`, speculation of at least two, and a
prefill chunk. No API request ran and no legacy session graph was captured.

This is an unsupported configuration probe, not a model/runtime failure and
not graph coverage. The ordinary protocol test could not proceed with this
pack while bypassing the native execution path. The supervised launch returned
1 after 2.13 seconds; minimum host `MemAvailable` was 26,265,399,296 bytes
(24.45 GiB), above the six-GiB floor. Logs and telemetry are retained under
`experiment/` and `supervisor/`.

Session pre/post/stage and token-session graph classes remain untested on Orin.
A valid runtime cell needs a compatible legacy-format model pack or a targeted
test fixture that constructs those graph classes directly. The existing native
pack is not a valid substitute. No source or runtime defaults changed.
