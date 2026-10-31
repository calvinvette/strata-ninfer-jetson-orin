# Q2_0 cache-size screens at 8K capacity

Date: 2026-10-31. Device: Jetson AGX Orin Developer Kit (`orin1`, Linux
5.15.148-tegra, aarch64, NVIDIA driver 540.4.0, CUDA 12.6). Host-reported
physical memory is 32,187,883,520 bytes. Model: Qwen3.8-Flash-Next GSQ-RCO
Q2_0. Both screens used a 512-token prompt, 64 generated tokens, temperature
0, 8,192-token context reservation, one warmup and one measured request per
process, prompt cache off, PCIe staging off, prefill 128, eight workers, MTP
window 2 with no drafts accepted/offered (`mtp_max=0`, draft counters zero),
3 GiB workspace reserve, 6 GiB resident budget and the existing 9 GiB runtime
headroom setting. Tracing was disabled. The test did not exercise near-limit
context ingestion.

## Artifact and map identity

The binary was built in Release mode with `-O3 -DNDEBUG` and CUDA architecture 87. The runtime executable SHA-256 was
`76ec8f095a2fb44edad9e2ebfec38378ea6a601076beb90ec06bfd2b12e8cdfc`; its
source code is `fc9b84b9` (no `src/` or `include/` changes through the current
reporting commit). Model and auxiliary artifact hashes are reused from the
verified same-host identity record: native shard
`69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720`, PLE
shard `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`,
PLE pack `a43d7d0b69525335f4b000d5197a1d3aefcd3c0014fc3e12b3455e0a5d827ba2`,
PLE index `c758314d495a1261d06a806b1c415596dfabe62e0cbf44ce592dc84c53229ccd`,
and expert profile `b3e62120218cd96d175a0547530158869177dd2164b22b40f32bea7d7e85fb8c`.

The profile is a static rank list with no eviction. Hashes below cover the
ranked `(layer, expert)` pairs used to construct each cache map; both backends
reported the same slot count and profile at startup. The 4,000-slot profile
prefix hash is `6edcb2fedb58c628fc954a3ac581816dfb3453e3474a158b33cf98cffa1f4e85`.
The 3,000-slot prefix hash is `ea9288dd40eedfaecd799054bab3192ee1b5b922b7f790869a53fdc3aa267a01`.
These are profile-derived map identities, not an independently dumped runtime
ID array.

## 4,000-slot backend screen

Three randomized independent-process pairs compared Strata with strict NInfer
at 4,000 slots. All six processes passed, with identical startup configuration,
profile-derived map identity and response text. All warmup and measured text
hashes were `4a7ec1ebd61dc2be1dee07887644a5891e034bd488088155171f3fcb6eb69e85`.
The request counters reported 23,356/30,720 decode cache hits (76.0%) in every
measured arm.

| Metric | Strata median | NInfer median | Paired NInfer effect (faster is positive) | Paired 95% bootstrap interval |
| --- | ---: | ---: | ---: | ---: |
| Prompt TPS | 31.26 tok/s | 31.10 tok/s | -0.21% | -4.72% to +1.81% |
| Decode TPS | 9.03 tok/s | 9.33 tok/s | +3.38% | +0.73% to +13.64% |
| First-visible TTFT | 16.56 s | 16.62 s | -0.29% | -4.88% to +2.44% |
| Client total | 23.50 s | 23.23 s | +0.04% | -2.46% to +5.33% |

No median reaches the preregistered 5% useful-effect threshold. This does not
justify seven-pair confirmation for the backend substitution at this cache
size. The descriptive client-total 95th percentile was 24.43 s for Strata and 23.99 s for NInfer (three independent process observations per arm). The full-precision paired observations are in
[`4k-backend-paired-summary.json`](4k-backend-paired-summary.json).

## 3,000 versus 4,000 slots with NInfer held fixed

A separate randomized three-pair screen changed only the static cache size
within strict NInfer. Pair order was 3K→4K, 4K→3K, 3K→4K. All six processes
passed; all measured requests returned 64 tokens, and all warmup/measured text
hashes were identical across configurations. The 3K arm reported 22,321/30,720
cache hits (72.7%); the 4K arm reported 23,356/30,720 (76.0%). Cache allocation
rose from 3,955 MiB to 5,273 MiB.

| Metric | 3,000-slot median | 4,000-slot median | Paired 4K advantage | Paired 95% bootstrap interval |
| --- | ---: | ---: | ---: | ---: |
| Prompt TPS | 30.39 tok/s | 31.64 tok/s | +4.10% | +1.95% to +6.38% |
| Decode TPS | 8.85 tok/s | 9.44 tok/s | **+6.33%** | **+5.61% to +6.91%** |
| First-visible TTFT | 17.01 s | 16.37 s | +3.75% | +1.91% to +5.93% |
| Client total | 24.08 s | 23.01 s | +4.44% | +3.32% to +5.71% |

Decode TPS is the nominated primary for this decode/cache screen. All three
paired decode effects exceed 5%, and the three-block paired bootstrap interval
is above zero. Prompt TPS, TTFT and client total also improve; none regresses by
more than 5%. This is sufficient to advance the cache-size comparison to a
seven-pair held-out confirmation, not to qualify the 4K profile. The bootstrap
interval is discrete with only three pairs and should be read as a screen.
The responses are from a synthetic completion prompt and have no independent
quality oracle. The next confirmation must use held-out retrieval prompts and
check the expected answer as well as completion behavior.

Descriptive client-total p95 was 24.17 s for 3K and 23.11 s for 4K (n=3 independent process observations per configuration). Drafted and accepted speculative tokens were zero in every measured request. The full-precision observations, profile-prefix map hashes, and paired
intervals are in [`cache-size-paired-summary.json`](cache-size-paired-summary.json).

## Resources and limits

The minimum process-level available RAM across both campaigns was 9.23 GiB in
the 4K backend screen and 10.15 GiB in the cache-size screen. The cache-size
screen's peak sampled swap was 1.94 GiB; sampled cgroup OOM-kill counts were
zero. The 4K backend screen's peak swap was 1.94 GiB, also with zero OOM kills.
Clock reads were observation-only: CPU frequencies ranged 729.6–2,201.6 MHz,
GPU frequencies 306–1,300.5 MHz; EMC readback was denied. Clocks remained
dynamic. Raw tegrastats logs include temperatures and named rails, but energy
was not attributed to requests or presented as whole-board energy. No clock,
service or system settings were changed.

## Decision

Keep NInfer opt-in. The 4,000-slot backend comparison is tied at the end-to-end
screen threshold. The 3K-to-4K cache-size change shows a promising decode
throughput screen result but needs held-out correctness and seven-pair
confirmation. No release profile or general quality claim follows.
