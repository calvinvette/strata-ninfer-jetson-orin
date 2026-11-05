# Coder 2K retrieval screen with a 6 GiB pinned complement

Four fixed, balanced-order Strata/strict-NInfer pairs used the same 2,048-token
active-ticket retrieval fixture, 4,096-token context, model, binary, and expert
profile as the [un-staged 2K screen](../2026-11-05-e6-coder-retrieval-2k/README.md).
This adaptive variant used `--pcie-frac 1.0`, a 6 GiB pinned complement, six
GiB host headroom, and the existing three GiB workspace reserve. Default
adaptive swapping was enabled (`--adapt-every 4`); each warmup performed eight
exchanges before measurement. The measured requests had matching aggregate
route counters in all pairs, but per-expert owner IDs were not captured.

All eight measured responses returned `73192` with identical six-token IDs.
Both backends logged 111 resident hits, 2,112 GPU/cache lookups and 768 PCIe
reads per measured request (2,880 routes total). Decode changed −1.48% at the
paired median (four-pair screening interval −3.26% to −0.85%). Prompt TPS
changed −1.19% (−2.58% to −0.97%), client TTFT reduction was −1.20%
(−2.64% to −0.98%), and client duration reduction was −1.21%
(−2.65% to −0.98%). No useful NInfer gain was demonstrated; all four latency
medians were slower in this screen. The 768 PCIe reads show substantial staged
coverage, but not a fixed-owner kernel comparison.

The supervisor passed the six GiB physical floor with 14.87 GiB minimum
available RAM. Swap peaked at 1.73 GiB; the existing OOM-kill count stayed at
one. The run took 1,411 s. Clocks were sampled read-only and dynamic, EMC
readback was denied, and energy was not measured. Full per-arm data are in
[`run/results.json`](run/results.json); raw logs and supervisor captures
remain in this workspace.

Reproduce with:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-11-05-e6-coder-retrieval-2k-pcie6g/supervisor \
  --sample-clocks --timeout 3600 -- \
  python3 bench/results/2026-11-05-e6-coder-retrieval-2k/run_retrieval_perf_screen.py \
  bench/results/2026-11-05-e6-coder-retrieval-2k-pcie6g/run --staged-pcie-gib=6
```
