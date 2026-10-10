# Automatic expert-cache allocation retry — 2026-10-10

This supervised Orin check exercises the existing `STRATA_TEST_CACHE_FAIL=1`
fault injection. The first automatic expert-cache allocation is refused as an
out-of-memory failure; the runtime should retry with fewer slots, start the
session and complete a real request. It used the pinned IQ1_M pack and source
shards, the 512-token prepared workload, profile-driven cache population,
speculation window 4, prefill chunk 512 and 4096-token context.

The accepted invocation is retained under `native-with-profile/`. It passed
with a six-GiB supervisor floor and 13,862,178,816 bytes (12.91 GiB) minimum
observed availability. Logs show the simulated failure, automatic shrink from
4,864 to 4,753 slots, successful loading of all 4,753 profile slots, successful
session startup, a 511-token prompt, and one generated token (ID 32). This is
failure-retry and short-request completion evidence; it is not a latency
comparison or performance claim.

The initial attempt without native flags and the native attempt without the
required profile are retained separately with their reasons. The second
reached the injected allocation failure and successfully retried, completed
prefill, then correctly refused decode because spec 4 requires an expert
profile. The final attempt supplied that profile and completed decode.

Reproduction from the repository root:

```bash
STRATA_TEST_CACHE_FAIL=1 python tools/integration/run_control.py \
  --output bench/results/2026-10-10-phase3-cache-failure-retry/reproduction \
  build/integration/candidate/strata \
  --pack /home/calvin/models/strata-orin-validation/pack \
  --native /home/calvin/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --expert-profile data/expert-profile-coder.bin --spec 4 --prefill 512 \
  --tokens-file build/integration/workloads/pp512-tg64.tokens \
  --max-context 4096 --max-new 1 --expert-cache auto \
  --ple-gguf /home/calvin/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf
```
