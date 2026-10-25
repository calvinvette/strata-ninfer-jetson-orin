# E5 Q2_0 strict NInfer MTP-4 accepted-prefix parity

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. The test compared
MTP disabled and MTP-4 while holding the NInfer expert backend, static cache
profile, model, prompt, KV format and workers constant.

## Setup

Both arms used the Q2_0 model/PLE pack, an 8K context, FP16 KV, 3,000
profile-ranked expert slots, prefill 128, eight CPU workers, strict
`--expert-backend ninfer`, `--adapt-swaps 0`, MTP batch 1 and CPU prefill share
disabled. The prompt contained 512 tokens and both arms generated 32 tokens at
temperature zero. MTP-4 used the converted Q2_0 runtime and
`--spec 4 --mtp-max-t 4`; the control removed MTP while keeping the same strict
NInfer expert backend. Each arm ran sequentially in a fresh private engine.

The prompt SHA256 is
`ca13a79c83650d0bda01e8db5cc641308e496ff8342cb17471916c8d0a502729`. The
Release binary SHA256 was
`527d7833ac398b82368c37b1001ed1adfdd245730b28482a90fef28851161be8`.

## Result

MTP-4 offered 33 drafts and accepted 23. Both arms produced identical 32-token
IDs and identical final main-model state. At every shared accepted-prefix
boundary, the main-model state fingerprints matched across GDN, PLE, tail, dead,
pooled, full pooled state, KV and previous PLE state:

| Generated prefix length | State |
| ---: | --- |
| 1, 5, 8, 9, 10, 14, 17, 21, 25, 27, 31, 32 | Exact match |

The full test output, including each token sequence, state fingerprint, timing,
and engine arguments, is in [`evidence/results.json`](evidence/results.json).
This directly checks accepted-prefix publication against the serial MTP-off
execution with the same NInfer backend.

## Resources and interpretation

The supervised run lasted 99.8 seconds. Minimum physical/admission availability
was 18,003,820,544 bytes (16.77 GiB), above the preserved 6 GiB floor. Cgroup
memory events were zero. CPU clocks ranged from 729.6 MHz to 2.202 GHz and GPU
clocks from 306 MHz to 1.3005 GHz; EMC readback was denied. Energy was not
attributed. The supervisor summary is in
[`evidence/supervisor-result.json`](evidence/supervisor-result.json); raw logs
and one-second telemetry remain in the local run directory.

One run measured MTP-4 prompt/decode times of 23.49/11.60 seconds and MTP-off
times of 24.20/19.17 seconds. These single-run durations are included for
context only; this is a correctness test, not an MTP performance estimate or an
NInfer-vs-Strata comparison. Long retrieval/scoring tasks, repeated continuation
and broader cancellation boundaries remain open in E5.
