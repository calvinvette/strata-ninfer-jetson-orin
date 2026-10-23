# Position-512 layer-1 verifier parts — Orin — 2026-10-20

This fresh same-service short/long/short pair captures the layer-1 verifier
router, per-expert contributions and combined MoE output at the position where
the preceding [prefill/state trace](../adaptive-position512-prefill-gdn2/README.md)
first observed an adaptive layer-1 owner change. It uses Coder IQ1_M at pinned
revision `5348543e0147355ac9cbcb031184a3546350988e`, current candidate binary
SHA256 `6e4b89f7d0979dd0d16eb000c238aa837d5c990dbe54033dada9a479a93fcd38`, and
the opt-in `iq3_xxs/iq4_nl@layer=31` CPU Q8_1 mirror. Randomized order was
delayed control then adaptive cap-8.

At model layer 1 and position 512, the input activation, token ID, expert IDs
and router weights matched across the repeated requests. The shared-expert
output was bit-identical. Delayed control also had bit-identical routed expert
contributions and combined MoE output. In the adaptive arm, three of ten
expert-hit contribution rows changed in all 2,560 values each. The layer-1
combined MoE vector changed in all 2,560 values (relative L2
`0.00489364`, maximum absolute difference `0.000158567`). The following
layer-2 dispatch activation changed in all 2,560 values; delayed-control
dispatch and GDN state remained exact.

The [independent same-input native expert oracle](compare_owner_oracle.py)
resolved the contribution fingerprints: all three delayed-control rows and
the adaptive initial rows match the CPU oracle exactly, while adaptive recovery
rows for experts 95, 11 and 205 match the GPU oracle exactly. The separate
all-layer route trace reports experts 95 and 11 moving CPU-to-GPU, but reports
expert 205 as CPU-owned in both requests. That disagreement means the trace's
owner field does not describe the captured verifier row reliably at this
position; use the direct output oracle for verifier ownership. The output
arithmetic boundary is now localized to CPU-versus-GPU expert execution for
these three rows, while the route/owner reporting discrepancy remains open.
Both runs passed supervision at 14.24 GiB minimum
host/admission availability for delayed control and 14.35 GiB for adaptive,
with zero sampled cgroup pressure/OOM events. This is correctness localization,
not a speed or model-quality comparison.

The raw captures and analyses are retained in each arm directory. The
same-service verifier-parts analyzer is reproducible with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_layer25_verifier_parts.py \
  --run bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-layer1-verifier-pair/adaptive-cap8/result \
  --layer 1 --positions 512 \
  --output /tmp/position512-layer1-adaptive.json

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-layer1-verifier-pair/compare_owner_oracle.py \
  --root bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-layer1-verifier-pair \
  --output /tmp/position512-layer1-owner-oracle.json
```

The [campaign metadata](campaign.json) records source hashes, model shard
identity, order and supervision results. Per-arm dispatch and verifier
comparisons check initial/recovery rows; the raw `verify-moe-parts.bin`,
`verify-moe-output.bin`, `verify-moe-routes.jsonl`, GDN state dumps and logs are
the underlying evidence.
