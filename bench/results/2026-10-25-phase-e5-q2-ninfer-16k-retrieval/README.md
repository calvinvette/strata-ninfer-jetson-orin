# E5 Q2_0 strict NInfer 16K retrieval and arithmetic check

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. This held-out
functional check uses an actual 16,384-token prompt and compares the corrected
Strata and strict NInfer expert backends with MTP off and static residency.

## Setup and result

The prompt places three unique codes at approximately 10%, 50% and 90% of the
context, then asks for their ordered values and the sum of their numeric
suffixes. Both backends returned the exact expected answer in 47 tokens:

```
EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768
```

Generated token IDs and all nine final persistent-state fingerprints matched.
The exact formatted prompt contained 16,384 tokens. Prompt-content SHA256 is
`f5d2c25f800f4db9cb520cc8f91c01304ba5f5dd6e76063516de65cd04de8771`; formatted
token-ID SHA256 is
`1f188699d177b7f8d440b2f03fbbd2c15a677afa5c580c21f706fb748fe97b5b`; workload
SHA256 is `2449c1fef24e24df909a5499e36916c8e0669ddb7dea5598ae13614280399ea1`.

Both sequential fresh engines used the same Q2_0 model and PLE pack, 3,000
static expert slots, 32K context cap, FP16 KV, prefill 128 and eight workers;
adaptive swaps and MTP were disabled. Only the expert backend changed. The
Release server SHA256 was
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75` from
source revision `b893fa488b0b60f550a5b4a84e54b4ceaf53b47c`.

| Backend | Prompt ms | Decode ms | Generated tokens | Exact answer | Final state |
| --- | ---: | ---: | ---: | --- | --- |
| Strata | 213,880.5 | 10,290.9 | 47 | pass | reference |
| Strict NInfer | 217,484.6 | 9,699.3 | 47 | pass | matches Strata |

These are single-run functional timings, not a paired performance estimate.
The prompt-time difference (+1.69%) and decode-time difference (−5.75%) are
not performance conclusions. This checks retrieval from one actual 16K prompt;
it does not qualify prompts near the 32K cap, broader tasks or performance at
longer contexts.

## Resources and reproduction

The supervised run lasted 496.4 seconds. Minimum available physical/admission
memory was 18,349,694,976 bytes (17.09 GiB), above the preserved 6 GiB floor.
There were 471 telemetry samples and zero sampled cgroup low/high/max/OOM/OOM-kill
events. CPU clocks ranged from 729.6 MHz to 2.2016 GHz; GPU clocks from 306 MHz
to 1.3005 GHz. EMC readback was unavailable, clocks were observed rather than
controlled, and energy was not attributed.

`evidence/` contains the exact workload and run configuration, result with
output IDs/state hashes, engine logs, supervisor summary, memory samples and
tegrastats output. Model hashes are recorded in the [8K report](../2026-10-25-phase-e5-q2-ninfer-8k-retrieval/README.md).

Reproduce the prompt and check with:

```sh
python3 tools/integration/prepare_ninfer_long_retrieval.py \
  --tokens 16384 --output /tmp/q2-retrieval-16k
python3 tools/integration/run_control.py \
  --output /tmp/q2-retrieval-16k-supervisor --timeout 1800 --interval 1 \
  --sample-clocks -- python3 tools/integration/ninfer_q2_retrieval_check.py \
  --config bench/results/2026-10-25-phase-e5-q2-ninfer-16k-retrieval/evidence/config.json \
  --engine build/integration/e0-cuda-build/strata \
  --workload /tmp/q2-retrieval-16k/workload.json \
  --output /tmp/q2-retrieval-16k-run --compare-strata-control --run
```
