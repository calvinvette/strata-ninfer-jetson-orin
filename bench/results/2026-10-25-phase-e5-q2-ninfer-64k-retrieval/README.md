# E5 Q2_0 strict NInfer 64K retrieval and arithmetic check

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. This held-out
functional check uses an actual 65,536-token prompt and compares the corrected
Strata and strict NInfer expert backends with MTP off and static residency.

## Setup and result

The prompt places three unique codes at approximately 10%, 50% and 90% of the
context, then asks for their ordered values and the sum of their numeric
suffixes. Both backends returned the exact expected answer in 47 tokens:

```
EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768
```

Generated token IDs and all nine final persistent-state fingerprints matched.
The exact formatted prompt contained 65,536 tokens. Prompt-content SHA256 is
`bee2e6d260872df0ae3079fe2afd372717fe288617650e0f21dab689ffd59ce6`; formatted
token-ID SHA256 is
`610583fbb363bad5da8bde52c4eccd779b64ba53e7890f11bac48fa188dcbe08`; workload
SHA256 is `0ab719f94047c0c3b05cba06e32e7b06f82c2793ec0818ea38128411d598dd82`.

Both sequential fresh engines used the same Q2_0 model and PLE pack, 3,000
static expert slots, 128K context cap, FP16 KV, prefill 128 and eight workers;
adaptive swaps and MTP were disabled. Only the expert backend changed. The
Release server SHA256 was
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75` from
source revision `bc6ca900`.

| Backend | Prompt ms | Decode ms | Generated tokens | Exact answer | Final state |
| --- | ---: | ---: | ---: | --- | --- |
| Strata | 684,332.8 | 11,100.5 | 47 | pass | reference |
| Strict NInfer | 657,827.9 | 17,893.0 | 47 | pass | matches Strata |

These are single-run functional timings, not a paired performance estimate.
The prompt-time difference (−3.87%) and decode-time difference (+61.2%) are
not performance conclusions. This checks retrieval from one actual 64K prompt;
it does not qualify prompts near the 128K cap, broader tasks or performance at
longer contexts.

## Resources and reproduction

The supervised run lasted 1,443.1 seconds. Minimum available physical/admission
memory was 15,779,831,808 bytes (14.70 GiB), above the preserved 6 GiB floor.
There were 1,365 telemetry samples and zero sampled cgroup low/high/max/OOM/OOM-kill
events. GPU clocks were observed dynamically; EMC readback was unavailable.
No clock controls were used and energy was not attributed.

`evidence/` contains the exact workload and run configuration, result with
output IDs/state hashes, engine logs, supervisor summary, memory samples and
tegrastats output. Model hashes are recorded in the [8K report](../2026-10-25-phase-e5-q2-ninfer-8k-retrieval/README.md).

Reproduce with `prepare_ninfer_long_retrieval.py` and
`ninfer_q2_retrieval_check.py` as shown in the [16K report](../2026-10-25-phase-e5-q2-ninfer-16k-retrieval/README.md),
substituting `--tokens 65536` and this report's `evidence/config.json`.
