# Layer-31 expert-155 mirror and layer-32 state follow-up — Orin — 2026-10-20

This same-service, randomized short/short/short pair follows the adaptive
initial-to-recovery divergence after the layer-11 expert-179 and layer-27
expert-175 Q8_1 CPU mirrors. It uses the pinned Coder IQ1_M GGUF revision
`5348543e0147355ac9cbcb031184a3546350988e`, candidate binary SHA256
`e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`, and
seed `20261035`. Delayed-control and adaptive-cap8 used identical settings,
`--continuations 0`, three 512-token requests, 12 requested output tokens, zero
prompt cache, and captured all 48 verifier MoE inputs at position 511, layer-31
expert rows, and layer-32 GDN intermediates and raw pre/post state.

## Findings

At layer 31, token 271 routes expert 155 (rank 0) with identical activation,
expert IDs and router weights across adaptive intermediate and recovery
requests. The owner moves CPU (`-1`) to GPU (`0`). The default service rows
match an independent `native_expert_parity` oracle exactly on each owner path;
CPU and GPU outputs differ in all 2,560 values, with 1.331% relative L2. The
GGUF tensor types are IQ3_XXS/IQ4_NL. An oracle run with
`iq3_xxs/iq4_nl@layer=31` makes CPU and GPU outputs bit-identical, also matching
both mirrored service rows exactly.

With that selector added to both pair arms, the layer-31 expert row, shared
output and combined MoE output are bit-identical across the owner change. Raw
layer-32 GDN pre/post recurrent and convolution state at position 511 is exact
across all three requests in both arms; the raw post-state hashes match the
serving per-GDN hashes at ordinal 24. Delayed control remains exact throughout.

The local boundary result does not restore whole-request state parity. Adaptive
accepted-state and per-GDN fingerprints still differ at all 12 prefixes, while
token IDs match. At position 511 the first captured input activation difference
moves to layer 33, and expert IDs/owners also differ later in the stack. This is
a narrow operator/state localization, not an adaptive migration fix, quality
result or performance comparison.

Both pair arms passed `MemoryMax=28G` supervision with no cgroup memory events.
Minimum host/admission availability was 14.168 GiB for delayed control and
14.309 GiB for adaptive; clocks remained dynamic. The two earlier failed setup
attempts and the extra-continuation capture-count failure are retained in
sibling result directories and excluded from these findings.

## Reproduction

From the repository root, rerun the pair with a fresh output directory:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --output /tmp/layer11-27-31-mirror-layer32-state-pair \
  --seed 20261035 --continuations 0 --sequence short-short-short \
  --generated-tokens 12 --prompt-cache 0 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=8,iq2_s/q2_0@layer=13,iq3_xxs/iq4_nl@layer=16,iq2_s/iq4_nl@layer=24,iq3_s/iq4_nl@layer=28,iq3_s/iq4_nl@layer=29,iq3_xxs/q2_0@layer=30,iq2_s/iq4_nl@layer=11,iq3_s/iq4_nl@layer=27,iq3_xxs/iq4_nl@layer=31' \
  --capture-moe-positions 510,511 \
  --capture-verify-moe-layer 31 --verify-moe-positions 511 \
  --verify-moe-input-layers all \
  --capture-verify-gdn-layer 32 --verify-gdn-positions 511 \
  --capture-verify-gdn-state-layer 32 --gdn-state-positions 511 --run
```

`run_pair.py` supervises each arm in its own 28-GiB systemd scope. The raw
captures, campaign manifest, input/route and state comparators, oracle dumps,
service-to-oracle joins, supervisor samples and clock observations are retained
in this directory. The exact code revision, model shard hashes and capture
hashes are recorded in `campaign.json` and the generated analysis files.
