# One-block Coder MTP × KV outlier follow-up

This separate randomized block checks whether the two slow 512-token MTP4 arms
in the seven-block confirmation recur. It is a diagnostic follow-up, not a
standalone screen or a replacement for the seven-block paired estimates. It
ran after the primary campaign on the same local date, with one observation per
cell; it cannot provide a confidence interval.

## Identity and execution

- Jetson AGX Orin, ARM64, CUDA 12, SM87; all eight arms ran on 2026-10-21.
- Model: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
  `5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M two-shard GGUF. Model and
  MTP files remained under `~/models/strata-orin-validation/`.
- Source commit: `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`.
- Candidate binary SHA256:
  `b672187692408e8abcb48beb6d80282b01954bae819ec48963ac7c6440e4ec9`.
- Design: one randomized 2 × 2 × 2 block across 512/7,501-token prompts,
  FP16/INT8 KV, and MTP off/4; seed `20261039`. The 512-token, one-token
  warmup ran before each arm.
- Each arm had a separate 28-GiB cgroup and preserved the six-GiB host floor.
  Clocks were read-only/dynamic. Rail energy was not measured for this
  follow-up; raw tegrastats are retained with each supervisor record.

The raw arms and block order are in [`campaign/`](campaign/). All eight
measured requests returned the exact answer:
`EARLY=EMBER-VAULT-317, MIDDLE=SILVER-MAPLE-846, LATE=TIDAL-COPPER-529, SUM=1692`.
Every MTP4 request accepted 33 of 42 drafted tokens.

## Single-block paired observations

Each cell compares its single MTP4 arm against its single MTP-off arm. These
are descriptive ratios only; positive latency changes mean slower and negative
throughput changes mean slower.

| Prompt | KV | TTFT off → MTP4 (change) | Total off → MTP4 (change) | Prompt throughput off → MTP4 | Decode throughput off → MTP4 |
|---|---|---:|---:|---:|---:|
| 512 | FP16 | 25.86 → 26.02 s (+0.62%) | 29.53 → 29.62 s (+0.30%) | 19.88 → 19.75 tok/s (−0.64%) | 11.94 → 12.19 tok/s (+2.07%) |
| 512 | INT8 | 25.35 → 26.51 s (+4.60%) | 28.92 → 30.12 s (+4.14%) | 20.28 → 19.38 tok/s (−4.41%) | 12.27 → 12.16 tok/s (−0.86%) |
| 7,501 | FP16 | 331.55 → 335.49 s (+1.19%) | 335.18 → 339.49 s (+1.28%) | 22.63 → 22.37 tok/s (−1.17%) | 12.03 → 10.96 tok/s (−8.86%) |
| 7,501 | INT8 | 328.91 → 329.94 s (+0.31%) | 332.52 → 333.91 s (+0.42%) | 22.81 → 22.74 tok/s (−0.31%) | 12.12 → 11.02 tok/s (−9.03%) |

The short-task MTP4 latency outliers from the seven-block confirmation did not
recur in this block. The largest short-task total-time increase was 4.14% for
INT8, compared with the retained multi-fold delays in the two flagged primary
arms. This does not establish a cause or remove those arms from the primary
analysis. The long-task MTP4 decode loss recurred at about 9% for both KV
formats, consistent with the seven-block result.

All arms passed the exact-answer and supervisor checks. Across 1,714 memory
samples, minimum host and admission availability was 17.03 GiB; per-arm cgroup
`high`, `max`, `oom`, and `oom_kill` counters were all zero. No arm breached
the six-GiB host floor. No energy estimate or confidence interval is reported.

Re-run the independent output/memory audit from the repository root:

```sh
python3 bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/followup/audit_qualification.py
```

The primary seven-block confirmation and its inference remain in
[`../README.md`](../README.md). Phase 6 remains open for its other planned
factors and response-model assessment; Phase 5's accepted-state divergence
also remains unresolved.
