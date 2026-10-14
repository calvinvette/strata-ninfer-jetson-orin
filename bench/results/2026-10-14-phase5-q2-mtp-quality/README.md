# Q2_0 MTP task-quality check — 2026-10-14

This quality-only check ran one request in each of three fresh Q2_0 services:
MTP disabled, MTP2 and MTP4. All used the same 2,048-token prepared prompt,
3,000 expert-cache setting, FP16 KV, 8K context, captured decode, and
`--adapt-every 4 --adapt-accepted-only`. The API reported 2,094 prompt tokens
after chat formatting and zero cached tokens. Each request had a 512-token
output allowance and ended naturally.

| MTP window | Prompt / completion tokens | Answer words | Drafts offered / accepted | Task rubric |
| ---: | ---: | ---: | ---: | --- |
| Off | 2,094 / 293 | 235 | 0 / 0 | Pass |
| 2 | 2,094 / 293 | 235 | 155 / 108 | Pass |
| 4 | 2,094 / 293 | 235 | 155 / 108 | Pass |

All replies were byte-identical (SHA256
`ad9816e2168a3143c54cab057a9bcb871f7a31ae42bf60730f7afb68d11d4ecb`). Each
started with `Processor:`, exceeded 200 words, described fetch/decode/execute,
RAM, binary data, input and output, included `17 x 19 = 323`, and stopped
naturally. The three 28-GiB supervised processes passed; minimum host
availability was 16.87 GiB and minimum admission availability was 12.93 GiB.
No clocks were changed. This is a task-level check for one prompt and one
artifact/configuration, not a broad language-quality result or timing
comparison. The elapsed times are retained in `analysis.json` as observations
only. No default or MTP profile is promoted.

The model was the local Qwen3.8-Flash-Next GSQ-RCO Q2_0 two-shard artifact with
the local `q2-ple-pack`, `q2-expert-profile.bin`, and MTP runtime pack under
`~/models/strata-orin-validation/`. The candidate binary SHA256 was
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`.
No model files are included here.

Reproduction used the checked-in configs and workload with the included
`quality_api_driver.py`, one condition at a time:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output <condition>/supervisor --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase5-q2-mtp-quality/quality_api_driver.py \
  --config bench/results/2026-10-14-phase5-q2-mtp-quality/config-mtp<N>.json \
  --workloads bench/results/2026-10-14-phase5-q2-mtp-quality/workloads.json \
  --cells quality-pp2048-512 --output <condition>/results.json
```

The separate [accepted-prefix evidence](../2026-10-13-phase5-q2-accepted-prefix/README.md)
checks token and persistent-state parity for Q2_0 MTP windows, but on different
prompt lengths/settings. This report does not assert state parity from the
identical text alone.
