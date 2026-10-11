# Q6_K warp-dequant confirmation at 8K context

Date: 2026-10-11. Device: Orin AGX, CUDA 12.6, current integration candidate.
This is a held-out, end-to-end confirmation of the opt-in
`STRATA_Q6K_WARP_DEQUANT=1` path, not a default-dispatch change.

## Configuration and workload

Both arms used the same IQ1_M Coder pack and Q2_0 model identity, MTP pack,
3,000 requested expert-cache slots, 8,192 configured context, FP16 KV,
speculation window 4, prefill chunk 64, 8 expert-pool workers, mmap experts,
and disabled CPU prefill sharing. Each independent service process received a
separate 172-token warmup followed by the exact same formatted 512-token
held-out field-report prompt and generated 64 tokens. The arms ran in randomized
order within seven same-day pairs. The only arm difference was the candidate
environment variable. The raw requests retain the returned text and token
counts; all pairs produced identical text, 90 drafts, and 34 accepted drafts.
Observed cache capacity was 3,903 slots in every pair.

## Results

| Measure | Median paired candidate delta | Paired bootstrap 95% percentile interval |
| --- | ---: | ---: |
| Request time | −5.901% | −7.004% to −4.953% |
| Prompt time | −7.226% | −8.764% to −6.286% |
| Decode time | +0.419% | +0.194% to +2.165% |

The interval resamples seven whole paired deltas (200,000 replicates, fixed
seed `2026101182`). The request-time pair deltas are retained in
[`analysis.json`](analysis.json), which is reproducible with [`analyze.py`](analyze.py).
One baseline prompt measurement in pair 5 was 49.296 seconds, compared with
17.5–19.2 seconds in the other baseline cells; its pair is retained, not
excluded. That pair's request delta was −58.932%, and it materially affects
the mean but not the reported median. The measured advantage is primarily in
prompt processing; decode was slightly slower overall. This is evidence for
this single workload/configuration, not a general speedup or quality result.

## State and resource checks

A separate traced process pair used the same 512-token prompt and generated
eight tokens. Baseline and candidate returned identical text (SHA256
`790ff9515ebe758924ff61e6b7f7472e09518a4d9d4e05e0b085e1223e974bc2`). All
four accepted-prefix commits matched, including committed token IDs and the
full state fingerprints. Final full state was at layer 519 with GDN hash
`f6ff63db654bdbdd`. The complete raw state lines are in
`state-check/{baseline,candidate}/engine.log`; `analysis.json` retains the
exact compared lines. Both supervisors passed with minimum host
availability of 14.17 GiB (baseline) and 14.25 GiB (candidate), above the
six-GiB guard.

In the seven timing pairs, minimum host availability ranged from 14.16 to
14.34 GB (decimal values in supervisor records). Sampled CPU rates ranged
729–2,201 MHz. GPU clocks and EMC were unavailable in these raw samples, and
energy was not measured. The campaign did not pin clocks or alter power mode.

## Limits and interpretation

This confirms output and accepted-prefix state parity for one prompt, context,
cache size, and speculation configuration while showing a median timing
difference. It does not establish task quality, behavior at other prompt/context
sizes, a causal performance model, energy efficiency, or a default change.
Retain the candidate as opt-in until broader held-out workload and context
coverage plus the Phase 4 kernel/CPU qualification gates are complete.
