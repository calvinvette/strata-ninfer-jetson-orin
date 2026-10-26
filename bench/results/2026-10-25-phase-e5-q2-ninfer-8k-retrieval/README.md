# E5 Q2_0 strict NInfer 8K retrieval and arithmetic check

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. This held-out
functional check uses an actual 8,192-token prompt and compares the corrected
Strata and strict NInfer expert backends with MTP off and static residency.

## Setup and result

The prompt places three unique codes at approximately 10%, 50% and 90% of the
context, then asks for their ordered values and the sum of their numeric
suffixes. Both backends returned the exact expected answer in 47 tokens:

```
EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768
```

Generated token IDs and all nine final persistent-state fingerprints matched.
The exact formatted prompt contained 8,192 tokens. Prompt-content SHA256 is
`ad4adce52d37ce02f0a98ab5379e74df5155f58680242179df7bded970308691`; formatted
token-ID SHA256 is
`67efae68a2fb123143bd62daa81441594fcf763c78aec5524d228f21b697d0ff`; workload
SHA256 is `ec4f0de71d0c88af72ba968d1d09f16dad718bc1986b512095da3e960ded6356`.

Both sequential fresh engines used the same Q2_0 model and PLE pack, 3,000
static expert slots, 16K context cap, FP16 KV, prefill 128 and eight workers;
adaptive swaps and MTP were disabled. Only the expert backend changed. The
Release server SHA256 was
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75` from
source revision `17a18e2310420c0614aff91b6d2b87a6a23d4a96`.

| Backend | Prompt ms | Decode ms | Generated tokens | Exact answer | Final state |
| --- | ---: | ---: | ---: | --- | --- |
| Strata | 137,002.0 | 9,860.2 | 47 | pass | reference |
| Strict NInfer | 135,164.7 | 9,929.0 | 47 | pass | matches Strata |

These are single-run functional timings, not a paired performance estimate.
The approximate differences (−1.34% prompt time and +0.70% decode time) are
not performance conclusions. This case extends the retrieval check from 4K to
8K actual input tokens; it does not qualify near-limit 16K ingestion, broader
tasks, or performance at longer contexts.

## Resources and reproduction

The supervised run lasted 328.7 seconds. Minimum available physical/admission
memory was 19,003,613,184 bytes (17.70 GiB), above the preserved 6 GiB floor.
There were 312 telemetry samples and zero sampled cgroup low/high/max/OOM/OOM-kill
events. CPU clocks ranged from 729.6 MHz to 2.2016 GHz; GPU clocks from 306 MHz
to 1.3005 GHz. EMC readback was unavailable, clocks were observed rather than
controlled, and energy was not attributed.

`evidence/` contains the exact workload and run configuration, result with
output IDs/state hashes, engine logs, supervisor summary, memory samples and
tegrastats output. The model files remain under `~/models` and are not copied
into this repository:

| Model shard | Size | SHA256 |
| --- | ---: | --- |
| `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf` | 37,623,740,192 bytes | `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720` |
| `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf` | 28,800,138,432 bytes | `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` |

Reproduce the prompt and check with:

```sh
python3 tools/integration/prepare_ninfer_long_retrieval.py \
  --tokens 8192 --output /tmp/q2-retrieval-8k
python3 tools/integration/run_control.py \
  --output /tmp/q2-retrieval-8k-supervisor --timeout 1200 --interval 1 \
  --sample-clocks -- python3 tools/integration/ninfer_q2_retrieval_check.py \
  --config bench/results/2026-10-25-phase-e5-q2-ninfer-8k-retrieval/evidence/config.json \
  --engine build/integration/e0-cuda-build/strata \
  --workload /tmp/q2-retrieval-8k/workload.json \
  --output /tmp/q2-retrieval-8k-run --compare-strata-control --run
```
