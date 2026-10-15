# Current-source Coder GGUF 16K retrieval — Orin — 2026-10-15

This supervised Phase 7 run tested the current candidate on the Coder GGUF
directory at 16,384 configured context. The two shard hashes are recorded in
`model-sha256.txt` and are byte-identical to the Coder IQ1_M shards used in the
earlier service qualification. This extends current-binary evidence to another
context size; it is not a second model cohort or independent repetition.

The unique formatted retrieval prompt contained exactly 15,003 tokens and
reported zero cached prompt tokens. The answer returned `MAPLE-ORBIT-731`,
`COBALT-HARBOR-284` and `VELVET-COPPER-956` exactly once and in order, then the
same service returned `RECOVERED`. The task used 41 output tokens. MTP drafted
32 and accepted 30. Engine-reported prompt and decode rates were 23.6 and 14.5
tokens/s; the prompt took 637.0 seconds and the full supervised process took
708.5 seconds, including startup, warmup and recovery.

The run used the current candidate binary (SHA256 in `binary-sha256.txt`),
source commit `b99b26a2`, and the same opt-in profile as the 8K check: Q6_K
warp-dequant, accepted-only MTP4 at cadence 4, FP16 KV, 3,000 requested expert
slots (3,903 actual), eight workers, prefill chunk 64 and dynamic clocks. It
ran with `MemoryMax=28G` and a six-GiB host-availability guard. Across 673
samples, minimum host/admission availability was 12.76 GiB, maximum cgroup use
was 12.90 GiB, and `high`, `max`, `oom` and `oom_kill` counters stayed zero.
GPU frequencies ranged 306 MHz–1.3005 GHz, CPU frequencies 729.6 MHz–2.2016
GHz, and `tj` 48.4–56.8 °C. EMC readback was denied; energy was not
request-attributed.

This confirms one 16K prompt/profile/model identity and same-service recovery.
It does not qualify general 16K quality, establish independent statistical
repetition, or close Phase 7.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m-16k/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q6-recall/run_recall_case.py \
  --config bench/results/2026-10-15-phase7-current-source-coder-iq1m-16k/config-16384.json \
  --workload bench/results/2026-10-15-phase7-current-source-coder-iq1m-16k/workload-16384.json \
  --warmup-workload bench/results/2026-10-15-phase7-current-source-coder-iq1m-16k/warmup-512.json \
  --output bench/results/2026-10-15-phase7-current-source-coder-iq1m-16k/run
```

The answer, server configuration, engine log, telemetry, supervisor result,
model hashes and binary identity are retained here.
