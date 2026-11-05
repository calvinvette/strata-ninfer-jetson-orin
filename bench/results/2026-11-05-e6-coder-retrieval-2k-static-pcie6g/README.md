# Coder 2K retrieval static-owner screen with a 6 GiB pinned complement

Four fixed, balanced-order Strata/strict-NInfer pairs used the same 2,048-token
active-ticket retrieval fixture, 4,096-token context, model, binary, and expert
profile as the [un-staged 2K screen](../2026-11-05-e6-coder-retrieval-2k/README.md).
This variant used `--pcie-frac 1.0`, a 6 GiB pinned complement, six GiB host
headroom, the existing three GiB workspace reserve, and `--adapt-every 0`.
Logs confirm adaptive swaps were off, so the profile and pinned complement
were static across each warmup and measured request. A separate [instrumented route/owner capture](owner-capture-all/README.md)
records all 2,880 layer/expert assignments for one request per backend. Timing
remains uninstrumented; route-set differences limit causal interpretation.

All eight measured responses returned `73192` with identical six-token IDs.
Both backends logged 86 resident hits, 2,087 GPU/cache lookups and 793 PCIe
reads per request (2,880 routes total), matching in every pair. Decode changed
−1.40% at the paired median (four-pair screening interval −3.97% to +0.18%).
Prompt TPS changed +0.17% (−4.16% to +2.90%), client TTFT reduction was +0.18%
(−4.36% to +2.81%), and client duration reduction was +0.16%
(−4.34% to +2.78%). The decode effect is below the 5% useful-effect gate and
the interval spans zero. This does not demonstrate a useful gain or
equivalence; no confirmation or profile promotion follows.

The static run offloaded 793/2,880 routes (27.5%) to PCIe, compared with
768/2,880 (26.7%) in the adaptive run. Resident GPU hits were 3.0%; the
remaining routed experts used the CPU/file path. The supervisor passed the
six GiB physical floor with 15.03 GiB minimum available RAM. Swap peaked at
1.47 GiB; the existing OOM-kill count stayed at one. The run took 1,385 s.
Clocks were sampled read-only and dynamic, EMC readback was denied, and energy
was not measured. Full per-arm data are in
[`run/results.json`](run/results.json); raw logs and supervisor captures
remain in this workspace.

Reproduce with:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-11-05-e6-coder-retrieval-2k-static-pcie6g/supervisor \
  --sample-clocks --timeout 3600 -- \
  python3 bench/results/2026-11-05-e6-coder-retrieval-2k/run_retrieval_perf_screen.py \
  bench/results/2026-11-05-e6-coder-retrieval-2k-static-pcie6g/run \
  --staged-pcie-gib=6 --static-owner
```
