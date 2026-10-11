# Seven-pair CPU expert-pool worker confirmation — Orin — 2026-10-11

This randomized seven-block timing confirmation compares 4 versus 8 CPU
expert-pool workers on the held-out 1,069-token prompt and eight-token output.
It uses the IQ1_M Coder model with Q2_0 MTP, CPU prefill sharing disabled, a
fixed requested 3,000-slot cache (3,903 admitted slots), and the current
candidate engine SHA-256
`5de05658f9b91f1b5a416b49285bc21fbc441f0fb0747b45d9f2f840fbbccb47`.
Each worker/count block used an independent process and a separate 1,069-token
warmup. Timing runs disabled all engine, state and allocation tracing.

All 14 timed API requests passed; every run admitted the same cache capacity
and produced the same output hash. Eight workers had a median request time of
32,824.9 ms versus 33,337.2 ms for four workers, a 1.54% median reduction.
Median prompt time was 32,081.2 vs 32,382.6 ms, while median decode time was
733.8 vs 950.0 ms. The seven paired deltas for four relative to eight workers
were `+0.83, −0.32, +1.76, +2.16, +1.55, +1.91, +0.80%`; the harness's
paired-bootstrap 95% interval for the median was +0.80% to +1.91%. Thus 8
workers were faster in six of seven pairs, but the request-level effect is
small and limited to this workload/configuration.

A separate traced correctness check on the same current binary ran two
independent processes per worker count. All four cells matched the same output,
final persistent-state fingerprints and full accepted-prefix token/state trace;
all five verifier commits were represented. Trace timings are excluded. This
refreshes the earlier held-out state check, which used a different binary.

The six-GiB physical-memory supervisor passed the 24-minute campaign. Minimum
host `MemAvailable` was 14,009,331,712 bytes (13.05 GiB); the trace correctness
follow-up minimum was 14,337,454,080 bytes (13.35 GiB). Tegrastats observed
CPU frequencies from 729 to 2,201 MHz, junction temperatures from 47.8 to
58.5 C and GR3D utilization from 0% to 99%. GPU/EMC clocks were unavailable;
energy and thermal equilibrium were not qualified.

This confirms the 8-worker advantage for one held-out prompt in the
CPU-sharing-disabled policy. It does not establish task quality, interaction
with other prefill-sharing modes or a general worker default, so no default
changed. The 512-token screen and accepted-prefix state results are documented
separately in the linked earlier reports in `docs/integration/STATUS.md`.

`experiment/results.json` retains all paired samples and interval calculations;
`state-experiment/results.json` retains trace equality. Raw per-cell configs,
API outputs, engine logs, supervisor memory samples and tegrastats are retained
under the two experiment/supervisor trees. The exact config, workload and model
workload are copied here for reproduction. Model artifact checksums for the same
IQ1_M/MTP artifacts are retained in the [prefill-share control manifest](../2026-10-11-phase4-gdn-prefill-share-control/model-artifact-identities.json);
the paths in that manifest match this run's config. Model files and build
products remain outside Git.
