# Held-out 2,048-token mapped versus pread confirmation

This is a second fixed-cache, randomized seven-pair Orin transfer cell at a
2,048-token prompt and 64-token generation. The earlier fixed-cache cell used
512 prompt tokens. Both use the same Qwen3.8-Flash-Next Coder IQ1_M artifacts,
MTP files, tokenizer, engine build and requested 5,000-MiB expert-cache cap.
This report tests transfer behavior at a longer prefill; it is not a general
policy recommendation. Artifact identities are in `artifact-identities.json`.

All fourteen requests completed under the six-GiB physical-memory supervisor.
Each pair matched emitted token IDs, all nine persistent-state fields, 6,519
actual cache slots and 49,669 cache hits. Each arm generated 64 tokens. Minimum
`MemAvailable` was 8,690,331,648 bytes (8.09 GiB). The prompt token IDs have
SHA256 `840a12d5350ef22232fb737a190b96359d7adc54ed138863a06bf104bcf0b8c6`.

| Measure | Mapped median | Pread median | Paired mapped-minus-pread median (95% bootstrap interval) |
| --- | ---: | ---: | ---: |
| Request time | 62,753.7 ms | 63,999.1 ms | −1.31% (−2.01%, −0.52%) |
| Prompt time | 57,979.5 ms | 57,657.0 ms | +0.60% (+0.39%, +1.40%) |
| Decode time | 4,896.5 ms | 6,168.4 ms | −19.49% (−23.30%, −18.25%) |
| VIN_SYS_5V0 rail energy | 485.58 J | 478.46 J | −0.70% (−2.27%, +5.45%) |
| VDD_GPU_SOC rail energy | 824.30 J | 829.67 J | −1.17% (−1.95%, +1.00%) |
| Whole-device NVMe read-byte delta | 9,068,318,720 B | 9,360,203,776 B | −5.97% (−7.46%, −2.55%) |

Intervals use 100,000 pair-resamples with seed 20261011. Mapped lowered
request-time median by a modest 1.31%; its prompt median was 0.60% higher and
decode median 19.49% lower. The whole-board rail intervals include zero for
both reported rails, so this cell does not establish an energy reduction. The
512-token cell showed a larger request-time difference, but had two large
slow-clock outliers. These workload cells together support further evaluation,
not a default switch or a claim that mapped reads generally improve requests.

CPU clocks were dynamic (729–2,201 MHz); median of per-request CPU medians was
729 MHz for each arm. tegrastats returned no GR3D or EMC clock samples. Rail
energy is trapezoid integration of named whole-board readings, includes
unrelated system activity, and rail values are separate and non-additive. NVMe
read deltas are whole-device counters including unrelated reads and kernel
readahead; process and cgroup-scoped read-byte counters were unavailable.
Mapped major-fault median was 91,067 versus 69,687 for pread; minor-fault
medians were 201,344 versus 212,950. Fault directions therefore differ. Raw
pairs, telemetry and owner events remain in `experiment/` and the supervisor
files.

Reproduce from the repository root using the recorded model configuration and
engine:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-10-11-phase3-transfer-heldout-2048 \
  --timeout 1800 -- \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  tools/integration/file_tier_transfer_parity.py \
  --config /home/calvin/models/strata-orin-validation/strata-orin-validation-8k.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-11-phase3-transfer-heldout-2048/experiment \
  --prompt-tokens 2048 --generated-tokens 64 --pairs 7 --run \
  --tegrastats-energy --tegrastats-interval-ms 100 --expert-cache 5000
```
