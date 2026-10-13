# Q6 prefill-chunk × cache-budget screen

This three-block randomized screen crossed prefill chunks of 32 and 128 tokens
with `--expert-cache` arguments of 3,000 and 5,000. The cache argument is a
budget in largest-expert-blob equivalents, not a literal slot count. It used
the Orin IQ1_M Q6_K warp-dequant, accepted-only MTP4 profile, FP16 KV, 8K
context, eight workers, prompt cache disabled and no `STRATA_TRACE`. The fixed
workload was 512 prompt tokens and 64 generated tokens. Each of the 12 fresh
services ran one warmup and three measured requests; all 36 measured requests
passed with exact prompt/output counts and zero cache reuse.

All cells passed under a 28-GiB cgroup ceiling and six-GiB available-host
floor. Minimum host availability across the campaign was 8.29 GiB; cgroup OOM
and OOM-kill counters remained zero. Actual cache slots were 3,903 for every
3,000 budget run and ranged from 5,378 to 6,519 for the 5,000 budget setting.
The raw per-cell allocation and telemetry records are retained beside this
report.

| `--expert-cache` argument | Prefill chunk | Actual slots by block | Median prompt tok/s by block | Median decode tok/s by block | Median request ms by block |
| ---: | ---: | --- | --- | --- | --- |
| 3,000 | 32 | 3,903 / 3,903 / 3,903 | 20.7 / 20.8 / 20.9 | 18.7 / 18.3 / 18.5 | 28,104 / 28,034 / 27,851 |
| 3,000 | 128 | 3,903 / 3,903 / 3,903 | 61.5 / 61.7 / 61.5 | 19.3 / 19.4 / 19.3 | 11,654 / 11,604 / 11,640 |
| 5,000 | 32 | 5,513 / 6,489 / 6,519 | 24.5 / 27.2 / 27.5 | 20.0 / 19.9 / 20.0 | 24,088 / 22,051 / 21,833 |
| 5,000 | 128 | 5,378 / 6,519 / 6,315 | 67.6 / 78.1 / 73.2 | 19.3 / 19.6 / 19.9 | 10,778 / 9,838 / 10,200 |

Values are median timings within each service; the three randomized blocks are
the independent repetitions. Chunk 128 improved median prompt throughput in
all six paired block comparisons: +194%, +197%, and +194% at budget 3,000, and
+176%, +187%, and +166% at budget 5,000. Median request time fell by 58.2–
58.6% at budget 3,000 and 53.3–55.4% at budget 5,000. Decode-rate changes
were smaller and changed direction across cache budgets: +3.2–6.0% at 3,000
and −3.5 to −0.5% at 5,000. The magnitude of the prompt effect was fairly
consistent, while cache-capacity variability and the decode interaction remain
unresolved at three blocks. Do not fit or promote a general interaction from
this screen.

Response text was not byte-identical across requests. Some condition/block
sequences repeated one alternate prose digest on the second request, and the
5,000/128 cell had additional variation. Since the 64-token output cap cannot
complete the prepared 200-word quality rubric, the result is a throughput and
admission screen only. No cache or prefill default changed. A task-quality
check and held-out confirmation are needed before promoting chunk 128.

Clocks were dynamic; EMC clock access and scoped energy were unavailable. The
result covers one Orin, one IQ1_M artifact, one 512/64 workload and the opt-in
Q6/MTP profile. It does not qualify other prompt lengths, formats, task quality
or mid-request cache resizing.

Reproduce each block under the same 28-GiB systemd scope with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/prefill_cache_screen.py \
    --config bench/results/2026-10-14-phase6-q6-prefill-cache/base-config.json \
    --workloads bench/results/2026-10-14-phase6-q6-prefill-cache/workloads.json \
    --output bench/results/2026-10-14-phase6-q6-prefill-cache/block-NN \
    --cache-values 3000 5000 --prefill-values 32 128 \
    --rounds 3 --seed SEED --timeout 1800 --no-trace
```
