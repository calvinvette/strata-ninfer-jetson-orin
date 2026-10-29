# No-trace API screen: Q2_0 pp16384+tg128 at 32K capacity

Date: 2026-10-29. Device: Jetson AGX Orin 64GB. Model: Qwen3.8-Flash-Next
GSQ-RCO Q2_0, same GGUF shards, PLE pack, expert profile and 3,000-slot
expert cache in both arms. Source revision: `5c94944c6f98869fd8b9d1cb6c0ac3f25bfbe784`;
binary SHA-256: `fbd40926be198adc92cd9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`.

## Method

Three same-day fresh-process pairs compared the Strata expert backend with
strict NInfer at 32,768 configured context. The formatted prompt had exactly
16,384 tokens and each request generated 128 tokens. PCIe staging and prompt
cache were disabled in both arms. Tracing was disabled. Each process sent one
same-workload warmup followed by one measured streaming API request. Pair order
was randomized, though all three draws happened to run NInfer before Strata.
The measured response content and warmup content matched byte-for-byte within
each pair. This generic generation workload has no independent answer oracle;
the API screen did not capture persistent-state fingerprints.

| Pair | Order | Prompt TPS | Decode TPS | First-visible TTFT | Client total |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | NInfer → Strata | -0.12% | 0.00% | +0.19% | +0.18% |
| 1 | NInfer → Strata | +0.12% | 0.00% | -0.06% | -0.07% |
| 2 | NInfer → Strata | -0.24% | +1.14% | +0.31% | +0.19% |
| Median paired change |  | **-0.12%** | **0.00%** | **+0.19%** | **+0.18%** |

The paired 95% bootstrap intervals were -0.24% to +0.12% prompt TPS, 0.00%
to +1.14% decode TPS, -0.06% to +0.31% TTFT, and -0.07% to +0.19% client
total. All include no effect and none approaches the preregistered 5% useful
effect threshold. Given the small effects, same-order blocks, and no quality or
state oracle, this screen does not justify a confirmation campaign or an
acceleration claim.

| Arm | Prompt TPS | Decode TPS | TTFT | Client total |
| --- | ---: | ---: | ---: | ---: |
| Strata medians | 81.6 tok/s | 8.9 tok/s | 200.93 s | 215.16 s |
| Strict NInfer medians | 81.7 tok/s | 8.9 tok/s | 200.95 s | 215.14 s |

Minimum available memory across the six processes was 10.78 GiB. Peak sampled
swap was 2.58 GiB. Cgroup low/high/max/OOM/OOM-kill counters remained zero.
Observed CPU clocks ranged from 729.6 to 2,201.6 MHz and GPU clocks from 306 to
1,300.5 MHz; EMC readback was unavailable. Energy was not measured. No clock or
service settings were changed. The run is a three-pair screen for one synthetic
API shape, not broad workload or release qualification. Raw captures remain
local-only.

## Paired-effect chart

![No-trace Q2_0 API effects across screened workload shapes](no-trace-api-effects-chart/paired-effects.svg)

The combined chart includes the 1K, 4K and 16K prompt screens. Sanitized paired
values and bootstrap intervals are in
[JSON](no-trace-api-effects-summary.json) and
[CSV](no-trace-api-effects-chart/paired-effects.csv).
