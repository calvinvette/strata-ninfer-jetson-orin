# Strata-backend Q2_0 cache-capacity ablation

Date: 2026-10-31. Device: Jetson AGX Orin, CUDA 12.6, SM87. This three-pair counterbalanced screen held the Strata expert backend fixed and compared 3,000 versus 4,000 expert-cache slots. Both settings retain the default adaptive expert swaps. It reuses the same two heldout tokenizer-verified 512-token retrieval/checksum prompts and 64-token generation limit as the NInfer cache-capacity confirmation. Context was 8,192 tokens; prefill chunk 128, MTP window 2, prompt cache off, PCIe staging off, eight workers, resident budget 6 GiB, workspace reserve 3 GiB, host reserve 9 GiB. Pair order was 3K→4K, 4K→3K, 3K→4K. Only cache capacity changed.

The CUDA binary SHA256 was `a870afb388809691edd0ac844dd5b104b6a50fdbbd92baf555cbca13969516dd`; source revision was `8dc1f868`. All six processes and 24 warmup/measured requests passed. Each measured answer began with its exact retrieval value and each emitted 64 tokens. The runs were not a broad quality evaluation.

## Paired effects

Positive means 4K is faster for throughput and lower latency for TTFT/client time. Intervals bootstrap the three paired processes (100,000 resamples); this is screening evidence.

| Heldout prompt | Metric | 3K median | 4K median | 4K advantage (95% interval) |
| --- | --- | ---: | ---: | ---: |
| NIMBUS | Prompt TPS | 24.7 tok/s | 21.8 tok/s | −8.50% (−12.10%, +0.93%) |
| | Decode TPS | 7.0 tok/s | 7.6 tok/s | +16.92% (−2.86%, +22.86%) |
| | First-visible TTFT | 20.96 s | 23.67 s | −8.37% (−12.08%, +0.96%) |
| | Client total | 29.99 s | 32.14 s | −0.49% (−9.64%, +5.05%) |
| ORBIT | Prompt TPS | 26.2 tok/s | 21.9 tok/s | −9.54% (−16.41%, −5.73%) |
| | Decode TPS | 7.1 tok/s | 8.5 tok/s | +20.83% (+19.72%, +42.37%) |
| | First-visible TTFT | 19.79 s | 21.53 s | −8.97% (−15.80%, −5.70%) |
| | Client total | 28.56 s | 30.74 s | +0.88% (−7.08%, +2.91%) |

Measured GPU expert-cache hit rates rose from 61.4% to 72.6% on NIMBUS and from 61.4% to 74.2% on ORBIT. This provides evidence that increased cache capacity with adaptive swaps can improve decode on the Strata backend too; the effect is not exclusive to NInfer. It comes with slower prompt processing and TTFT in this small sample, while client-total changes remain near zero. The 4K policy therefore does not pass the project's combined 5% improvement / 5% regression gate. The positive decode result is workload-specific and not an end-to-end product gain.

## Resources and interpretation

Minimum sampled available host RAM was 10.06 GiB; peak sampled swap was 2.70 GiB and sampled OOM kills were zero. CPU observations ranged 729.6–2,201.6 MHz, GPU 306–1,300.5 MHz; EMC readback was denied. Clocks were dynamic and energy was not attributed. Memory limits and clock settings were unchanged.

The result supports a cache-policy explanation for decode-rate changes, but the three-pair sample is too small to quantify a backend-by-capacity interaction. No seven-pair confirmation is warranted for this profile because prompt/TTFT regressions exceed budget and client total is tied. Per-pair values, output hashes, resource measurements and interval calculations are in [`paired-summary.json`](paired-summary.json). Raw requests and supervisor logs remain in `/tmp/e6-strata-cache-ablation3/`.
