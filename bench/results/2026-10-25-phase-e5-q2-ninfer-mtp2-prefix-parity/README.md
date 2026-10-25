# E5 Q2_0 strict NInfer MTP-2 accepted-prefix parity

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. This compares MTP
disabled and MTP-2 while holding the strict NInfer expert backend and static
expert profile constant.

## Setup and result

Both fresh private engines used the Q2_0 model and PLE pack, 8K context, FP16
KV, 3,000 profile-ranked expert slots, prefill 128, eight CPU workers, strict
`--expert-backend ninfer`, `--adapt-swaps 0` and CPU prefill share disabled.
The generated prompt was 512 tokens and both arms generated 32 tokens at
temperature zero. The MTP-2 arm used the converted Q2_0 MTP runtime and
`--spec 2 --mtp-max-t 2`.

The test passed. MTP-2 offered 17 drafts and accepted 15. MTP-off and MTP-2
produced the same 32 output token IDs and identical final state. At all 18
shared accepted-prefix boundaries, GDN, PLE, tail, dead, pooled, full pooled,
KV and prior-ple state fingerprints matched exactly:

| Generated prefix lengths | Result |
| --- | --- |
| 1, 3, 5, 7, 9, 10, 12, 14, 16, 17, 19, 21, 23, 25, 27, 29, 31, 32 | Exact state match |

The prompt SHA256 is
`ca13a79c83650d0bda01e8db5cc641308e496ff8342cb17471916c8d0a502729`. Full
per-token IDs, state traces, timings and exact arm arguments are in
[`evidence/results.json`](evidence/results.json).

## Resources and interpretation

The supervised run lasted 109.1 seconds. Minimum physical/admission availability
was 18,356,518,912 bytes (17.09 GiB), above the required 6 GiB floor. Cgroup
memory events were zero. CPU clocks ranged from 729.6 MHz to 2.202 GHz and GPU
clocks from 306 MHz to 1.3005 GHz; EMC readback was denied. Energy was not
attributed. The supervisor summary is in
[`evidence/supervisor-result.json`](evidence/supervisor-result.json); raw logs
and one-second telemetry remain in the local run directory.

Single-run prompt/decode times were 24.66/13.40 seconds for MTP-2 and
23.45/19.71 seconds for MTP-off. They are recorded as context only, not a
performance estimate. This validates accepted-prefix commits on a 512-token
prompt for one Q2_0 static profile; long retrieval/scoring tasks and repeated
continuation remain open in E5.
