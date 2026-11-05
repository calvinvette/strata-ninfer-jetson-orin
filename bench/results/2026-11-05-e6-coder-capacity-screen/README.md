# Coder context-capacity screen (interim)

Date: 2026-11-05. Jetson AGX Orin, SM87, CUDA 12.6. The sweep compares the
Strata and strict-NInfer expert backends on the same Coder IQ1_M 512-token
`is_prime(n)` task while increasing configured context capacity. It uses four
order-balanced pairs per cell, a static six-GiB PCIe expert complement, static
owners, `adapt-every=0`, CPU prefill sharing off, and a six-GiB physical-memory
guard. Each output is checked against an 11-case independent function oracle.

## Completed cells

| Configured capacity | Decode TPS change, paired median (95% interval) | Prompt TPS change | TTFT reduction | Client-time reduction | Output/oracle | Min available RAM |
|---:|---:|---:|---:|---:|---|---:|
| 1K | −0.56% [−1.09%, +2.99%] | +0.46% | +0.41% | +0.02% | 89 tokens equal; pass | 14.90 GiB |
| 2K | −0.25% [−73.81%, +0.45%] | −0.90% | −0.87% | −0.55% | 89 tokens equal; pass | 14.82 GiB |
| 4K | +0.63% [−2.94%, +8.56%] | +0.36% | +0.37% | +0.26% | 89 tokens equal; pass | 14.75 GiB |
| 8K | −1.42% [−1.49%, −0.32%] | −0.32% | −0.33% | −0.80% | 89 tokens equal; pass | 14.65 GiB |
| 16K | −0.88% [−1.23%, +0.38%] | −0.16% | −0.16% | −0.17% | 89 tokens equal; pass | 14.44 GiB |

Effects are NInfer relative to Strata; positive decode/prompt changes and TTFT/client
reductions favor NInfer. The 2K cell contains one severe retained outlier, reflected
in its wide interval. No completed cell meets the 5% decode-gain criterion. Each
supervisor passed with return code zero and retained the six-GiB memory floor.

## Scope and current decision

These are context **reservations**, not long-prompt ingestion tests: every cell
uses the same 512-token prompt and 89-token generation. They do not establish
performance at a matching actual prompt length, broad task quality, or a release
profile. The evidence so far does not support a context-capacity-dependent
NInfer gain. Keep E6/E7 open and do not promote a profile. Larger configured
capacities (32K through 256K) are still running; this interim report will be
updated when the campaign terminates.

Per-cell records: [`context-1024/results.json`](context-1024/results.json),
[`context-2048/results.json`](context-2048/results.json),
[`context-4096/results.json`](context-4096/results.json),
[`context-8192/results.json`](context-8192/results.json),
[`context-16384/results.json`](context-16384/results.json). Supervisor summaries
are adjacent under `supervisor-{capacity}/result.json`; raw telemetry and arm logs
remain local and are not part of this interim report.
