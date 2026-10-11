# File-tier transfer × expert-cache interaction screen — Orin — 2026-10-11

This same-day randomized screen tests mapped versus pread expert reads at two
fixed requested cache budgets using the same 512-token prompt and 64-token
generation. Each cache stratum contains three randomized mapped/pread pairs.
The current IQ1_M Coder candidate used Q2_0 MTP, prefill chunk 64, context
8,192, and CPU prefill sharing disabled. The 3,000- and 5,000-slot requests
admitted 3,903 and 6,519 actual slots. Engine SHA-256 was
`facca01aaf48730f0098fb67b254dd0f42cc063403b03834ed84fa41211dbb83`.
Both strata used prompt token SHA-256
`9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`.

All six pairs passed: mapped and pread matched generated token IDs, all nine
persistent-state fields, and actual cache slots within each cache stratum.
Mapped request time was lower in all three pairs at each size:

| Requested cache | Actual slots | Mapped median prompt/decode (ms) | Pread median prompt/decode (ms) | Paired mapped request delta range | Minimum host availability |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3,000 | 3,903 | 26,747.5 / 5,760.3 | 27,033.3 / 7,235.6 | −6.23% to −0.97% (median −4.75%) | 13.05 GiB |
| 5,000 | 6,519 | 22,649.9 / 4,664.2 | 21,912.6 / 6,262.9 | −3.76% to −2.67% (median −3.54%) | 8.03 GiB |

These are three-pair screens without a useful confirmation interval. Cache
strata ran sequentially, so their absolute times cannot isolate a cache-size
effect. Outputs matched across the two strata, but persistent-state fingerprints
did not; cross-cache numerical parity is not claimed. The 5,000-slot runs came
within 2.03 GiB of the required physical-availability floor. The run controller
would abort at the six-GiB guard.

Read-only samples showed CPU rates from 729 to 2,202 MHz, GPU from 306 to
1,300.5 MHz, and EMC at 3,199 MHz in both strata. Per-request tegrastats rail
integrals are retained, but represent whole-board system activity and are not
process-attributed. Process read-byte counters were unavailable; major faults
and whole-device block reads are retained in the raw results. These conditions
limit timing and transfer-cost interpretation. No transfer mode or default was
changed; a larger paired confirmation with request-local I/O counters is still
needed before promotion.

The `experiment-cache3000/` and `experiment-cache5000/` directories retain
all arm logs, state/owner observations, pair comparisons and tegrastats rail
samples. Matching `supervisor-cache*/` trees retain physical-memory and sampled
clock observations. `model-config.json` and the generated token IDs preserve
reproduction inputs; model files and build products remain outside Git.

Reproduce each stratum from the repository root with the integration venv:

```sh
python tools/integration/run_control.py --sample-clocks --privileged-emc \
  --output bench/results/2026-10-11-phase3-transfer-cache-interaction-screen/supervisor-cache3000 \
  --timeout 1800 -- /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  tools/integration/file_tier_transfer_parity.py \
  --config bench/results/2026-10-11-phase3-transfer-cache-interaction-screen/model-config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-11-phase3-transfer-cache-interaction-screen/experiment-cache3000 \
  --prompt-tokens 512 --generated-tokens 64 --pairs 3 --seed 2026101101 \
  --run --tegrastats-energy --tegrastats-interval-ms 100 --expert-cache 3000
```

For the second stratum, substitute `cache5000` in the two output paths, use
seed `2026101102`, and set `--expert-cache 5000`.

On the same current candidate, artifact-aware Q2_0 `ple_parity` and
`ple_reader_selftest` CTests passed 2/2 under the six-GiB supervisor; minimum
host availability was 26,462,167,040 bytes (24.64 GiB). Integration Python
unittest discovery passed 99/99. These are selected contract regressions, not
whole-model quality qualification. Raw PLE output is retained in
`ple-current/supervisor/`. The PLE parity and reader executable SHA-256 values
were `021239e6fa46ba81b1d1c011b10a71a6386ae420d14cc25cc496a8558efaed30` and
`f1f9d5c16fe48d29b8154363630415f53abf824f4d8044889c8cb88d7cdc7639`.
The Python suite output is in `integration-tests.txt`. Reproduce with:

```sh
python tools/integration/run_control.py --sample-clocks --privileged-emc \
  --output bench/results/2026-10-11-phase3-transfer-cache-interaction-screen/ple-current/supervisor \
  --timeout 600 -- ctest --test-dir build/integration/candidate \
  --output-on-failure -R 'ple_parity|ple_reader_selftest'
```
