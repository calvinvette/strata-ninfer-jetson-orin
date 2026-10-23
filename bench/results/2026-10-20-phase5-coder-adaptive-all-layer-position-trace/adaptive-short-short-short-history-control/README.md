# Repeated-short adaptive history control — Orin — 2026-10-20

This same-service pair tests whether the intervening 2,048-token request is
necessary for the observed adaptive accepted-state divergence. Each arm issued
three identical 512-token prompts in order: initial, intermediate and recovery.
The delayed-control and adaptive-cap8 arms ran in randomized order with a
12-token generation limit. The initial and final requests are compared directly;
the intermediate request tests a short-request-only history.

Both arms passed the 28-GiB supervisor. Minimum host/admission availability was
14.24 GiB for adaptive and 14.20 GiB for delayed control; sampled cgroup memory
events stayed at zero. The model was the
pinned Coder IQ1_M GGUF and PLE pack. The executable SHA256 is recorded in
`campaign.json`; the source worktree was at `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`.

All 12 initial and recovery token IDs matched in both arms. Delayed control's
accepted-state and per-layer GDN fingerprints matched at every prefix. In the
adaptive arm, state and GDN fingerprints first differed at zero-based prefix 4
between the initial and intermediate requests, and remained different through
prefix 11. The intermediate and recovery requests then matched state, GDN and
token IDs exactly. At captured positions 505–511, activation inputs and expert
IDs matched across requests while adaptive owner placement changed. At position
505 the owner map changed on both request transitions without a selected
activation or expert-ID difference. The delayed route, activation and state
traces were exact.

This shows that an intervening long request is not required to reproduce the
adaptive state difference in this short/short/short sequence. It does not
identify which owner-dependent operation or earlier state write causes the
difference, establish a general migration failure rate, or measure performance.
The same-day short/long/short repeat is retained in
[`../adaptive-short-long-short-repeat-seed20261083/`](../adaptive-short-long-short-repeat-seed20261083/);
it showed the same accepted-prefix pattern. Raw traces, API responses,
supervision telemetry, commands and comparisons are retained here.
