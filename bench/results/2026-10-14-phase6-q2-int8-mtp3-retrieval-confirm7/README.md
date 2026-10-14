# Q2_0 int8-KV MTP3 held-out confirmation — Orin — 2026-10-14

This seven-block Phase 6 confirmation tested the int8-KV MTP3 candidate against
MTP-off on a distinct held-out retrieval-plus-arithmetic task. Each block
randomized two fresh services. Both used an 8,192-token context, the same
3,000-slot expert profile, eight pool workers, captured graphs, static expert
residency, no prompt cache, an exact 512-token prompt, and a 48-token generation
allowance. All 14 measured responses naturally stopped at 47 tokens and exactly
returned:

```
EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768
```

An independent suffix calculation verifies `618 + 243 + 907 = 1768`. The
engine reported int8 KV and 3,000 actual expert slots in all cells. MTP3 offered
34 drafts and accepted 29 in each block. The prompt text SHA256 is recorded in
[`analysis.json`](analysis.json); the current binary SHA256 is
`5a72dbad8a79782a7cd778ab222fdcfe82f3665b25923767215f0f465bbcd213`. Exact
SHA256 identities for the Q2_0 shards, PLE pack, MTP weights, tokenizer and
expert profile are in [`model-checksums.txt`](model-checksums.txt). All weights
remained under `~/models/`.

| Measure | MTP-off median | MTP3 median | Paired change (95% interval) |
| --- | ---: | ---: | ---: |
| Decode throughput | 5.272 tok/s | 5.717 tok/s | +8.83% (+7.34%, +10.63%) |
| Prompt throughput | 26.366 tok/s | 26.672 tok/s | +0.36% (−1.41%, +3.43%) |
| Client TTFT | 19.719 s | 19.514 s | −0.16% (−3.06%, +1.52%) |
| Client total request | 28.519 s | 27.431 s | −2.82% (−4.68%, −1.23%) |

Intervals bootstrap the seven whole within-block paired ratios (5,000
resamples). Decode throughput improved and request time fell for this task;
prompt throughput and TTFT were unresolved. This is held-out confirmation for
one short retrieval workload and this fixed int8/cache/context profile. It does
not qualify other prompts, KV formats, windows or adaptive-residency behavior,
and does not change a default.

The runs used a 28-GiB cgroup ceiling and six-GiB admission floor. Minimum
physical host and effective admission availability were 16.911 and 6.211 GiB;
all sampled cgroup low/high/max/OOM/OOM-kill counters were zero. Read-only GPU
clock samples during requests ranged from 306 to 1,300 MHz; EMC frequency was
unavailable because debugfs access was denied. Tegrastats `tj` range and
per-request clock observations are in `analysis.json` and the raw logs. Clocks
were dynamic and energy was not attributed to requests.

The [seven-pair campaign](run-retry1/) retains per-block randomization,
requests, engine logs, capabilities, memory samples, clocks and tegrastats.
Run `python3 bench/results/2026-10-14-phase6-q2-int8-mtp3-retrieval-confirm7/analyze.py`
from the repository root to repeat the strict configuration, exact-answer,
resource and paired-timing checks. The separate [`run/setup-attempt.txt`](run/setup-attempt.txt) records two
pre-launch wrapper mistakes; no service ran there. It is not part of the
measured campaign.
