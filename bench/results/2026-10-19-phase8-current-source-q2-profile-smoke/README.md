# Current-source Q2_0 selected-profile recall and recovery — Orin — 2026-10-19

The current integration candidate passed the selected Q2_0 service profile at 8K context. The checked-out repository HEAD was `d50ff723`; the binary contains engine source from `b6ea6188` and has SHA256 `b09ed0b5774de235d145bff869950730a78cbf5ddc6b4057098d70b981130eaa`.

The profile used Q2_0, FP16 KV, MTP off, 8,192 context, 3,000 exact expert slots, prefill chunk 128, eight workers, prompt cache and adaptive swaps disabled, a 3,072-MiB workspace reserve, and the `MemoryMax=28G` supervisor with a six-GiB host floor. After a 512-token warmup, the service processed an uncached 7,498-token prompt. It returned all three planted markers exactly once and in order, then returned `RECOVERED` to a separate request on the same service. The independent reviewer passed.

The measured prefill took 276.0 seconds (27.2 tokens/s); the 41-token recall request took 284.1 seconds. Across 322 one-second memory samples, minimum host availability was 18.05 GiB and minimum admission availability was 8.57 GiB. All sampled cgroup low/high/max/OOM/kill counters were zero. Clocks were observed dynamically; EMC readback was denied and energy was not request-attributed. This verifies one functional profile-specific cell and is not a performance comparison or broad quality claim.

The exact binary, source commits, model revision and shard hashes, PLE pack and profile hashes, and request configuration/workload hashes are recorded in [`artifact-identities.json`](artifact-identities.json). The raw request, independent review, engine log, memory/clock samples and `tegrastats` capture are retained under [`run/`](run/) and [`supervisor/`](supervisor/). Models and packs remained under `~/models/strata-orin-validation/`.

Reproduce with a fresh output path:

```sh
OUTPUT_ROOT=bench/results/2026-10-19-phase8-current-source-q2-profile-smoke/reproduction \
  bash bench/results/2026-10-19-phase8-current-source-q2-profile-smoke/run.sh
```

This confirms the selected profile on the current candidate source. It does not close Phase 5 state/migration gates or Phase 6's broader interaction and energy work.
