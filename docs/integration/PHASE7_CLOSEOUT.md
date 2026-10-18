# Phase 7 closeout — bounded Orin qualification matrix

Phase 7 is complete for the specific Orin cells listed in the
[Phase 7 evidence matrix](PHASE7_MATRIX.md). This closeout records measured
capacity, retrieval and arithmetic criteria, same-service recovery, a sustained
selected-profile run, and the completed API, cancellation and teardown checks.
It does not establish general product support or promote a default.

## Exit criteria and evidence

| Plan gate | Evidence and bounded result |
| --- | --- |
| Request capacity with physical-memory telemetry | The selected Q2_0 MTP-off profile passed near-limit multi-position retrieval and same-service recovery at configured contexts 8K, 16K, 32K, 64K, 128K and 256K. Each row in the matrix records formatted prompt count, minimum host/admission availability and sample count. All sampled cells maintained at least the six-GiB floor and recorded zero cgroup pressure/OOM events. Each context is an individually tested point; interpolation is not established. |
| Long-context quality, separate from ingestion and recovery | Independent arithmetic review passed for 32K retrieval-plus-sum (`1971`), 64K arithmetic replication (`1971`), and a new held-out 128K retrieval-plus-sum task (`1980`). The 256K selected-profile cell is retrieval/recovery only. |
| Repeated API/streaming, cancellation and teardown | The selected profile passed the seven-case API protocol suite, separate decode and progress-confirmed prefill cancellation with same-service recovery, and three fresh-service teardown/reload cycles. One two-slot streamed sequence passed functional checks but was slower than serial. Four-way concurrency remains unqualified and excluded. |
| Vision and cache-reuse checks | A bounded vision smoke and three-service exact image-grounding test passed on the separate IQ1_M cohort; a larger image request passed admission but its truncated answer is excluded from quality. Q2_0 MTP4 and IQ1_M cache-reuse soaks are recorded as separate profile/cohort rows. These results do not qualify vision or cache reuse on the selected Q2_0 MTP-off profile, which disables prompt caching. |
| Thermal equilibrium and sustained service | The selected Q2_0 profile completed 101/101 exact 512-token retrieval-plus-arithmetic responses over 1,802.4 seconds. Five-minute median `tj` stabilized at 55.218 and 55.296 °C in the final ten minutes. Dynamic CPU/GPU clocks and raw board rails were logged. The rail data is not process-attributed, and the available telemetry does not support a no-throttling claim. |
| Bounded support matrix and exclusions | The matrix states the exact model cohorts, runtime settings, contexts, task criteria, memory floor, repetitions and unsupported cells. The 256K prefill took 32,851.9 seconds in one synthetic retrieval request; there is no 256K arithmetic or sustained-service result. No performance or energy win follows from these functional checks. |

## Supported scope and exclusions

The tested serving candidate is the pinned Q2_0 two-shard Coder GGUF on Orin
with FP16 KV, MTP off, 3,000 exact expert slots, prefill chunk 128, eight
workers, prompt cache disabled, adaptive swaps disabled and a 3,072-MiB
workspace reserve. Evidence covers only the exact rows and workloads in the
matrix. It does not qualify other hardware, quantizations, context points,
concurrency levels or task quality beyond those rows. It does not promote a
product default.

Adaptive IQ1_M expert migration remains unqualified because it changes
persistent state and later continuation tokens in the tested recovery
sequence; see the Phase 5 findings in [STATUS](STATUS.md). Process-attributed
energy, complete Phase 6 interaction/Pareto analysis, four-way concurrency,
large-image answer quality, and vision/cache reuse on the selected Q2_0
MTP-off profile remain outside this closeout. Phases 5 and 6 remain open.

Reopen Phase 7 if the selected model, runtime profile, context domain, supported
features or hardware scope changes, or if new evidence contradicts a listed
cell. Phase 8 may use this bounded matrix only with these exclusions and the
Phase 5/6 gates relevant to the chosen release features still stated clearly.
