# Q2_0 fixed route-ranked 5K-residency backend screen

Date: 2026-10-31. Device: Jetson AGX Orin (`orin1`), aarch64, SM87, CUDA
12.6. This three-pair screen asks whether NInfer's resident expert path gains
request-level performance when both backends use one identical fixed expert
map with high workload-route coverage.

## Method and scope

The held-out NIMBUS retrieval workload had 512 prompt and 128 generated tokens.
A separate untimed route-capture run recorded 122,880 routed expert selections
and 10,065 distinct layer/expert pairs. `tools/make_profile.py --no-base`
ranked those pairs by trace frequency; the 5,000 resident slots cover 85.23%
of that trace. Both backends then used the same profile with adaptive swapping
disabled. Each fresh process received one warmup and one measured request;
the pair order was randomized. Only backend selection changed within a pair.

This is an **oracle-residency diagnostic**: the profile was derived from this
same workload's routes. It is not a deployable profile, held-out profile
quality evidence, or a general workload result. The identical profile file
also means the two backends started with the same fixed resident IDs; adaptive
map variation is absent from this comparison.

The source implementation was `e781e411c93252be2351feb35468ce06ff6a16a4`;
the executable SHA256 was
`fd67288c399d895be036dab344e30caab3d081540bfc552f22dac6a5fc33644a`. Q2_0
shards, profile, route trace and PLE pack remain under `~/models/`. Their
identities and the explicit runtime controls are in
[`campaign.json`](campaign.json). Raw request text and process telemetry remain
outside Git. [`summarize_fixed_screen.py`](summarize_fixed_screen.py) produces
the sanitized paired data in [`paired-summary.json`](paired-summary.json).

## Results

| Metric | Strata median | NInfer median | Paired median effect | Paired 95% screening interval |
| --- | ---: | ---: | ---: | ---: |
| Prompt TPS | 29.17 | 29.15 | +0.01% | −1.47% to +1.08% |
| Decode TPS | 18.59 | 18.81 | +1.19% | −0.25% to +2.50% |
| First-visible TTFT | 17.67 s | 17.67 s | +0.03% | −1.46% to +1.18% |
| Client completion | 24.45 s | 24.44 s | +0.29% | −0.43% to +0.78% |

Positive paired effect favors NInfer. Effects are candidate/control ratios
for throughput and control/candidate ratios for latency; each metric is thus
positive when NInfer is faster. All six measured responses passed the exact
`NIMBUS-7319` prefix and 128-token checks and had one shared response SHA256.
Both backends reported 84.9% decode GPU-cache hits in all three pairs.

No metric reached the preregistered 5% useful-effect threshold, and the
intervals do not support a NInfer improvement. Do not run seven-pair
confirmation for this cell. With fixed residency and high route coverage, the
screen still found no material NInfer-specific API gain. This narrows the
adaptive-map caveat but does not establish why the integration lacks a gain or
exclude an effect on other workloads.

Minimum available host memory across the six measured processes was 9.11 GiB;
maximum sampled swap use was 1.71 GiB and sampled OOM-kill counters were zero.
CPU clocks ranged from 729.6 to 2,201.6 MHz and GPU clocks from 306 to
1,300.5 MHz. EMC was not readable, energy was not measured, and clocks were
left dynamic.

## Correctness-only persistent-state check

After the timing screen, one additional fresh-process pair repeated the same
warmup and measured request with final persistent-state hashing enabled. All
four responses had the same exact prefix, 128-token length and response hash.
The final GDN, PLE, tail, pooled, KV, MTP, stale, dead, pooled-full and
previous-embedding fingerprints matched across both requests and both
backends. Minimum available memory was 9.08 GiB for Strata and 9.11 GiB for
NInfer. This is one bounded final-state check; it is not accepted-prefix
parity, full byte-level state equivalence or general quality evidence. The
hashing run is separate from performance data. See
[`state-parity.json`](state-parity.json).
