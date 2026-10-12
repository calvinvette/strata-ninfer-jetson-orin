# Q2_0 16K mapped reads versus pread confirmation — Orin — 2026-10-13

This seven-pair confirmation compared mapped expert reads with asynchronous
`pread` on a distinct held-out prompt. It used the Q2_0 Qwen3.8-Flash-Next
Coder shards and associated dense PLE pack, all retained under
`~/models/strata-orin-validation/`. The upstream artifact revision recorded for
this cohort is `5348543e0147355ac9cbcb031184a3546350988e`; dense PLE and expert
profile checksums are in the retained artifact identity record linked from the
earlier 32K screen. The on-disk GGUF shards were SHA256-checked in place:

| Shard | Bytes | SHA256 |
| --- | ---: | --- |
| `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf` | 37,623,740,192 | `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720` |
| `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf` | 28,800,138,432 | `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` |

The runtime candidate SHA256 was
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.

The exact formatted prompt was 16,384 tokens with eight generated tokens, a
16,424-token context reservation, 3,000 requested and observed expert-cache
slots, prefill chunk 512, CLI speculation 2, and prompt-cache capacity 6. Both
arms used eight pread workers where applicable, staging disabled, identical
model/runtime arguments, and a randomized within-pair order (seed `20261013`).
The prompt text, token IDs, tokenizer checksums and harness prompt digest are in
[`prompt.json`](prompt.json); complete per-arm results and state/output checks
are in [`experiment-7pairs/results.json`](experiment-7pairs/results.json).

All seven pairs passed. Generated token IDs, actual cache slots, and all nine
recorded persistent-state fields matched within every pair (`L=16391`). Pread
request time was lower in all but the first pair: median 98.569 s versus
101.549 s mapped, a paired median delta of −2.23% with a bootstrap 95%
interval of −3.91% to −1.94%. Prompt time was −2.42% (−4.13% to −2.02%), while
decode time was +6.33% slower (1.87% to 9.45%). The request improvement is below
the benchmark protocol's proposed 5% promotion threshold, and the decode
regression exceeds its 5% guard. Do not promote a default from this result.

Pread had a median 2,451 process major faults versus 246,208 for mapped
(−99.0% paired median ratio effect) and a median whole-device block-read count
of 9.73 GB versus 15.03 GB (−33.1%). Fault behavior is consistent with the
different access methods. Block-device counters cover the full NVMe device and
include unrelated host reads and kernel readahead. The run did not expose
process `/proc/io` or leaf-cgroup read-byte counters. The page cache was not
flushed, so this measures the shared warm-cache conditions of these paired
runs, not cold storage behavior. Logical expert-read counts were about 156 GB
per arm and are not physical disk traffic.

The campaign ran in a user systemd scope with `MemoryMax=28G` and
`IOAccounting=yes`; the independent supervisor kept the six-GiB floor. Minimum
host `MemAvailable` was 17.76 GiB and minimum effective scope headroom was
7.34 GiB. OOM and OOM-kill counters remained zero. CPU clocks varied from
729.6 to 2,201.6 MHz and GPU clocks from 306 to 1,300.5 MHz; EMC clock readback
was unavailable. No clocks were changed. Per-request tegrastats rail estimates
are whole-board activity, include unrelated system work, and are not additive
or process-attributed; they do not establish energy per request.

[`analyze.py`](analyze.py) recomputes paired timing intervals, fault and block
read summaries, memory floor, dynamic clock ranges, and system-rail estimates
from the retained raw results and supervisor files. [`analysis.json`](analysis.json)
is its output. Supervisor and tegrastats samples are committed; engine logs are
ignored locally and their hashes are listed in `ENGINE_LOG_SHA256.txt`.
The exact command and supervisor terminal record are retained under
[`supervisor/`](supervisor/). This confirms one held-out 16K prompt/configuration;
it does not qualify cold-read behavior, other contexts or prompts, or a general
transfer-policy win. The separate 32K three-pair screen remains inconclusive.
