# Current-source Coder GGUF 32K retrieval — Orin — 2026-10-15

This supervised Phase 7 run tested the current candidate on the Coder GGUF
directory at 32,768 configured context. The two model shard hashes are in
`model-sha256.txt` and match the Coder IQ1_M artifacts used in earlier service
tests. This is a current-binary/context regression, not a new model cohort or
an independent statistical repetition.

The unique formatted prompt contained 30,032 tokens and zero cached prompt
tokens. The answer returned `MAPLE-ORBIT-731`, `COBALT-HARBOR-284` and
`VELVET-COPPER-956` exactly once and in order, then the same service returned
`RECOVERED`. The answer used 41 tokens; MTP drafted 32 and accepted 30.
Engine-reported prompt and decode rates were 23.6 and 14.0 tokens/s; prompt
processing took 1,273.3 seconds and the whole supervised run took 1,339.5
seconds, including startup, warmup and recovery.

The run used the current candidate binary (SHA256 in `binary-sha256.txt`),
source commit `b99b26a2`, and the opt-in profile documented in the 8K report:
Q6_K warp-dequant, accepted-only MTP4 at cadence 4, FP16 KV, 3,000 requested
expert slots (3,903 actual), eight workers, prefill chunk 64 and dynamic
clocks. It ran under `MemoryMax=28G` with the six-GiB host-availability guard.
Across 1,266 samples, minimum host/admission availability was 12.60 GiB,
maximum cgroup use was 11.32 GiB, and `high`, `max`, `oom` and `oom_kill`
counters were zero. GPU frequencies ranged 306 MHz–1.3005 GHz, CPU
frequencies 729.6 MHz–2.2016 GHz, and `tj` 49.6–56.3 °C. EMC readback was
denied, and energy was not request-attributed.

This confirms one exact 32K retrieval prompt/profile/model identity and
same-service recovery. It does not establish broad 32K quality, statistical
repetition, a thermal-soak result for this binary, or Phase 7 completion.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m-32k/supervisor \
  --timeout 2700 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q6-recall/run_recall_case.py \
  --config bench/results/2026-10-15-phase7-current-source-coder-iq1m-32k/config-32768.json \
  --workload bench/results/2026-10-15-phase7-current-source-coder-iq1m-32k/workload-32768.json \
  --warmup-workload bench/results/2026-10-15-phase7-current-source-coder-iq1m-32k/warmup-512.json \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m-32k/run
```

The answer, server configuration, engine log, telemetry, supervisor result,
model hashes and binary identity are retained here.
