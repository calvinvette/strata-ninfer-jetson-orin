# Coder MTP4 × KV × prompt-length screen

## Result

A randomized three-block screen compared MTP-off with MTP4 on two fixed Coder
IQ1_M retrieval workloads, under FP16 and INT8 KV. All 24 arms passed the
workload's expected-answer checks. The screen used the 512-token short prompt
from the preceding MTP screen and the 7,501-token near-limit prompt from the
preceding MTP × KV confirmation. It is a workload screen, not held-out prompt
confirmation for MTP4.

Paired effects below are MTP4 relative to MTP-off, with paired-block bootstrap
95% intervals. The three randomized blocks are the independent units; tokens
within a request are not treated as replicates.

| KV | Workload | Decode throughput | Client TTFT | Client total |
| --- | --- | ---: | ---: | ---: |
| FP16 | 512 prompt tokens | +10.29% (+5.46, +12.00) | +1.21% (+0.26, +4.15) | −0.14% (−1.14, +2.96) |
| INT8 | 512 prompt tokens | +11.35% (+10.01, +11.90) | +3.35% (+0.07, +7.91) | +1.48% (−1.24, +5.60) |
| FP16 | 7,501 prompt tokens | −10.95% (−13.19, −9.54) | +0.59% (−7.85, +1.66) | +0.69% (−7.66, +1.80) |
| INT8 | 7,501 prompt tokens | −8.80% (−9.13, −7.95) | +1.13% (−7.70, +1.23) | +1.21% (−7.52, +1.33) |

The decode direction changes with prompt length: MTP4 improved short-task
decode throughput in this screen and reduced near-limit decode throughput.
Long-request total-time intervals include zero because prompt processing
dominates these 45-token completions. The short workload's MTP4 × KV decode
interaction interval also includes zero; the screen does not support a KV
specific MTP4 recommendation. No configuration or default is promoted.

Each long MTP4 arm drafted 42 tokens and accepted 33; each short MTP4 arm drafted
39 and accepted 34. MTP-off drafted and accepted none. The answer checks passed
for 47 short-task and 45 near-limit output tokens in all cells. These counts
describe this fixed workload set and do not qualify persistent-state parity.

## Measurement scope

- Date: 2026-10-24; three randomized blocks; 12 qualified same-day paired
  comparisons and no excluded pairs.
- Model: pinned Coder IQ1_M GGUF artifact, revision
  `5348543e0147355ac9cbcb031184a3546350988e`; upstream base-checkpoint MTP
  weights. Both remain under `~/models/strata-orin-validation/`.
- Request shape: context 8,192; short input 512 tokens / 47 output tokens;
  near-limit input 7,501 tokens / 45 output tokens. The exact workloads are
  retained in `inputs/workloads.json`.
- Expert profile: 1,500 MiB requested; 1,934 actual resident slots / 3,807 MiB.
  Other serving settings were inherited from `config-source.json` and held
  constant across paired arms.
- Runtime: Orin AGX, native CUDA/SM87, dynamic GPU clock samples 306–1,300.5
  MHz. EMC clock readback was unavailable. Minimum physical availability was
  16.83 GiB and minimum effective admission availability was 15.69 GiB. The
  28-GiB arm cgroup recorded zero high, max, OOM or OOM-kill events.
- Energy: not analyzed. Raw tegrastats records are retained locally; this
  screen makes no energy-per-token or Pareto claim.

Binary SHA-256:
`ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df`.
The campaign and paired audit are `campaign.json` and `final-audit.json`.
Per-arm logs and supervisor telemetry are retained locally and are not part of
the compact Git record.

Reproduce the paired audit with:

```sh
python3 tools/integration/audit_mtp_kv_screen.py \
  bench/results/2026-10-24-phase6-coder-mtp4-kv-heldout-length-screen3/campaign.json \
  --run-root bench/results/2026-10-24-phase6-coder-mtp4-kv-heldout-length-screen3 \
  --output /tmp/mtp4-kv-audit.json
```

This three-block result is screening evidence only. It does not satisfy the
seven-block held-out confirmation requirement or the energy/Pareto, graph ×
speculation, broader workload, or Phase 5 persistent-state gates. Phase 6 and
Phase 5 remain open.
