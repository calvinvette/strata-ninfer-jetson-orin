# Post-fix Phase 3 checks on the current candidate — Orin — 2026-10-11

After rebuilding the candidate for the accepted-prefix QSA spare-row fix, the
artifact-aware Q2_0 PLE oracle passed all seven stages for three tokens. It
reconstructed native key bytes exactly and matched the native projection to the
independent decoded path. Worst relative L1 error was `1.148e-7`, with no
non-finite values. The fixture uses real Q2_0 layer-1 weights and table rows;
hidden state and convolution history are synthetic. This is operator evidence,
not whole-model quality or performance qualification.

The same binary passed all 19 selected Phase 3 CTests: shared memory-budget
arithmetic, conversation/cache ownership and transfer, VMM, expert-cache
allocation/refusal, native PLE reconstruction and reader, the PLE oracle,
platform admission, captured-graph ownership, convolution cache, and
conversation validation/snapshot/file paths. Minimum host `MemAvailable` was
24.63 GiB during the oracle and 24.51 GiB during CTest. Both commands ran under
the standard six-GiB physical-memory supervisor, with no floor breach.

These tests reconfirm selected contracts after the verifier change. They do not
close Phase 3's broad cgroup pressure, full model graph allocation attribution,
or remaining transfer/admission measurements. Raw output and supervisor
telemetry are retained in `supervisor/` under the two result directories
`2026-10-11-phase5-final-ple/` and this directory.
