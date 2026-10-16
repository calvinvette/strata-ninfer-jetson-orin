# Q2_0 staggered four-slot overlap check — Orin — 2026-10-16

This diagnostic follows the four-slot 8K screen, which completed four distinct
retrieval tasks but observed at most two active slot states. Here, four unique
streaming requests were staggered by 0.5 seconds, with prompt lengths descending
from 1,024 to 256 tokens. That order exercises the server's shorter-waiter
prefill-yield path. Each request asked for a distinct exact code. This is a
concurrency occupancy and correctness test, not a latency or throughput
comparison.

Three fresh-service blocks ran on the same binary and four-slot Q2_0 profile.
All 12 replies used the exact requested prompt token count and contained their
own marker exactly once. `/metrics` and `/slots` both observed four occupied
slots in blocks 0 and 1. Block 2 observed at most three occupied slots, while
four requests were running and one remained outside the slots. Thus four-way
overlap was seen in two of three runs but did not pass the reproducibility gate.
The campaign status is intentionally `fail`; this does not represent an answer
quality or memory-floor failure. Do not claim reliable four-way serving from
this result. The prior equal-length 8K screen also observed at most two active
slots.

The Q2_0 service binary SHA256 was
`fd9c010cb5e126dfa1f272d6c2864830df25a67c08c5aacc69ea4c98d5c2a29b`. The
configuration requested four batch slots, 16,384 context, 3,000 expert-cache
slots, MTP4, FP16 KV and disabled adaptive swaps. The three-block campaign and
per-sample API observations are under `campaign/`; the separate pilot run is
under `run/`. Minimum host/admission availability across the supervised
confirmation was 14.66/10.19 GiB, above the six-GiB floor. Sampled cgroup
pressure and OOM counters stayed zero. Clocks remained dynamic; energy was not
attributed per request.

Reproduce from the repository root on Orin:

```sh
python3 bench/results/2026-10-16-phase7-q2-concurrency4-staggered/prepare.py
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-16-phase7-q2-concurrency4-staggered/campaign-supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-16-phase7-q2-concurrency4-staggered/campaign.py \
  bench/results/2026-10-16-phase7-q2-concurrency4-staggered/campaign
```

Four-way overlap remains unqualified. Two-slot streamed serving retains its
separate tested scope; neither result claims a latency benefit.
