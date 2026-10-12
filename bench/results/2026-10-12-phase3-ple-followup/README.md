# Q2_0 PLE and Phase 3 regression follow-up — Orin — 2026-10-12

The current candidate passed the artifact-aware Q2_0 PLE oracle and the
selected ownership, memory, transfer and graph CTest set. All seven PLE stages
passed for three tokens; worst relative L1 error was `1.148e-7`, with no
non-finite values. CTest passed 19/19 and integration Python discovery passed
111/111. The six-GiB supervisor observed minimum `MemAvailable` of 24.66 GiB
during PLE and 24.53 GiB during CTest.

PLE used the real Q2_0 dense pack and GGUF shard 2/table data with synthetic
hidden state and convolution history. CTest covered shared-memory budgeting,
conversation/cache accounting, VMM, PLE, allocation refusal, platform memory,
captured-graph ownership, transfer and convolution cache contracts. This does
not qualify whole-model output quality, graph-pool pricing, or broad pressure
behavior. Dynamic clocks were sampled; energy was not measured.

Reproduction commands and raw supervisor telemetry are retained here. The
exact CTest selection is in the supervisor command metadata. Models remain in
`~/models/`; no model or build artifact was added to Git.
