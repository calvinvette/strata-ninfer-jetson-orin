# Current-source Q2_0 selected-profile recall and recovery — Orin — 2026-10-18

The current integration candidate at source commit `0b28cd634fa3a7ba9da514df0200d96baea330e4`
passed the selected Q2_0 service profile at 8K context. The candidate binary
SHA256 was `320963c6572a13065e7704b3f98d477c8e29119ea45a96114f532008134e9932`.
The exact model, PLE shard, pack, tokenizer and expert-profile identities are
retained in the [Phase 7 artifact manifest](../2026-10-17-phase7-q2-prefill128/sustained-512/artifacts.json);
all model files remained under `~/models/strata-orin-validation/`.

The configuration was Q2_0, FP16 KV, MTP off, 8,192 context, 3,000 exact
expert slots, prefill chunk 128, eight workers, prompt cache and adaptive swaps
disabled, with a 3,072-MiB workspace reserve. After a 512-token warmup, the
service processed a 7,498-token uncached prompt and returned all three planted
markers exactly once and in order. It then returned `RECOVERED` to a separate
request on the same service. The independent reviewer passed all prompt-count,
marker and recovery checks.

The run was supervised with `MemoryMax=28G`, one-second sampling and the
six-GiB physical-availability guard. Across 324 samples, minimum host
availability was 17.69 GiB and minimum admission availability was 8.69 GiB.
All sampled `low`, `high`, `max`, `oom` and `oom_kill` counters were zero.
Prompt processing took 288.0 seconds (26.0 tokens/s); the full retrieval
request took 295.6 seconds and same-service recovery took 3.7 seconds. Clocks
remained dynamic. No process-attributed energy was measured. These are one
functional profile-specific run and its timings are not a performance
comparison or a broad quality claim.

The original runner result, independent review, service configuration, engine
log, one-second memory and clock samples, and `tegrastats` output are retained
here. Reproduce with [`run.sh`](run.sh); it writes to a fresh timestamped
subdirectory. The binary and model files are not stored in Git.
