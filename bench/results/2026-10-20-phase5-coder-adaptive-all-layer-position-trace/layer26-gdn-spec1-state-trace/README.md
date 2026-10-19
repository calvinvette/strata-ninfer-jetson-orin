# Single-token verifier-window localization attempt — Orin — 2026-10-20

This attempted to split the first differing position-506 two-token commit by
rerunning the same-service sequence with `--spec 1`. The native Coder pack
validates its runtime arguments before loading weights and requires `--spec T`
with `T >= 2`; the engine exited at argument validation in 3.36 s. No model
execution or state capture occurred. The failed cell is retained as an explicit
unsupported measurement; it does not change the supported native-pack path.

The successful two-token-window committed-state trace is documented in
`../layer26-gdn-commit-state-trace/`. Further single-token localization will
need a diagnostic that observes the prefix inside a supported two-token window.
