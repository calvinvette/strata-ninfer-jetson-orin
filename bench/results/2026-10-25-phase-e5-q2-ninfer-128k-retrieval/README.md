# E5 Q2_0 strict NInfer 128K retrieval and arithmetic check

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. This held-out
functional check uses an actual 131,072-token prompt and compares the corrected
Strata and strict NInfer expert backends with MTP off and static residency.

## Setup and result

The prompt places three unique codes at approximately 10%, 50% and 90% of the
context, then asks for their ordered values and the sum of their numeric
suffixes. Both backends returned the exact expected answer in 47 tokens:

```
EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768
```

Generated token IDs and all nine final persistent-state fingerprints matched.
The exact formatted prompt contained 131,072 tokens. Prompt-content SHA256 is
`b6608e265444304c8073088ea87beba7dd182962da0c8be0a53728963d695b54`; formatted
token-ID SHA256 is
`bc252250a5dd7105d98a5692d1f75b5aa2be8ecbabae36e93b819961f367a8c8`; workload
SHA256 is `65e83d08d1d27ab17303af9e8ebf3bac810d13c4330f5ba8332ce39fb18c9b8a`.

Both sequential fresh engines used the same Q2_0 model and PLE pack, 3,000
static expert slots, 256K context cap, FP16 KV, prefill 128 and eight workers;
adaptive swaps and MTP were disabled. Only the expert backend changed. The
Release server SHA256 was
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75` from
source revision `7bb76e19`.

| Backend | Prompt ms | Decode ms | Generated tokens | Exact answer | Final state |
| --- | ---: | ---: | ---: | --- | --- |
| Strata | 1,328,886.1 | 12,649.5 | 47 | pass | reference |
| Strict NInfer | 1,274,647.7 | 12,404.3 | 47 | pass | matches Strata |

These are single-run functional timings, not a paired performance estimate.
The prompt-time difference (−4.08%) and decode-time difference (−1.94%) are
not performance conclusions. This checks retrieval from one actual 128K prompt;
it does not qualify near-limit 256K ingestion, broader tasks or performance at
longer contexts.

## Resources and reproduction

The supervised run lasted 2,740.4 seconds. Minimum available physical/admission
memory was 12,240,797,696 bytes (11.40 GiB), above the preserved 6 GiB floor.
There were 2,591 telemetry samples and zero sampled cgroup low/high/max/OOM/OOM-kill
events. Clocks were observed dynamically, EMC readback was unavailable, no
clock controls were used, and energy was not attributed.

`evidence/` contains the exact workload and run configuration, result with
output IDs/state hashes, engine logs, supervisor summary, memory samples and
tegrastats output. Model hashes are recorded in the [8K report](../2026-10-25-phase-e5-q2-ninfer-8k-retrieval/README.md).

Reproduce with `prepare_ninfer_long_retrieval.py` and
`ninfer_q2_retrieval_check.py` as shown in the [16K report](../2026-10-25-phase-e5-q2-ninfer-16k-retrieval/README.md),
substituting `--tokens 131072` and this report's `evidence/config.json`.
