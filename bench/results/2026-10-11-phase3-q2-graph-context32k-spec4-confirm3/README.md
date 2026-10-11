# Q2_0 32K/spec4 graph backing confirmation — Orin — 2026-10-11

Three independent service startups repeated the Q2_0 native verifier graph
probe at 32,768 configured context, 256 requested expert-cache slots, prefill
512 and speculation 4. Each loopback request used the same 31-token prompt and
returned 24 tokens. The candidate binary and both Q2_0 GGUF shards were held
constant; their artifact identities are in `artifact-identities.json`.

All three requests passed. The six-GiB `run_control.py` supervisor measured
minimum host `MemAvailable` of 20.93, 20.71 and 20.84 GiB. Each process emitted
three successful CUDA graph instantiations, exactly matching three
`verifier`/`verifier-commit-graph` owner events (two verifier graphs, one
commit graph). The service stayed alive after the request.

For each process, 20 consecutive 100 ms NVMap samples immediately before the
first graph call were stable at 6,005,686,272 bytes. The 20 samples after the
last call were stable at 6,054,395,904 bytes. The measured stable-to-stable
increase was exactly 48,709,632 bytes (46.45 MiB) in all three startups. This
is repeatable process-owner backing over the graph capture/instantiate interval
and adjacent synchronous allocations; it is not an isolated graph executable
size or a complete physical-memory ledger. The prior 32K/spec4 screen measured
the same interval; the confirmation therefore strengthens repeatability for
this configuration only.

The request elapsed 14.53, 10.14 and 8.52 seconds across the three startups.
Those values are not a timing comparison: clocks were dynamic (GPU samples
306 MHz; CPU samples varied), EMC sampling was denied, and NVMap sampling and
owner tracing were enabled. Energy was not measured. No defaults or runtime
behavior changed.

Raw configurations, service results, engine traces, NVMap samples and
supervisor telemetry are retained in `../2026-10-11-phase3-q2-graph-context32k-spec4-repeat{1,2,3}/`.
The prior one-process screen is
[`2026-10-11-phase3-q2-graph-context32k-spec4`](../2026-10-11-phase3-q2-graph-context32k-spec4/README.md).
Model files and build outputs remain outside Git.
