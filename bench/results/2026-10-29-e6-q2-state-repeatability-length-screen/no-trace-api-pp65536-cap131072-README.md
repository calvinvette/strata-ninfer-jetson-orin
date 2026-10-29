# No-trace API screen: Q2_0 pp65536+tg128 at 131K capacity

Date: 2026-10-29. Device: Jetson AGX Orin 64GB (`orin1`, Linux aarch64,
kernel 5.15.148-tegra, NVIDIA driver 540.4.0, CUDA 12.6). Model: Qwen3.8-
Flash-Next GSQ-RCO Q2_0. Source revision used to build the executable:
`5c94944c6f98869fd8b9d1cb6c0ac3f25bfbe784`; executable SHA-256:
`fbd40926be198adc92cd9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`.
The current documentation checkout is `ab22096983c49abd5b7d900ff9584028f6421a5f`.

The two Q2_0 GGUF shards were verified by SHA-256:

- Native shard: `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720`
- PLE shard: `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`
- PLE dense pack: `a43d7d0b69525335f4b000d5197a1d3aefcd3c0014fc3e12b3455e0a5d827ba2`
- PLE index: `c758314d495a1261d06a806b1c415596dfabe62e0cbf44ce592dc84c53229ccd`
- Expert profile: `b3e62120218cd96d175a0547530158869177dd2164b22b40f32bea7d7e85fb8c`
- Tokenizer chat template: `12827f24b742ea4e80cdc12dbcf9622227056b9f797252a3149263d4f9aaadce`
- Tokenizer vocabulary: `4ba64f0332abcfb0b600b7df1537d1e836e68009d5fb7cdb77339738dc6365c4`
- Tokenizer merges: `4ba698529766c7a2f5052083ea10cdf2485577f5237a332ee291054eb11e3332`
- Tokenizer token types: `5088c8c298fc06af8382ddb3b76c888703ac2634e82263b97eedcc2ad202738b`

## Method and limitations

Three same-day independent-process pairs compared the Strata expert backend
with strict NInfer at 131,072 configured context. Each request used an exactly
65,536-token formatted prompt and generated 128 tokens. Both arms used the same
GGUFs, PLE pack, expert profile, tokenizer, 3,000-slot expert cache, 8 workers,
MTP window 2, 3 GiB workspace reserve, and 6 GiB available-memory admission
floor. Prompt cache, PCIe staging and request tracing were disabled. Each fresh
process sent one warmup followed by one measured streaming API request. The
benchmark explicitly set `temperature=0` (greedy). Pair order was Strata →
NInfer, NInfer → Strata, then Strata → NInfer. Clock rates were observed
without setting clocks.

All six processes passed and warmup response text matched byte-for-byte across
the two backends in all three pairs. However, measured text differed between
Strata and NInfer in every pair. The first differing character followed a
common prefix of 52, 613 and 325 characters in pairs 0, 1 and 2. Within the
same process, measured text also differed from warmup in five of six cases
(both requests emitted 128 tokens); the only exact repeat was Strata in pair
1. Since decoding was greedy, these differences are not explained by
stochastic sampling. They expose a repeatability or persistent-state issue
that this timing-only run did not instrument. No independent task-quality
oracle or persistent-state fingerprints were captured.

Prompt TPS and first-visible TTFT describe the common prompt workload, but
decode TPS and client total include backend-dependent generated text paths and
must not be read as isolated kernel effects. The results do not establish
quality-equivalent generation or qualify a production profile.

| Pair | Order | Prompt TPS change | Decode TPS change | First-visible TTFT change | Client total change |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | Strata → NInfer | -0.93% | +3.16% | +0.93% | +0.86% |
| 1 | NInfer → Strata | +1.13% | -56.63% | -1.07% | +1.46% |
| 2 | Strata → NInfer | -0.20% | +21.58% | +0.25% | -0.24% |
| Median paired change |  | **-0.20%** | **+3.16%** | **+0.25%** | **+0.86%** |

The 95% paired bootstrap intervals were -0.93% to +1.13% for prompt TPS,
-56.63% to +21.58% for decode TPS, -1.07% to +0.93% for first-visible TTFT,
and -0.24% to +1.46% for client total. Every interval includes zero; no median
meets the 5% useful-effect screen. The wide decode interval reflects a 3.63 tok/s
NInfer result in pair 1 against 8.37 tok/s for Strata; this outlier was not
reproduced by the other two pairs. Since the measured token paths differed,
the decode and client-total effects are confounded and cannot qualify the
backend. Median arm rates were 86.79/86.50 prompt
tok/s and 8.16/8.21 decode tok/s (Strata/NInfer); median first-visible TTFT was
755.62/758.36 s and median client total was 773.52/777.62 s. No confirmation
campaign or acceleration claim is justified.

Minimum available RAM across the six processes was 7.12 GiB; peak sampled swap
was 6.33 GiB. Cgroup low/high/max/OOM/OOM-kill counters were zero. Observed CPU
clocks ranged from 729.6 to 2,201.6 MHz and GPU clocks from 306 to 1,300.5 MHz;
EMC readback was unavailable. Energy was not measured; tegrastats rails are not
process-attributed energy. The sum of supervised process durations was 157.5
minutes. The campaign driver exited after both arms in block 1, before launching
block 2. Block 2 was completed directly with the pre-generated block workload,
planned Strata-then-NInfer order, identical control settings, and normal
supervisor records; the campaign manifest was reconciled from those records.

This is a three-pair screen for one synthetic 64K API workload, not a full E6
exit or release qualification. The full output hashes, common-prefix lengths,
within-process repeatability results, arm timings, resource summaries,
bootstrap summaries and artifact identities are in the
[combined sanitized data](no-trace-api-effects-summary.json). Raw request,
server, memory and tegrastats captures remain local-only.

## Paired-effect chart

![No-staging Q2_0 API paired effects across screened workload shapes](no-trace-api-effects-chart/paired-effects.svg)

This combined plot covers 1K, 4K, 16K, 32K and 64K prompt screens. The 64K
cell’s measured outputs differed in all three pairs; the plot and source data
identify output matching by cell. It remains screening evidence only.
