# Community benchmark on Jetson AGX Orin 64 GB (JetPack 7)

Measured on 2026-11-01 by skipauthenticate. Original Qwen3.8-Flash-Next IQ3_S at a 262,144-token context on a
Jetson AGX Orin 64 GB with JetPack 7 and CUDA 13.2, using setup's configuration with file-backed experts: three runs
each at 4,096, 32,768 and 128,000 prompt tokens, recall checks at 32K and 128K, and one recall check with a prompt that
fills 92% of the window (240,212 tokens). Main limitation: one device, one server process per group of runs, and
about 1 GiB of memory margin above the 6 GiB floor of [`run_control.py`](../../../tools/integration/run_control.py)
on a machine with other processes resident.

The 2026-10-25 [context-capacity sweep](../2026-10-25-flashnext-context-capacity-sweep/README.md) already ran IQ3_S at a
262,144-token configured capacity on a 32 GB Orin with short prompts, and says it did not measure prompts that
occupy 64K–256K tokens. This report adds the 64 GB board and prompts that actually fill 128K and 256K.

This relates to [issue #1](https://github.com/calvinvette/strata-ninfer-jetson-orin/issues/1) (a 64 GB Orin). For
its two questions, see [What 64 GB changes](#what-64-gb-changes).

## Hardware and software

- Jetson AGX Orin Developer Kit 64 GB (61.4 GiB visible), 12 Cortex-A78AE cores, MAXN power mode, no clock changes.
  Storage: WD_BLACK SN850X 1 TB NVMe.
- L4T R39.2.1 (JetPack 7), kernel 6.8.12-1021-tegra, Ubuntu 24.04.5 LTS, driver 595.78 (CUDA driver API 13.2),
  CUDA 13.2 (V13.2.86) toolkit.
- Strata 0.1.41 from this repository at `7178ce40` plus the JetPack 7 setup change
  ([validation report](../2026-11-01-jetpack7-cuda13-orin-validation/README.md)): source build, engine SHA-256
  `c8434642…`.
- Background: an idle PyTorch training worker (about 3 GB RSS) and a llama-server with a 0.5B model (about 0.8 GB RSS)
  stayed resident; 2 GiB of swap was full before the runs. No other GPU work ran (a shared GPU lock was held).

## Model and configuration

- [ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF)
  at revision `ed59f920` (setup's pin), `IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-0000{1,2}-of-00002.gguf`, SHA-256
  `4c1eb2ce…` (54,817,524,224 bytes, verified after download) and `316b46f3…` (the shared n-gram shard).
- No vision. MTP draft layer from setup (`Strata-data/mtp/rt`), spec 4, `--spec-min-p 0.5`.
- Context 262,144; KV int8 (setup's choice for this context); KV streaming off (setup: "it needs ~3.6 GB of RAM beside
  the ~62 GB IQ3_S uses"); expert cache auto; prefill auto; file-backed experts (`--mmap-experts`).
- Prepared with `./setup.sh --yes --setup --family qwen --model IQ3_S --gguf-dir <models> --context 262144
  --vision no --low-ram mmap --no-start`. The only difference from setup's default configuration is
  `--mmap-experts` ([default](strata-iq3_s-setup-default.json), [used](strata-iq3_s-mmap.json)). Without it the
  engine chose file-backed experts by itself ("the 46.84 GiB expert arena does not fit available shared RAM with
  headroom"), so both start the same way; see [Memory](#memory).
- Realized expert cache: 18,348 slots, 34.94 GiB of shared RAM allocated to the GPU (75% of the 24,576 layer-expert
  pairs). Sampling: greedy (`temperature 0`), `reasoning_effort none`.

```text
python3 tools/integration/run_control.py --output <run>/supervisor --timeout 21600 --interval 2 --sample-clocks -- \
  .venv/bin/python serve/server.py --engine strata --config strata-iq3_s.json --port 18080
```

## Method

Speed: the unchanged [`benchmark.py`](../2026-09-30-community-rtx-5090/benchmark.py) of the 2026-09-30 report
(SHA-256 `1ae2942e…`): streaming chat requests built to an exact token count with the server's tokenizer and chat
template, a nonce before the filler so no prompt reuses another's prefix (reused tokens were 0 in every run), a
256-token output cap, three runs per length, one excluded warmup request per server. Prompt and decode rates are the
engine's (`/metrics`); TTFT and total time are client-side and include prompt processing.

Recall: the unchanged [`tools/needle_bench.py`](../../../tools/needle_bench.py), depths 10/50/90 at 32K and 128K and
depth 50 for the full-window prompt.

Servers, each started fresh, in this order: (1) setup's default configuration, stopped by the memory floor while
loading (see [Memory](#memory)); (2) the 4,096 and 32,768 runs and 32K needles; (3) the 128,000 runs and 128K needles;
(4) three more 4,096 runs ([data](iq3_s-4k-third-server/)), then a `262k` needle that the script skipped (its target
plus room to answer exceeds the context); (5) a `260k` needle stopped by the memory floor while an unrelated engine
compile ran on the same machine; (6) the same `260k` needle with nothing else running, which passed. Servers 2–6 used
the configuration above. The script sizes the haystack by characters, so the `260k` target produced a 240,212-token
prompt. The OS file cache was not dropped between servers. [engine.log](engine.log) covers all six.

## Results

| Prompt tokens (actual) | Reused | Generated | Runs | Prompt tok/s, median [range] | Decode tok/s, median [range] | TTFT s, median [range] | Total s, median |
| ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| 4,096 | 0 | 256 | 3 | 234.7 [227.2–248.8] | 23.7 [21.3–26.7] | 17.5 [16.5–18.1] | 28.3 |
| 32,768 | 0 | 256 | 3 | 420.5 [411.6–433.8] | 25.5 [24.0–25.7] | 78.0 [75.6–79.7] | 87.9 |
| 128,000 | 0 | 256 | 3 | 358.4 [354.3–360.9] | 12.1 [6.3–23.1] | 357.4 [354.9–361.5] | 376.0 |
| 4,096 (third server) | 0 | 256 | 3 | 237.4 [231.4–242.1] | 8.8 [7.6–25.6] | 17.3 [17.0–17.8] | 46.1 |

Recall ([32K](iq3_s-4k-32k/needles.json), [128K](iq3_s-128k/needles.json), [full window](iq3_s-full-window/needles.json)):

| Length | Depths | Found | Prompt tokens | Seconds per check |
| --- | --- | --- | --- | --- |
| 32k | 10, 50, 90 | 3 of 3 | 33,286–33,287 | 49–88 |
| 128k | 10, 50, 90 | 3 of 3 | 125,605–125,606 | 324–369 |
| 260k (full window) | 50 | 1 of 1 | 240,212 | 674 (prompt read at 356.9 tok/s) |

Per-run rows with the generated text are in `iq3_s-*/results.json`; [engine.log](engine.log) has every server's
engine output, including one `strata serve:` timing line per request.

**Decode varied widely between requests of the same length.** At 128,000 tokens the three runs decoded 12.1, 6.3 and
23.1 tok/s with nearly the same draft acceptance (148, 152 and 148 accepted of 212, 209 and 213 drafts); the third
server's 4,096-token runs decoded 7.6, 8.8 and 25.6 tok/s against 23.7 [21.3–26.7] in the first server. Prompt rates
were steady (within 4%). The cause was not isolated: the adaptive expert tier was on (setup's default), the OS file
cache was shared with the earlier long prompts, and the background processes listed above were resident. Treat the
decode medians as screening values with that spread. One 32K and one 128K needle check reused 16,384 prompt
tokens (each haystack shares a prefix with the previous one).

## Memory

[`memory_summary.py`](memory_summary.py) over `run_control.py`'s 2-second samples:

| Server | Minimum MemAvailable | Peak swap used |
| --- | ---: | ---: |
| 4K/32K runs | 6.79 GiB | 2.0 GiB |
| 128K runs and needles | 8.05 GiB | 2.0 GiB |
| 4K runs before the first full-window attempt | 7.09 GiB | 2.0 GiB |
| Full-window check, first attempt (an engine compile ran beside it) | 5.92 GiB: stopped by the 6 GiB floor after 124 s | 2.0 GiB |
| Full-window check, repeated without the compile | 7.57 GiB | 2.0 GiB |
| First start with setup's default configuration | 5.89 GiB: stopped by the 6 GiB floor 45 s after launch | 2.0 GiB |

The first start used setup's unmodified configuration. The engine chose file-backed experts by itself and sized
the same cache (18,354 slots, 34.95 GiB); while the cache filled, `MemAvailable` reached 5.89 GiB and `run_control.py`
stopped the server (`pressure_abort`, [record](iq3_s-default-config-abort/supervisor-result.json)). The next start, with
`--mmap-experts` given explicitly, made the same choices and stayed at or above 6.79 GiB. This is the same behavior
with a margin of about one GiB that varied between starts, not an effect of the flag. Without the supervisor the first
start would not have been stopped. Each `supervisor-result.json` of a completed run says `fail` / `supervisor signal 2`
because the run script stops the server with SIGINT at the end.

## What 64 GB changes

For [issue #1](https://github.com/calvinvette/strata-ninfer-jetson-orin/issues/1):

- **More hot experts.** With 64 GB, setup's automatic cache gave the GPU 18,348 IQ3_S experts (34.94 GiB) instead of a
  fixed 3,000-slot request. For Q2_0, setup's 64 GB default loads all 31.64 GiB of experts into RAM with a
  5,956-slot GPU cache; on short prompts it read 290.3 prompt tok/s and decoded 25.5 tok/s at 557 tokens, against
  64.4 and 13.0 for the 32 GB-oriented qualified profile on the same device and day (screening, three rounds;
  [validation report](../2026-11-01-jetpack7-cuda13-orin-validation/README.md#q2_0-on-the-cuda-132-build-screening)).
  That profile ran with 40 GiB available; the all-in-RAM default ran at 5–7 GiB available.
- **A Q2 model that is not the Coder.** The original Flash-Next Q2_0 (`69820c02…`) installs with
  `./setup.sh --family qwen --model Q2_0` and served the runs above.

## Correctness and limitations

- Every speed run returned 256 tokens of text about the prompt's code (stop reason `length`); quality was not scored.
- Recall results are listed above; a needle check measures recall on those inputs, not general long-context quality.
- Screening only: three runs in one server per length, not seven independent processes. One device.
- Not measured: energy, EMC clock, images, sampled decoding, concurrent requests, KV streaming, contexts beyond
  262,144, and IQ3_S without other resident processes.
