# Q2_0 exact-entry-count grouped-kernel experiment

Date: 2026-10-31. Device: Jetson AGX Orin Developer Kit, CUDA 12.6, SM87. This experiment tests whether compile-time specialization for actual 2/3/4-entry groups removes enough per-column predication to improve NInfer's Q2_0 grouped operator. It is enabled only with `STRATA_NINFER_Q2_EXACT_N=1`; default behavior remains unchanged. Reduction order and Q2_0/Q8_1 arithmetic are unchanged. The separate `STRATA_NINFER_Q2_CTA256` experiment was unset throughout.

The model was Qwen3.8-Flash-Next-GSQ-RCO Q2_0. Shard 1 (37,623,740,192 bytes) SHA256: `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720`; shard 2 (28,800,138,432 bytes) SHA256: `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`. The source checkout was `02d146d9` plus the reported kernel change. Source-file SHA256 was `b49d75d02876d1eaa59d74d38e2867f5ecefa509909683adbcdfc6f3c18a02bb`; the built `strata` and `ninfer_q2_expert_parity` SHA256 values are in [`paired-summary.json`](paired-summary.json).

## Operator confirmation

Seven randomized independent-process pairs compared the default grouped kernel and exact-entry variant on the same layer-3/expert-94 captured Q2_0 activation. Each process ran the independent scalar oracle, grouped intermediate/output checks, repeated-input stability, and one-token plus grouped 64/128 operator timings. All 14 processes passed; output tensors had the same SHA256.

| Shape | Default NInfer median | Exact-entry median | Candidate latency change (95% paired interval) | NInfer/Strata median, default → candidate |
| --- | ---: | ---: | ---: | ---: |
| One token | 24.16 us | 24.91 us | +3.13% (+2.92%, +3.46%) | 0.973x → 1.007x |
| Grouped 64 | 4,519.69 us | 4,016.11 us | **−11.03% (−11.24%, −10.94%)** | 1.146x → 1.016x |
| Grouped 128 | 9,147.63 us | 8,067.01 us | **−11.82% (−11.83%, −11.78%)** | 1.150x → 1.014x |

Latency is lower-is-better. The 95% intervals use 100,000 bootstrap resamples of seven independent process pairs. Exact-entry specialization clears the 5% operator benefit threshold for grouped 64/128 shapes, but makes the one-token operator about 3% slower. Ratios to Strata are descriptive ratios of per-pair medians.

## Request-level screens

Two no-trace API screens tested whether the grouped operator result changes full requests. Both kept strict NInfer, 3,000 cache slots, adaptive swaps, 8K context, prefill chunk 128, MTP window 2, prompt cache off, and PCIe staging off. Only the candidate environment toggle differed. Each independent process warmed the same workload, then measured it once. The 512-token screen used two heldout retrieval prompts with a 64-token cap; the 2,048-token screen used a heldout retrieval/checksum task with a 48-token cap and natural stopping.

| Workload | Metric | Default median | Exact-entry median | Candidate advantage (95% three-pair interval) |
| --- | --- | ---: | ---: | ---: |
| NIMBUS, pp512+tg64 | Prompt TPS | 25.4 tok/s | 25.4 tok/s | 0.00% (−1.54%, +0.40%) |
| | Decode TPS | 7.3 tok/s | 7.2 tok/s | −1.37% (−2.70%, +7.25%) |
| | TTFT | 20.41 s | 20.33 s | −0.08% (−1.58%, +0.40%) |
| | Client total | 28.84 s | 28.94 s | −0.82% (−1.77%, +2.36%) |
| ORBIT, pp512+tg64 | Prompt TPS | 27.6 tok/s | 26.8 tok/s | −0.72% (−6.88%, −0.37%) |
| | Decode TPS | 7.4 tok/s | 6.8 tok/s | −6.85% (−20.55%, −1.35%) |
| | TTFT | 18.79 s | 19.32 s | −0.72% (−7.01%, −0.62%) |
| | Client total | 27.44 s | 28.07 s | −2.66% (−11.82%, −1.06%) |
| Retrieval/checksum, pp2048+tg48 | Prompt TPS | 41.9 tok/s | 42.2 tok/s | −0.24% (−0.47%, +1.44%) |
| | Decode TPS | 8.9 tok/s | 8.8 tok/s | −1.12% (−2.25%, 0.00%) |
| | TTFT | 49.21 s | 48.95 s | −0.35% (−0.70%, +1.56%) |
| | Client total | 54.16 s | 53.92 s | −0.44% (−0.53%, +1.32%) |

All 12 measured responses passed their exact-answer check, and each task's response hash matched between backend variants. Output lengths were equal within each pair: 64 tokens for both pp512 tasks and 47 naturally stopped tokens for pp2048. These are screening results with three pairs, not confirmation. The pp512 ORBIT cell regressed on decode and client time; the pp2048 cell was effectively tied. No request-level metric showed a useful benefit, so a seven-pair service confirmation is not justified. This operator optimization does not qualify an end-to-end speedup.

## Resources and decision

Minimum sampled available RAM was 24.35 GiB for operator runs, 11.42 GiB for pp512 requests and 11.58 GiB for pp2048 requests. Peak sampled swap was 1.12, 2.57 and 2.55 GiB, respectively; OOM kills were zero. CPU observations ranged 729.6–2,201.6 MHz and GPU observations 306–1,300.5 MHz. EMC readback was denied; clocks were dynamic and energy was not measured.

Keep the exact-entry path opt-in as a reproducible operator experiment; do not select it for a service profile or claim NInfer end-to-end performance. The difference between grouped operator timing and full-request results indicates the synthetic ten-group operator shape does not establish the amount of qualifying work or time savings in ordinary requests. Per-pair timing, correctness, resource observations and bootstrap intervals are recorded in [`paired-summary.json`](paired-summary.json). Raw request bodies and supervisor traces remain under `/tmp` and are not committed.
