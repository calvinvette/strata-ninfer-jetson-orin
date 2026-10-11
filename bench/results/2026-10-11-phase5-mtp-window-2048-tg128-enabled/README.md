# MTP window timing screen — pp2048+tg128 — Orin — 2026-10-11

This same-day screen compares native MTP windows 2, 3 and 4 with MTP off for
the prepared 2,048-token prompt / 128-token output workload. It used three
randomized paired blocks, one warmup and one measured streamed API request per
fresh process, no trace instrumentation, prompt cache disabled, CPU prefill
sharing disabled, and the standard six-GiB physical-memory supervisor. The
source workload is the `pp2048+tg128` cell from the integration controls; the
selected, exact workload is retained in `selected-workloads.json`. The source
base config includes the explicit MTP draft path. The runner now checks that
MTP weights exist for every enabled window before it starts any process.
The candidate executable SHA256 is
`3ef80984af6f7bfee98cddeb1853b9a36be7e642d7c6ae5f2f810b4418a85f22`. Exact
model, pack, MTP and tokenizer checksums are referenced in
[`artifact-identities.json`](artifact-identities.json), which points to the
prior dated full-file identity manifest; the large weight files were not
rehashed during this timing campaign.

All 12 processes and measured requests passed. The generated API content was
identical within each MTP-off/window pair, and each pair matched actual expert
slots (3,903) and FP16 KV format. Minimum sampled host `MemAvailable` was
13.52 GiB. MTP accepted/offered 50/77, 62/130 and 69/174 draft tokens for
windows 2, 3 and 4 in every block.

| Window | Median paired decode delta | Three block deltas | Median total request delta | Median TTFT delta | Bootstrap interval for median decode delta |
| ---: | ---: | --- | ---: | ---: | --- |
| 2 | −11.22% | −11.22%, −11.22%, −11.20% | +2.77% | −0.19% | −11.22% to −11.20% |
| 3 | −26.41% | −26.42%, −26.41%, −26.41% | +8.17% | −0.17% | −26.42% to −26.41% |
| 4 | −36.50% | −36.58%, −36.48%, −36.50% | +13.20% | −0.10% | −36.58% to −36.48% |

This is a three-pair screen; the bootstrap intervals use only three
independent process pairs and are not confirmation intervals. No window is
promoted. Median decode throughput was 7.57 tokens/s off, 6.72 for window 2,
5.57 for window 3 and 4.80 for window 4. Median prompt throughput was about
36 tokens/s in every arm. This workload therefore reproduces the short-screen
direction: draft acceptance did not offset the added draft/verification cost.

CPU frequencies varied from 729 to 2,201 MHz. tegrastats reported GR3D load
from 0 to 99%, but GPU frequency and EMC frequency were unavailable; clocks
were not controlled. No energy, task quality, persistent-state, cancellation,
or long-context ingestion claim follows from this screen. The raw campaign,
per-process configurations, request records, engine logs and supervisor
telemetry are retained here. The MTP-off-only source configuration error from
the first attempt is recorded separately in the [excluded failed setup](../2026-10-11-phase5-mtp-window-2048-tg128/README.md).
The integration Python suite passed 88/88 tests, including the new workload
selection and MTP-weight preflight checks.
