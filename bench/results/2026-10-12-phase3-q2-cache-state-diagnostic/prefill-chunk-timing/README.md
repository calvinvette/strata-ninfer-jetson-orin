# Q2_0 prefill-chunk paired timing screen

This trace-free seven-pair screen compares `--prefill 64` with `--prefill 512`
on the same Orin candidate, 511-token prompt, greedy eight-token continuation,
3,000 requested expert-cache slots, 640 context and 3,072 MiB workspace reserve.
One warmup process per arm preceded the measured pairs. Arm order was randomized
within each pair; `order.json` records the seed and order. There is no allocation,
state-hash or integration trace in the timing arms. The candidate/model identities
and all pair deltas are in `analysis.json`; exact commands and full telemetry are
retained under each cell directory.

All seven pairs returned the same eight-token output sequence. Chunk 512 reduced
paired median client elapsed time by 44.87% relative to chunk 64 (paired bootstrap
95% interval −49.76% to −40.45%). The paired median prompt-time delta was −15.121 s
(95% interval −15.695 to −11.998 s). Decode delta was +82 ms (95% interval −643
to +202 ms), so this screen attributes the measured request difference to
prefill. Minimum `MemAvailable` was 18.01 GiB, above the six-GiB supervisor floor.

CPU clocks varied from 729.6 to 2,201.6 MHz and GPU clocks from 306 to 1,300.5
MHz; sampled EMC stayed at 3,199 MHz. Clocks were observed, never controlled.
Energy was not measured. This is one synthetic prompt, one cache/context cell
and seven process pairs; client elapsed is from the local `StrataEngine` wrapper,
not HTTP streaming TTFT. Separate raw-state checks on the same prompt found
repeatable accepted-prefix GDN differences between prefill chunks. Therefore
matching these eight tokens and a timing gain do not qualify the chunk setting's
numerical or task quality, and no default is promoted. See the parent diagnostic
for state comparisons and owner requests.
