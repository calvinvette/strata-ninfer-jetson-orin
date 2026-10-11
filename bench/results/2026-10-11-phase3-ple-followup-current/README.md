# Current-checkout Q2_0 PLE and Phase 3 ownership follow-up — Orin — 2026-10-11

The artifact-aware Q2_0 PLE oracle passed all seven stages for a three-token
block. It reconstructed the native Q2_0 key bytes exactly and matched the
native projection against the independently decoded path; worst relative L1
error was `1.148e-7`, with no non-finite values. The Q2_0 table and layer-1
weights are real; hidden state and convolution history are synthetic. The
PLE executable SHA256 is `021239e6fa46ba81b1d1c011b10a71a6386ae420d14cc25cc496a8558efaed30`.
The run's minimum host `MemAvailable` was 24.64 GiB. Raw output and telemetry
are in `supervisor/`.

The current candidate also passed all 15 selected accounting and owner CTests
sequentially under the six-GiB supervisor. Coverage included shared-memory
budget, conversation cache/state, VMM, Q2_0 PLE key and reader, per-layer and
segmented expert cache, refusal and pinned fallback, platform memory admission,
and convolution cache. Minimum host availability was 24.60 GiB. The exact
CTest command and output are retained in
`../2026-10-11-phase3-ctest-followup-current/supervisor/`.

Integration Python unittest discovery passed 91/91. These reruns reconfirm
selected contracts on the current checkout; they do not close Phase 3's broader
pressure, graph attribution, transfer-interaction or held-out workload gates.
No runtime default changed, and there is no whole-model quality or speed claim.
