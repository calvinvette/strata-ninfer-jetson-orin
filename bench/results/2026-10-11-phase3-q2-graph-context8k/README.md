# Q2_0 graph owner check at 8K context — Orin — 2026-10-11

This repeats the post-fix Q2_0 graph-owner service check with the configured
context raised from 4,096 to 8,192 tokens. The model shards, dense pack,
tokenizer, executable, 256-slot expert-cache request, prefill setting, native
speculation setting, and six-GiB supervisor are unchanged. The model and pack
remain under `~/models/strata-orin-validation/`.

All seven real-model API scenarios passed: repeated greedy responses, OpenAI
and Anthropic streaming, decode cancellation, prefill cancellation, and
recovery requests. Minimum host `MemAvailable` was 21.24 GiB. The session,
expert-cache and verifier device-owner allocation/free pairs balanced 1/1;
verifier mapped-host pairs balanced 16/16; and pageable expert-stage pairs
balanced 256/256. The owner trace ended with zero observed live requested bytes.

The graph interposer observed four successful instantiations (three verifier
window graphs and one commit graph), matching the integration owner events.
Root-readable Tegra NVMap samples were stable at 5,345,353,728 bytes before
the first graph call and 5,417,779,200 bytes after the fourth. The increase,
72,425,472 bytes (69 MiB), matches the earlier Q2_0 4K-context run exactly.
This brackets capture through first-request instantiation and adjacent
synchronous device allocations; it is not an isolated graph-executable size.
This one additional context point does not qualify all graph paths or their
non-NVMap allocations, cgroup pressure, energy, or transfer performance.

The sampler runs every 100 ms. The startup `supervisor/` record is an excluded
preflight launch attempt that occurred before the config file was created; it
did not start an engine. The valid run is in `supervisor-rerun/`. Raw
protocol, engine, owner, NVMap and memory/clock telemetry are retained here.
