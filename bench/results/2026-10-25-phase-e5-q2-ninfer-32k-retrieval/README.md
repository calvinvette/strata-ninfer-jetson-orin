# E5 Q2_0 strict NInfer 32K retrieval and arithmetic check

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. This held-out
functional check uses an actual 32,768-token prompt and compares the corrected
Strata and strict NInfer expert backends with MTP off and static residency.

## Setup and result

The prompt places three unique codes at approximately 10%, 50% and 90% of the
context, then asks for their ordered values and the sum of their numeric
suffixes. Both backends returned the exact expected answer in 47 tokens:

```
EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768
```

Generated token IDs and all nine final persistent-state fingerprints matched.
The exact formatted prompt contained 32,768 tokens. Prompt-content SHA256 is
`e618cd12e99465a61ee1c19cb555dff07e27c9d61d1e784e58f8145fc8bac9ca`; formatted
token-ID SHA256 is
`680ab685a1289ecc750608722b87df817fda0a55a97c7b4b8c4e35caef3f22a2`; workload
SHA256 is `2b0ac2b6737e15e757a7ffee873a9b6f57d131a3e728e1422be23c9a83108e64`.

Both sequential fresh engines used the same Q2_0 model and PLE pack, 3,000
static expert slots, 64K context cap, FP16 KV, prefill 128 and eight workers;
adaptive swaps and MTP were disabled. Only the expert backend changed. The
Release server SHA256 was
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75` from
source revision `9156bd81`.

| Backend | Prompt ms | Decode ms | Generated tokens | Exact answer | Final state |
| --- | ---: | ---: | ---: | --- | --- |
| Strata | 356,843.1 | 10,385.5 | 47 | pass | reference |
| Strict NInfer | 354,732.0 | 10,193.4 | 47 | pass | matches Strata |

These are single-run functional timings, not a paired performance estimate.
The prompt-time difference (−0.59%) and decode-time difference (−1.85%) are
not performance conclusions. This checks retrieval from one actual 32K prompt;
it does not qualify prompts near the 64K cap, broader tasks or performance at
longer contexts.

## Resources and reproduction

The supervised run lasted 785.4 seconds. Minimum available physical/admission
memory was 17,696,477,184 bytes (16.48 GiB), above the preserved 6 GiB floor.
There were 743 telemetry samples and zero sampled cgroup low/high/max/OOM/OOM-kill
events. GPU clocks were observed dynamically; EMC readback was unavailable.
No clock controls were used and energy was not attributed.

`evidence/` contains the exact workload and run configuration, result with
output IDs/state hashes, engine logs, supervisor summary, memory samples and
tegrastats output. Model hashes are recorded in the [8K report](../2026-10-25-phase-e5-q2-ninfer-8k-retrieval/README.md).

Reproduce with `prepare_ninfer_long_retrieval.py` and
`ninfer_q2_retrieval_check.py` as shown in the [16K report](../2026-10-25-phase-e5-q2-ninfer-16k-retrieval/README.md),
substituting `--tokens 32768` and this report's `evidence/config.json`.
