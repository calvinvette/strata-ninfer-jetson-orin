# Q2_0 MTP3 task-quality completion

This supervised Phase 5 check fills the MTP3 task-quality cell between the
existing Q2_0 MTP2 and MTP4 checks. It used the same exact 2,048-token prepared
computer-processing task, 512-token output allowance, Q2_0 two-shard artifact,
3,000 expert-cache setting, FP16 KV, 8K context, captured decode, and
`--adapt-every 4 --adapt-accepted-only` policy. The current candidate binary
SHA256 is `857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`.
Model and MTP files stayed under `~/models/`.

The single fresh service returned 2,094 formatted prompt tokens and 293
completion tokens, stopped naturally, and passed all nine task-rubric checks:
the exact `Processor:` opening, at least 200 words, fetch/decode/execute, RAM,
binary data, input and output, and `17 x 19 = 323`. Its answer SHA256
`ad9816e2168a3143c54cab057a9bcb871f7a31ae42bf60730f7afb68d11d4ecb` matches
the previous MTP-off, MTP2 and MTP4 answers exactly. This shared answer result
does not by itself prove persistent-state parity; direct accepted-prefix tests
are recorded separately.

`run_control.py` passed inside the 28-GiB systemd scope. Minimum physical host
availability was 17.023 GiB and minimum effective admission availability was
12.772 GiB, above the six-GiB host floor and separate three-GiB workspace
reserve. No clocks were changed. This is one task-quality cell, not timing
evidence or broad model-quality qualification. No profile or default changes.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-q2-mtp3-quality/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase5-q2-mtp3-quality/quality_api_driver.py \
  --config bench/results/2026-10-14-phase5-q2-mtp3-quality/config-mtp3.json \
  --workloads bench/results/2026-10-14-phase5-q2-mtp3-quality/workloads.json \
  --cells quality-pp2048-512 \
  --output bench/results/2026-10-14-phase5-q2-mtp3-quality/results.json
```

The response, server config, engine log and raw supervisor telemetry are kept
beside this report. See also the [MTP0/2/4 quality checks](../2026-10-14-phase5-q2-mtp-quality/README.md)
and [Q2_0 accepted-prefix state checks](../2026-10-13-phase5-q2-accepted-prefix/README.md).
