# Current-source Coder IQ1_M MTP × KV replication — Orin — 2026-10-20

This is a seven-block same-day replication of the short-prompt Coder IQ1_M
MTP-off/MTP4 × FP16/INT8-KV screen, using the current integration candidate
binary. It reuses the previously measured 512-token retrieval-plus-arithmetic
task, so it is a replication of that workload, not a new held-out task. It does
not test the separate Q2_0 Coder quantization or compare inference engines.

All 28 arms passed. Every request returned the independent expected answer
exactly:

```text
EARLY=EMBER-VAULT-317, MIDDLE=SILVER-MAPLE-846, LATE=TIDAL-COPPER-529, SUM=1692
```

The run used the Coder `IQ1_M` GGUF at Hugging Face revision
`5348543e0147355ac9cbcb031184a3546350988e`; the two model shard hashes are in
[`model-sha256.txt`](model-sha256.txt). It used the matching MTP runtime at
revision `de4b8e4d43b917e7706784d8bb445c9af86a3540`; its local artifact hashes
are recorded in [`artifact-sha256.txt`](artifact-sha256.txt). Model and MTP
artifacts remain under `~/models/strata-orin-validation/` and are not included
in this repository.

The candidate binary SHA256 is
`e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`. The
campaign records base source commit `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`;
the candidate also included the then-current uncommitted integration worktree.
The screened runtime settings were 8K context, 1,500 MiB requested expert
cache, 64-token prefill chunks, eight workers, 3,072 MiB workspace reserve,
and adaptive swapping off. Each paired cell had identical measured expert
residency: 1,934 slots / 3,807 MiB. Each arm ran under `MemoryMax=28G`.

| KV | Metric | MTP4 median effect vs off | Paired-block bootstrap 95% interval |
| --- | --- | ---: | ---: |
| FP16 | Prompt throughput | −3.62% | −5.35% to −0.20% |
| FP16 | Decode throughput | −3.15% | −4.14% to −0.86% |
| FP16 | Client TTFT | +3.76% | +0.21% to +5.83% |
| FP16 | Client total time | +3.83% | +0.58% to +5.49% |
| INT8 | Prompt throughput | −0.26% | −1.36% to +0.64% |
| INT8 | Decode throughput | −0.17% | −9.86% to +1.68% |
| INT8 | Client TTFT | +0.27% | −0.65% to +1.29% |
| INT8 | Client total time | +0.12% | −0.75% to +4.37% |

Effects are paired within randomized blocks, with ratios formed as MTP4 / MTP
off (or MTP4 / MTP-off latency). All seven pairs per KV format qualified for
same-local-day, exact prompt token count, KV format, and expert residency.
INT8 decode showed two large opposing block effects; its interval is wide and
includes zero. These data do not support promoting MTP4 for this cell. The
bootstrap intervals quantify block-to-block variation for this task and
configuration, not general model quality or performance uncertainty across
other workloads.

Across 1,977 one-second memory samples, minimum host availability was 16.70
GiB and minimum admission availability was 15.62 GiB, above the six-GiB host
floor. Maximum observed candidate cgroup use was 12.38 GiB. `high`, `max`,
`oom`, and `oom_kill` event counters stayed at zero. Read-only GPU clock
observations ranged from 306 MHz to 1,300.5 MHz; EMC clock readback was
unavailable.

The retained tegrastats samples also support a request-window integration of
each named rail, separately. These include board idle/background activity and
are not process-attributed; rails are not summed. Median joules per 45-token
answer were:

| KV | MTP | VIN_SYS_5V0 | VDD_CPU_CV | VDD_GPU_SOC |
| --- | ---: | ---: | ---: | ---: |
| FP16 | Off | 4.697 | 1.901 | 6.133 |
| FP16 | 4 | 4.665 | 2.035 | 5.748 |
| INT8 | Off | 4.708 | 1.917 | 6.078 |
| INT8 | 4 | 4.608 | 2.051 | 5.758 |

For the input rail `VIN_SYS_5V0`, paired MTP4 effects were −0.05% (95%
interval −2.55% to +1.23%) with FP16 KV and −2.20% (−3.05% to +1.28%) with
INT8 KV. The MTP × KV interaction was +1.86 percentage points (−3.83 to
+5.77). Every interval includes no effect. The other named-rail results and
all 28 per-arm integrals are in [`rail-energy.json`](rail-energy.json) and
[`rail-energy-pairs.csv`](rail-energy-pairs.csv). Reproduce the integration
with:

```sh
python3 bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-confirm7/analyze_rail_energy.py
```

This is board-rail energy per generated token over the full request window,
including prompt and decode. It does not estimate process-only energy or
generation-only energy.

The raw randomized campaign, per-arm request results, memory samples,
tegrastats, supervisor records, and paired residency/date audit are in
[`campaign/`](campaign/). The analysis is reproducible with:

```sh
python3 tools/integration/audit_mtp_kv_screen.py \
  bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-confirm7/campaign/campaign.json \
  --run-root bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-confirm7/campaign \
  --output bench/results/2026-10-20-phase6-coder-current-source-mtp-kv-confirm7/campaign/residency-audit.json
```

This confirms one current-source short-prompt replication only. It adds one
task-scoped latency/board-rail energy cell but does not estimate process-only
energy. Phase 6 remains open for the remaining supported interactions, broader
Pareto analysis, and configuration coverage; no default changed.
