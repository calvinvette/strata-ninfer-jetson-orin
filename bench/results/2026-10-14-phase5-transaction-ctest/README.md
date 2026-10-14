# Phase 5 publication and verifier regression — Orin AGX — 2026-10-13

A fresh serial focused CTest run passed the accepted-prefix publication and
usage contracts, speculative verifier parity, suffix drafter and draft policy,
coupled draft path, probabilistic sampling, and captured-graph trace coverage.

| Test | Result |
| --- | --- |
| `published_prefix_test` | Pass |
| `accepted_usage_test` | Pass |
| `spec_verify_parity` | Pass |
| `captured_graph_trace_test` | Pass |
| `suffix_drafter_test` | Pass |
| `draft_policy_test` | Pass |
| `coupled_draft_test` | Pass |
| `spec_prob_test` | Pass |

The tests cover zero/one/intermediate/full published prefixes, output clipping,
EOS behavior, accepted-usage retirement and rejected-suffix isolation, along
with the registered verifier/graph contracts. They do not by themselves prove
all model persistent state is transactionally isolated; the separate direct
state traces and model cancellation/recovery reports remain necessary evidence.

The command ran under a 28-GiB `systemd-run --user --scope` with a six-GiB
host/effective availability floor and read-only clock sampling. All eight tests
passed in 12.10 seconds. Minimum host/effective availability was 24.410 GiB;
`high`, `max`, `oom`, and `oom_kill` counters were zero. Raw CTest output,
commands and supervisor telemetry are retained in `supervisor/`.
