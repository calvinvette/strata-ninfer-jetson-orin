# Q6_K warp dequantization at 16K context

Date: 2026-10-11. Device: Orin AGX, CUDA 12.6, integration candidate.
This is a seven-pair, held-out end-to-end comparison for the opt-in
`STRATA_Q6K_WARP_DEQUANT=1` dispatch path. The default is unchanged.

## Configuration and workload

The two arms used the same Qwen3.8-Flash-Next Coder IQ1_M pack, Q2_0
expert representation, MTP pack, 3,000 requested cache slots, 16,384 context,
FP16 KV, speculation window 4, prefill chunk 64, 8 pool workers, mmap experts,
and disabled CPU prefill sharing. Each fresh service process handled the same
172/64 distinct warmup and a held-out 2,048/128 incident-log request. Pair
order was randomized (`seed=2026101116`). The only arm difference was the
candidate environment variable. The request is synthetic: it includes 42
unique log records, repeated padding lines and single-token padding to reach
exactly 2,048 tokens; it is not a natural long-context quality benchmark.

The candidate binary SHA256 was
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.
The full configs, prompts, token artifacts, request streams, server logs,
tegrastats and supervisor records are retained here. Model artifacts remain
under `~/models/`.

## Results

| Measure | Median paired candidate delta | Paired bootstrap 95% interval |
| --- | ---: | ---: |
| Engine prompt + decode time | −5.33% | −7.87% to −2.67% |
| Client request elapsed time | −5.33% | −7.87% to −2.67% |
| Prompt time | −5.63% | −8.14% to −2.94% |
| Decode time | −1.54% | −19.32% to +0.72% |

Each interval resamples seven complete paired deltas 200,000 times with fixed
seed `2026101116`; see [`analysis.json`](analysis.json) and reproduce it with
[`analyze.py`](analyze.py). All seven pairs completed without an excluded cell.
Pair 6 had a slower candidate prompt and is retained. Candidate and baseline
warmup text hashes and measured output hashes matched in every pair. Both arms
returned 2,048 prompt and 128 completion tokens, 117 speculative drafts and 88
accepted drafts. Observed conversation-cache slot count was four in each arm;
the model reported 3,903 expert slots. This establishes output and speculative
count parity for these requests, not task quality.

## Persistent-state check and resources

A separate trace-enabled baseline/candidate pair used the exact same 2,048-token
input at 16K context and generated eight tokens. The returned text SHA256 was
`61d2ab3912ee3bc276fa4f5110f0b5a47500d16534e71d419ec9e4a2160d464b` in both
arms. All three accepted-prefix commit lines matched, including committed token
IDs and embedded state fingerprints. The final full state hash at layer 2055,
all full-state hash records and final GDN fingerprints matched. Raw records are
in `state-check/{baseline,candidate}/engine.log`.

The minimum sampled host `MemAvailable` over the fourteen timing processes was
13,829,439,488 bytes (12.88 GiB), above the six-GiB guard. No supervisor failed;
all observed cgroup OOM and OOM-kill counters were zero. CPU clock samples
ranged from 46 to 2,201 MHz. GPU and EMC clock frequencies were unavailable, and
energy was not measured; tegrastats rail readings are not request-scoped energy.
No clocks, power mode or services were changed.

## Interpretation

This extends the earlier 8K-context confirmation to a second prompt and 16K
configured context. It supports an end-to-end improvement for these two
specific test cells, driven mainly by prompt time. It does not establish a
general speedup, task-quality parity, energy benefit, or default dispatch
change. Keep the candidate opt-in until the remaining Phase 4 kernel/CPU and
held-out workload gates are complete.
