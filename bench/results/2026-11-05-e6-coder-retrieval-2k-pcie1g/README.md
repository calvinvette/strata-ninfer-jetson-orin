# Coder 2K retrieval screen with a 1 GiB pinned complement

Four fixed, balanced-order Strata/strict-NInfer pairs used the same 2,048-token
active-ticket retrieval fixture, 4,096-token context, model, binary, and expert
profile as the [un-staged 2K screen](../2026-11-05-e6-coder-retrieval-2k/README.md).
This variant used `--pcie-frac 1.0`, a 1 GiB pinned complement, six GiB host
headroom, and the existing three GiB workspace reserve. Default adaptive
swapping was enabled (`--adapt-every 4`); each warmup performed eight exchanges
before measurement. The measured requests had matching aggregate counters in
all pairs, but per-expert owner IDs were not captured.

All eight measured responses returned `73192` with identical six-token IDs.
Both backends logged 111 resident hits among 2,787 GPU/cache lookups and 93
PCIe reads per request (2,880 routes total). Decode changed −0.04% at the paired median
(four-pair screening interval −0.99% to +2.21%). Prompt TPS changed −2.84%
(−5.51% to −0.38%), client TTFT reduction was −2.96% (−5.82% to −0.38%), and
client duration reduction was −2.94% (−5.78% to −0.36%). No useful decode gain
was demonstrated; the latency measures were slower for NInfer in this screen.
The small staged share and adaptive map make this a bounded policy screen,
not a fixed-owner kernel attribution.

The supervisor passed the six GiB physical floor with 19.67 GiB minimum
available RAM. Swap peaked at 1.64 GiB; the existing OOM-kill count stayed at
one. The run took 1,661 s. Clocks were sampled read-only and dynamic, EMC
readback was denied, and energy was not measured. Full per-arm data are in
[`run/results.json`](run/results.json); raw logs and supervisor captures
remain in this workspace.

Reproduce with:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-11-05-e6-coder-retrieval-2k-pcie1g/supervisor \
  --sample-clocks --timeout 3600 -- \
  python3 bench/results/2026-11-05-e6-coder-retrieval-2k/run_retrieval_perf_screen.py \
  bench/results/2026-11-05-e6-coder-retrieval-2k-pcie1g/run --staged-pcie
```
