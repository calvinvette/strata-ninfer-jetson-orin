# Phase 3 focused regression after staging-harness updates — Orin — 2026-10-11

The current native candidate (`strata` SHA256
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`) passed
the artifact-aware Q2_0 PLE oracle and the selected 19-test Phase 3 CTest set
after the stage timing and warmup-parity harness changes. The PLE oracle passed
all seven stages for three tokens, reconstructed native key bytes exactly and
matched the native projection to the independent decoded path. Worst relative
L1 error was `1.148e-7`; no values were non-finite.

The serial CTest selection covers shared memory budgets, conversation/cache
ownership and transfer, VMM, expert-cache allocation and refusal, native PLE
reconstruction and reader, the PLE oracle, platform memory reporting, captured
graph ownership, convolution cache and conversation validation/snapshot/file
paths. All 19 passed. Both commands ran under the six-GiB effective-availability
supervisor. Minimum host `MemAvailable` was 24.32 GiB for CTest and 24.48 GiB
for PLE, with no floor breach or OOM.

Raw output and telemetry are retained in `ctest/` and `ple/`. This reconfirms
selected contracts; the warmup-associated state mismatch and broader Phase 3
graph, pressure and transfer exclusions remain open.
