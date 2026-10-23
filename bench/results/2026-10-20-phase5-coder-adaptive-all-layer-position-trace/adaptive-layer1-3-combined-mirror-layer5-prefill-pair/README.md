# Repeated-prompt layer-5 prefill trace — Orin — 2026-10-20

This randomized pair used the combined layer-1/layer-3 CPU Q8_1 mirrors and
traced layer-5 GDN state during prefill. The repeated 505-token prompt payload
had identical layer-5 state hashes at every chunk boundary; the retained
end-of-prompt recurrent and convolution arrays were bit-identical between the
initial and recovery prompts in both delayed and adaptive arms.

The separate verifier capture at position 511 still shows an adaptive layer-5
state difference. The prefill trace labels the 505-token payload, while the
fully formatted request is 512 tokens. This pair therefore establishes that
the captured payload prefill segment matches but does not, by itself, cover the
entire formatted prompt tail. The subsequent [505–511 verifier trace](../adaptive-layer1-3-combined-mirror-prompt-tail505-511-corrected-pair/README.md)
finds the first changed layer-5 GDN input at position 505. Delayed control
remains exact.

Both runs passed supervision with at least 14.24 GiB host/admission
availability and zero sampled cgroup pressure/OOM events. This is not a
performance result. Reproduce with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261053 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3' \
  --capture-moe-positions 511 --trace-prefill-gdn-state-layer 5 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-combined-mirror-layer5-prefill-pair
```

Raw prefill snapshots, per-chunk hashes, request logs and supervision telemetry
are retained beside this report.
