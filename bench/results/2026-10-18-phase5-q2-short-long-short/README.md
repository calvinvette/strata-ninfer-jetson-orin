# Q2_0 same-service short→long→short check — Orin — 2026-10-18

This Phase 5 check asked whether a near-limit request changes the answer to the
same short request on a single live service with adaptive expert swaps and MTP
disabled. It used the selected Q2_0 profile: 8K context, FP16 KV, 3,000 exact
expert slots, prefill chunk 128, eight workers, a 3,072-MiB workspace reserve,
prompt cache off and the CUDA verifier graph path. The model is the
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` Q2_0 snapshot
`5348543e0147355ac9cbcb031184a3546350988e`, with model files under
`~/models/strata-orin-validation/`.
The two Q2_0 GGUF shard SHA256 values are `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720`
and `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`;
pack and expert-profile hashes are in the [artifact manifest](../../2026-10-17-phase7-q2-prefill128/sustained-512/artifacts.json).

After a 512-token warmup, the service answered the exact same uncached
512-token retrieval-and-sum prompt, processed an uncached 7,498-token retrieval
prompt, then answered the short prompt again. Both short answers exactly
matched the independent expected string
`EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768`.
The long answer returned all three independently specified markers exactly
once and in order. A separate reviewer rechecked the outputs, prompt/cache
counts and memory samples.

The candidate binary SHA256 was
`320963c6572a13065e7704b3f98d477c8e29119ea45a96114f532008134e9932`, from
source commit `0b28cd634fa3a7ba9da514df0200d96baea330e4`. The entire sequence
took 360.8 seconds. Minimum host availability was 17.89 GiB; minimum effective
admission availability was 11.75 GiB. Across 343 one-second samples, all
observed cgroup low/high/max/OOM/OOM-kill counters were zero. Clocks remained
dynamic; EMC readback was denied. Energy was not attributed.

This is one functional control sequence for the selected Q2_0 profile. It shows
exact short-answer recovery after this long request, but does not prove exact
persistent-state identity, qualify other prompts or formats, or address the
IQ1_M adaptive-migration state divergence. It makes no performance comparison
and does not close Phase 5.

The first launch attempt failed before starting model loading because the
runner had an incorrect repository-root calculation; that harness failure is
retained under `harness-failure/` and excluded. The corrected source and
successful run are under `retry/`.

Reproduce from the repository root on Orin with:

```sh
bash bench/results/2026-10-18-phase5-q2-short-long-short/run.sh
```

The runner writes a fresh timestamped output directory. Its default inputs are
the existing selected-profile Q2_0 configuration and independently reviewed
short/long workloads. The independent review can be repeated with:

```sh
python3 bench/results/2026-10-18-phase5-q2-short-long-short/review_sequence.py \
  --result bench/results/2026-10-18-phase5-q2-short-long-short/retry/result/result.json \
  --supervisor bench/results/2026-10-18-phase5-q2-short-long-short/retry/supervisor/result.json \
  --samples bench/results/2026-10-18-phase5-q2-short-long-short/retry/supervisor/memory.jsonl \
  --output /tmp/q2-short-long-short-review.json
```
