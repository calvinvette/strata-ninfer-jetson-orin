# Current-source Coder GGUF path smoke — Orin — 2026-10-15

This is a current-source, supervised Phase 7 recall and recovery check using
the downloaded `Coder-GGUF` directory. The two GGUF shards have the same full
SHA256 hashes as the Coder IQ1_M shards used by earlier Strata tests, so this
is a path/current-binary regression, not a second model cohort or independent
repeat. The model stayed under `~/models/strata-orin-validation/`.

Before starting the service, `verify_pack_compatibility.py` used the native
pack builder's GGUF parser and expert-layout function to compare the downloaded
Coder GGUF with the existing local Strata pack. All 48 layers and 256 experts
per layer matched, as did the `native_experts.txt` digest and pack source
sidecar. Six sampled expert blobs across the first, middle and final layers
matched byte-for-byte. Full GGUF shard hashes match the earlier model manifest.
No pack or model file was changed.

The service ran the established 8K retrieval task at 8,192 configured context,
with a unique 7,498-token prompt and zero cached prompt tokens. It returned the
three planted codes exactly once and in order, then returned `RECOVERED` to a
short request on the same service. The retrieval answer used 41 generated
tokens; MTP drafted 32 and accepted 30. Engine-reported prompt rate was 24.0
tokens/s and decode rate was 16.2 tokens/s. The warmup was 512 tokens and the
whole supervised run took 384.1 seconds.

The run used the current candidate binary (SHA256 in `binary-sha256.txt`),
source commit `b99b26a2`, and the tested opt-in profile: Q6_K warp-dequant,
accepted-only MTP4, cadence 4, FP16 KV, 3,000 requested expert slots (3,903
actual), eight workers, prefill chunk 64, and dynamic clocks. It was supervised
at `MemoryMax=28G` with the six-GiB host-availability guard. Across 364 memory
samples, host and admission availability stayed at or above 13.25 GiB; maximum
cgroup use was 14.00 GiB and `high`, `max`, `oom` and `oom_kill` counters were
zero. GPU observations ranged from 306 MHz to 1.3005 GHz and CPU frequencies
from 729.6 MHz to 2.2016 GHz; EMC readback was denied and energy was not
request-attributed.

This confirms this exact prompt, profile, model identity and current service
path. It does not add a model cohort, test cold storage, qualify general 8K
quality, or close Phase 7.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m/supervisor \
  --timeout 1200 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q6-recall/run_recall_case.py \
  --config bench/results/2026-10-15-phase7-current-source-coder-iq1m/config-8192.json \
  --workload bench/results/2026-10-15-phase7-current-source-coder-iq1m/workload-8192.json \
  --warmup-workload bench/results/2026-10-15-phase7-current-source-coder-iq1m/warmup-512.json \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m/run

/home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-15-phase7-current-source-coder-iq1m/verify_pack_compatibility.py \
  --gguf /home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --pack /home/calvin/models/strata-orin-validation/pack
```

The raw answer, server configuration, engine log, telemetry, supervisor result,
full shard hashes, binary identity and pack compatibility output are retained
with this report.
