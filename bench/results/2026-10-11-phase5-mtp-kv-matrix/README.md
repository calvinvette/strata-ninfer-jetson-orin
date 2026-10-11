# MTP accepted-prefix parity across KV formats — Orin — 2026-10-11

The current candidate binary (`3ef80984af6f7bfee98cddeb1853b9a36be7e642d7c6ae5f2f810b4418a85f22`)
was tested with the Qwen3.8-Flash-Next Coder IQ1_M pack and its MTP runtime.
The short workload used an exactly formatted 512-token prompt and 32 output
tokens. For each supported KV format, fresh engine processes ran MTP disabled
and windows 2, 3 and 4 with the same prompt, cache admission and no CPU prefill
sharing. All arms emitted identical token IDs, matched every shared accepted
commit boundary, and matched all nine final persistent main-model fields.

| KV format | MTP 2 accepted/offered | MTP 3 accepted/offered | MTP 4 accepted/offered | Minimum host availability |
| --- | ---: | ---: | ---: | ---: |
| FP16 | 14/18 | 17/30 | 19/39 | 13.46 GiB |
| INT8 | 14/18 | 17/30 | 19/39 | 13.54 GiB |
| Q4_0 | 13/19 | 15/34 | 16/48 | 13.46 GiB |
| K8V4 | 13/18 | 15/32 | 16/45 | 13.52 GiB |

The per-format structured traces, engine logs and six-GiB supervisor telemetry
are retained in the linked [FP16](../2026-10-11-phase5-mtp-kv-fp16/experiment/results.json),
[INT8](../2026-10-11-phase5-mtp-kv-int8/experiment/results.json),
[Q4_0](../2026-10-11-phase5-mtp-kv-q4_0/experiment/results.json), and
[K8V4](../2026-10-11-phase5-mtp-kv-k8v4/experiment/results.json) runs.

A separate 2,048-token prompt / 32-token output FP16 run also matched MTP-off
for all three windows. It matched 19, 17 and 14 shared commit boundaries for
windows 2, 3 and 4, respectively, with 14/18, 16/32 and 19/39 accepted/offered
drafts; minimum host availability was 13.34 GiB. See the [long-prompt result](../2026-10-11-phase5-spare-restore-long-prompt/experiment/results.json).

All arms passed under the six-GiB physical-memory supervisor. The integration
Python suite passed 83/83 tests, including the new KV-format option coverage.
These are correctness screens, not performance or task-quality comparisons.
Each arm is one process and the long workload is qualified only for FP16 KV.
MTP performance pairing, 128-token long-generation coverage, graph/eager
interaction, cancellation with accepted-prefix state comparison, fallback
counters and task-level quality remain open for Phase 5/6.
