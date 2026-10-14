# Q2_0 real-service MoE activation capture — Orin — 2026-10-14

This experiment added a bounded, opt-in capture at Strata's multi-token expert
dispatch boundary. The record contains a verifier-row FP32 activation, all
top-k expert IDs, and the finalized owner for each route. It records no token
text and does not alter the expert arithmetic. The capture code is disabled
unless `STRATA_CAPTURE_MOE_PATH` is set.

The Q2_0 artifact and PLE pack were already in
`/home/calvin/models/strata-orin-validation/`; no model was downloaded or copied
into Git. Both service runs used the Q2_0 accepted-only MTP4 8K configuration
and stayed under a 28-GiB cgroup ceiling with the six-GiB host-availability
floor. The GGUF identity is `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0`, split into
`Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf` (37,623,740,192 bytes)
and `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf` (28,800,138,432
bytes); the native PLE pack is `q2-ple-pack`. The parity utility reads expert
weights from the second shard.

| Check | Result | Minimum host availability |
| --- | --- | ---: |
| 8K retrieval capture | Three expected markers returned in order; same-service `RECOVERED` check passed. Captured warmup and retrieval rows at layer 0; dispatch 48 is the retrieval row and all ten routes, including expert 333, were CPU-owned. | 16.79 GiB |
| Short v2 capture smoke | Service started, returned a response, and validated two layer-0 rows of 2,560 finite values with ten route IDs and owners each. Expert 2 was on VRAM in row 0. | 16.95 GiB |
| CPU/GPU parity, expert 333 | Captured retrieval activation; relative L1 `9.85e-8`, 5,586/7,680 output words differ bitwise; both routes vs float reference `9.57e-3`. | 24.50 GiB |
| CPU/GPU parity, expert 2 | Captured short-service activation; relative L1 `1.03e-7`, 5,691/7,680 output words differ bitwise; both routes vs float reference `1.21e-2`. | 24.56 GiB |
| Native focused CTests | 17/17 passed, including expert multi-token and native expert parity format cases. | 24.48 GiB |
| Post-change Q2_0 PLE oracle | 7/7 stages passed; worst relative L1 `1.148e-7`. | 24.53 GiB |
| Post-change selected Phase 3 CTests | 15/15 passed. | 24.45 GiB |
| Post-change integration Python discovery | 134/134 passed. | 24.50 GiB |

Both retained captures use the JSONL schema `strata-moe-dispatch-v2`. The
`dispatch` field is a process-local call ordinal, not a verifier-window ID.
Route kind is `-1` CPU, `0` primary VRAM/foresight slot, `1` PCIe, or `2`
peer/helper GPU. The short smoke captured exactly two rows, including one
VRAM-owned and nine CPU-owned routes.

The two actual activations demonstrate small CPU/GPU operator differences for
one CPU-served expert and one VRAM-served expert. The full retrieval still
passed its task oracle and recovery. This evidence does not reproduce
the accepted-prefix state transaction or explain the adaptive-residency state
drift; it does not show that the two route results were mixed within one
verifier token.

Reproduction commands, using the checked-in Q2_0 service workload and pack:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output supervisor --timeout 2400 --interval 1 -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/run_recall_case.py \
  --config bench/results/2026-10-14-phase5-moe-activation-capture/config-full-v2.json \
  --workload bench/results/2026-10-14-phase7-q2-recall/workloads/workload-8192.json \
  --warmup-workload bench/results/2026-10-14-phase7-q2-recall/workloads/warmup-512.json \
  --output full-v2-run

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output v2-smoke-supervisor --timeout 1200 --interval 1 -- \
  python3 bench/results/2026-10-14-phase5-moe-activation-capture/run_capture_smoke.py \
  --config config.json --output v2-smoke

build/integration/candidate/native_expert_parity \
  /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf \
  --expert 2 --activation-f32 v2-smoke/activation-vram-2560.f32 0

build/integration/candidate/native_expert_parity \
  /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf \
  --expert 333 --activation-f32 activation-retrieval-2560.f32 0
```

The captured activation is converted from the JSONL record to raw little-endian
float32 for the standalone parity tool. The tool checks an independent float
reference and the CPU/GPU routes; it repeats the same captured activation in
three operator rows for its existing width-invariance checks.

The shared C++ changes require current-source CUDA, HIP and SYCL compile checks.
CUDA and live service checks passed on Orin. The current-source HIP/SYCL
compile/link run on maestro1 is retained in `backend-maestro1/`; it is compile
evidence only, with no GPU runtime claim. Both backends built `strata` and
`native_expert_parity` with one job. HIP completed 84/84 target steps and SYCL
125/125. Each `strata --help` exited 0 with the backend runtime libraries set
up. Each parity executable's no-argument usage check exited 2 as expected.
This checks loading and CLI dispatch only; neither utility exercised an
accelerator. HIP `strata` SHA256 is
`a8024415efe13ecd8d8d054db28b9ada9d58923a16512d181d558ed20cd2a7e6`; SYCL
`strata` SHA256 is
`b320d93b66d807519af95c07c1a87382228344710894cf276b4c05b9f4f6ca28`.

The first SYCL configure had parity disabled, so it did not generate the
`native_expert_parity` target. That target-selection attempt did not compile
anything; the configure was corrected to enable parity and the complete
125-step build then passed. The retained build log includes oneAPI and DPCT
warnings, plus the GCC include-path preference warning at link. No warning was
an error.

The CUDA service executable SHA256 is
`abef7698554590b3e28036844da207c0c58c291167204bee9dff248d80304b32`; the
`native_expert_parity` executable SHA256 is
`e82cd68769b0c777349142d355a461e7fdd600d3e065f6d3dce594c8e73956f0`. The
capture source SHA256 is `8aec317048a6b4531313206137773ad2bba0650cdf8ca5282bfcdb485f3bddcf`,
and the captured-activation parity source SHA256 is
`1613466c6a08f61e8fdb962f04439e1f9521e5744f14febcc5e8976d1126962b`.
The complete report artifact tree, including backend build logs, has its own
`SHA256SUMS.txt` manifest.
