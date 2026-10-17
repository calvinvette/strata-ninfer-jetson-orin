# Phase 7 evidence matrix

This matrix summarizes retained Orin tests for the Phase 7 plan. It records
individual tested cells, not a general product support guarantee. Phase 6 has
selected one bounded Q2_0 profile for Phase 7 qualification; that selection is
not product support or a default. The Phase 7 exit gates remain open. Each
result link contains its request artifacts, runner result and telemetry unless
noted otherwise.

## Profile selected for qualification

Q2_0, FP16 KV, 8,192 context, drafting off, 3,000 expert slots, 128-token
prefill chunks, eight workers, prompt cache disabled and adaptive swaps
disabled. The [Phase 6 profile decision](PHASE6_PROFILES.md) records the paired
latency evidence, exact-answer checks, headroom, rail-energy limits and the
selection boundary. The 8K supported-service matrix below mostly predates this
profile selection and uses different MTP settings; those rows do not by
themselves qualify the selected profile. The rows below qualify only their
listed workload cells.

## Q2_0 selected MTP-off profile

| Test | Configured context / actual prompt | Functional result | Minimum host / admission availability | Boundary |
| --- | ---: | --- | ---: | --- |
| Sustained uncached retrieval plus arithmetic, 8K | 8,192 / 512 tokens | 101/101 exact responses over 1,802 s; independent exact-answer review passed | 17.73 / 8.51 GiB | Thermal median stabilized near 55.2 °C in the final 10 minutes; dynamic clocks; raw rails only; [report](../../bench/results/2026-10-17-phase7-q2-prefill128/sustained-512/README.md) |
| Near-limit retrieval and same-service recovery, 8K | 8,192 / 7,498 tokens | Three markers once and ordered; `RECOVERED` on the same service; independent review passed | 17.96 / 11.75 GiB | One prompt/profile; [report](../../bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/README.md) |
| Near-limit retrieval and same-service recovery, 16K | 16,384 / 15,003 tokens | Three markers once and ordered; 41 output tokens; `RECOVERED`; independent review passed | 17.72 / 10.15 GiB | One selected-profile request; 611 supervised samples; [report](../../bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/README.md) |
| Near-limit retrieval and same-service recovery, 32K | 32,768 / 30,032 tokens | Three markers once and ordered; 41 output tokens; `RECOVERED`; independent review passed | 17.52 / 11.89 GiB | One selected-profile request; 1,106 supervised samples; [report](../../bench/results/2026-10-17-phase7-q2-prefill128-32k-selected-profile/README.md) |
| Held-out retrieval plus arithmetic and recovery, 32K | 32,768 / 30,040 tokens | Three markers once and ordered; suffix sum `1971`; `RECOVERED`; independent marker, arithmetic and runtime reviews passed | 17.42 / 11.48 GiB | One selected-profile task; 1,081 supervised samples; [report](../../bench/results/2026-10-17-phase7-q2-prefill128-32k-quality-mtp-off/README.md) |
| API protocols and disconnect/recovery | 8,192 / short protocol prompts; separate 7,498-token prefill cancel | Seven protocol scenarios passed; decode and progress-confirmed prefill cancellation logged; both recovered on the same service | 17.87 / 16.78 GiB | Short disconnect plus a separate cancel at 256/7,498 prompt tokens; [protocol report](../../bench/results/2026-10-17-phase7-q2-prefill128/api-cancel-recovery/README.md), [active-prefill report](../../bench/results/2026-10-17-phase7-q2-prefill128/api-prefill-cancel/README.md) |
| Fresh-service teardown and reload | 3 cycles; each used a 7,498-token prompt | Three exact marker responses; each listener and engine process stopped before the next cycle; independent review passed | 18.04 / 8.46 GiB | One retrieval workload repeated across three fresh services; [report](../../bench/results/2026-10-17-phase7-q2-prefill128/teardown-3cycle/README.md) |

## Q2_0 accepted-only MTP4

| Test | Configured context / actual prompt | Functional result | Minimum host / admission availability | Boundary |
| --- | ---: | --- | ---: | --- |
| Near-limit recall, 8K | 8,192 / 7,498 tokens | Three markers once and ordered; same-service recovery | 16.97 / 10.15 GiB | Single request point; [report](../../bench/results/2026-10-14-phase7-q2-recall/README.md) |
| Near-limit recall, 16K | 16,384 / 15,003 tokens | Three markers once and ordered; same-service recovery | 16.80 / 10.36 GiB | Single request point; same report |
| Near-limit recall, 32K | 32,768 / 30,032 tokens | Three markers once and ordered; same-service recovery | 16.36 / 10.31 GiB | Single request point; same report |
| Near-limit recall, 64K | 65,536 / 60,071 tokens | Three markers once and ordered; same-service recovery | 15.37 / 11.26 GiB | Single request point; [report](../../bench/results/2026-10-15-phase7-q2-recall-64k/README.md) |
| Near-limit recall, 128K | 131,072 / 120,149 tokens | Three markers once and ordered; same-service recovery | 13.65 / 13.19 GiB | Single request point; [report](../../bench/results/2026-10-15-phase7-q2-recall-128k/README.md) |
| Near-limit recall, 256K | 262,144 / 240,286 tokens | Three markers once and ordered; same-service recovery | 7.31 / 7.31 GiB | Single request point; lowest observed headroom in this matrix; [report](../../bench/results/2026-10-15-phase7-q2-recall-256k/README.md) |
| Held-out retrieval plus arithmetic, 32K | 32,768 / 30,040 tokens | Three codes ordered; suffix sum `1971`; recovery | 16.29 / 10.27 GiB | One task; [report](../../bench/results/2026-10-14-phase7-q2-recall/quality-replication-32768/README.md) |
| Held-out retrieval plus arithmetic, 64K | 65,536 / 60,079 tokens | Three codes ordered; suffix sum `1971`; recovery | 15.13 / 11.50 GiB | One task; [report](../../bench/results/2026-10-15-phase7-q2-quality-64k/README.md) |
| Sustained uncached retrieval, 8K | 14 requests in 30 min | All retrieval checks passed | 16.97 / 9.55 GiB | `tj` 54.5–60.1 °C; one sustained cell; [report](../../bench/results/2026-10-14-phase7-q2-recall/sustained-8k/README.md) |
| Sustained uncached retrieval, 16K | 8 requests over 30 min | All retrieval checks passed | 16.75 / 9.77 GiB | Peak scope use 18.23 GiB; [report](../../bench/results/2026-10-14-phase7-q2-recall/sustained-16k/README.md) |
| Sustained uncached retrieval, 32K | 4 requests over 2,298 s | All retrieval checks passed | 16.29 / 10.27 GiB | Peak scope use 17.73 GiB; [report](../../bench/results/2026-10-14-phase7-q2-recall/sustained-32k/README.md) |
| Prompt-cache reuse, 8K | 7,498-token prompt | 653 requests; 7,491 tokens reused; all marker checks passed | 16.93 / 10.72 GiB | Median request 2.86 s, first visible token 0.390 s; [report](../../bench/results/2026-10-14-phase7-q2-recall/cache-reuse-30m/README.md) |
| Reload and teardown, 8K | 3 fresh services; 7,498-token measured request each | All markers passed identically; listener and engine exited before reload | 16.85 / 6.90 GiB | Three sequential cycles; [report](../../bench/results/2026-10-15-phase7-q2-teardown3/README.md) |
| Streamed concurrency, 2 slots | 8K and 16K prompts | Both exact retrieval checks passed; overlap and two active slots observed | 15.66 / 7.36 GiB | No latency benefit in this pair; swaps disabled; [report](../../bench/results/2026-10-14-phase7-q2-recall/concurrency2/README.md) |
| Streamed concurrency, 4 slots | Four distinct 8K prompts | All four exact retrieval checks passed; four slots configured | 14.65 / 11.95 GiB | At most two active slot states observed; four-way gate failed; [report](../../bench/results/2026-10-15-phase7-q2-concurrency4/README.md) |
| Staggered streamed concurrency, 4 slots | Four distinct prompts, 256–1,024 tokens | All 12 exact prompt/marker checks passed in three fresh services; both APIs saw four active slots in 2/3 blocks | 14.66 / 10.19 GiB | Third block peaked at three active slots with one request outside; confirmation gate failed, no reliable four-way claim; [report](../../bench/results/2026-10-16-phase7-q2-concurrency4-staggered/README.md) |

The 256K test's 7.31 GiB minimum host availability cleared the required six-GiB
floor, with zero sampled cgroup pressure/OOM events. It took 11,557.8 seconds
for prompt processing at the engine-reported 20.8 tokens/s. It is a single
functional check, not a 256K sustained or performance qualification. Thermal
equilibrium, energy attribution and EMC clock readback were not established in
that run.

## IQ1_M opt-in MTP4

| Test | Functional result | Minimum host availability | Boundary |
| --- | --- | ---: | --- |
| Near-limit recall and recovery at 8K/16K/32K | Three markers in order and same-service recovery at each context | 12.67 GiB across context tests | One IQ1_M profile; [report](../../bench/results/2026-10-14-phase7-q6-recall/README.md) |
| 40-minute streamed cache-reuse soak | 1,579 requests, all marker checks passed | 13.34 GiB | Temperature stabilized near 76–77 °C for over 30 minutes; same report |
| Three-cycle reload/teardown | Warmup and measured request passed each cycle; listener and engine exited before reload | 13.11 GiB | Three cycles; [report](../../bench/results/2026-10-14-phase7-iq1-teardown3/README.md) |
| Bounded 56×56 vision smoke | HTTP 200; response described grid and gradient | 11.99 GiB host/effective | One small fixture; [report](../../bench/results/2026-10-14-phase7-iq1-vision/README.md) |
| Current-source exact image grounding, 224×224 | Exact quadrant counts and sum on all 3 fresh services | 11.76 GiB host/effective | One synthetic task at 16 vision tokens; not broad vision quality; [report](../../bench/results/2026-10-17-phase7-current-source-coder-iq1m-vision-count/README.md) |
| 2048×2048 image admission | HTTP 200 at 1,024 image tokens | 11.76 GiB host/effective | Answer truncated at 48 tokens; not a vision quality pass; same report |
| Held-out long-context task | Three codes at 10/50/90%, correct sum, and recovery | 12.75 GiB host/effective | One 30,040-token prompt; [report](../../bench/results/2026-10-14-phase7-q6-recall/README.md) |

## Current-source Coder IQ1_M regression

These runs use the `IQ1_M` variant from the Hugging Face repository
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, pinned to local snapshot
revision `5348543e0147355ac9cbcb031184a3546350988e`. The model shard hashes
match across the rows. This is a current-source path and context regression on
one quantization, not a comparison between quantizations or inference engines.

| Test | Configured context / actual prompt | Functional result | Minimum host / admission availability | Boundary |
| --- | ---: | --- | ---: | --- |
| Current-source retrieval and recovery | 8,192 / 7,498 tokens | Three markers in order; same-service recovery; MTP accepted 30/32 drafts | 13.25 / 13.25 GiB | One prompt/profile; [report](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m/README.md) |
| Current-source retrieval and recovery | 16,384 / 15,003 tokens | Three markers in order; same-service recovery; MTP accepted 30/32 drafts | 12.76 / 12.76 GiB | One prompt/profile; [report](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m-16k/README.md) |
| Current-source retrieval and recovery | 32,768 / 30,032 tokens | Three markers in order; same-service recovery; MTP accepted 30/32 drafts | 12.60 / 12.60 GiB | One prompt/profile; [report](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m-32k/README.md) |
| Current-source retrieval, arithmetic and recovery | 65,536 / 60,079 tokens | Three markers in order; suffix sum `1971`; same-service recovery; MTP accepted 34/39 drafts | 11.56 / 11.56 GiB | One prompt/profile; [report](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m-64k/README.md) |
| Current-source near-limit retrieval and recovery | 131,072 / 120,149 tokens | Three markers once and in order; same-service recovery; MTP accepted 28/33 drafts | 10.20 / 10.20 GiB | One prompt/profile; 6,074.8 s engine prefill; [report](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m-128k/README.md) |
| Current-source near-limit retrieval and recovery | 262,144 / 240,286 tokens | Completed; all three markers returned once and in order; same-service recovery passed | 7.44 GiB host and admission availability | One successful attempt after two intentionally interrupted attempts; 28,300 s prompt prefill; one functional point, not broad support; [report](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m-256k/README.md) |
| Current-source cache-reuse soak | 8K; 1,586 streamed requests over 40 minutes | Every response passed all three marker checks and reused 7,491 prompt tokens | 13.30 / 13.30 GiB | 31 minutes at 71.1–73.3 °C; [report](../../bench/results/2026-10-15-phase7-current-source-coder-iq1m-soak/README.md) |

## Exclusions and open gates

- The selected Q2_0 profile is qualified only for its listed 8K-context test
  cells. The tested configurations remain experimental; results do not
  promote defaults.
- Q2_0 256K has one retrieval/recovery sample and one 64K arithmetic sample,
  but no sustained 256K workload or broader task-quality suite.
- Four-way serving is not qualified. The four-slot screen completed all four
  long retrieval requests but observed no more than two active slot states. A
  staggered short-prompt confirmation observed four active slots in two of
  three processes, with all answers correct, but the third process reached only
  three; reliable four-way overlap remains unqualified.
- The large 2048×2048 IQ1_M image request passed admission, but its answer was
  truncated and is excluded from quality passes.
- IQ1_M adaptive routing can change persistent state and recovery tokens after
  swaps. Exact refill bytes and a held-out short task passed, but the numerical
  cause and task-level quality across workloads remain unresolved under Phase 5.
- Cancellation, reload, cache reuse and vision results cover only their listed
  profile, context, fixture and request points. They are not general service
  guarantees.
- Performance comparisons, energy attribution and cross-device conclusions
  require their own paired measurements; none follows from this matrix alone.

Phase 7 can close only after Phase 6 completes profile-selection work and the
remaining quality, sustained-service and support-boundary claims are explicitly
bounded.
