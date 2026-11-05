# Layer 16 MoE input and route capture

This diagnostic repeats the 2,048-token Coder retrieval under the static 6 GiB
complement, `adapt-every=0`, and `STRATA_PREFILL_CPU_SHARE=0`. It captures the
MoE activation and top-10 IDs/weights at layer 16, position 2,047 for Strata
and strict NInfer. The position was selected after a prior capture with CPU
prefill sharing enabled showed route differences; that earlier setup did not
match the performance screen. The corrected all-layer capture found no route
ID differences under the screen's settings.

At this boundary, both backends had the same token ID, bit-identical 2,560-value
MoE input, identical ordered expert IDs, and identical router weights. Both
returned the same six-token answer and token IDs. The tracked
[`result.json`](result.json) records the exact routes, activation error summary,
and hashes of local raw captures. Timings are excluded.

Raw input arrays and full logs remain local and are not committed. The
supervisor retained 14.98 GiB minimum available memory, above the six-GiB
floor; the existing OOM-kill count remained one. Clocks were sampled
read-only/dynamic, EMC readback was denied, and energy was not measured.

Reproduce from the project root on the Orin host:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-11-05-e6-coder-retrieval-2k-static-pcie6g/first-route-boundary-supervisor \
  --sample-clocks --timeout 2400 -- \
  python3 bench/results/2026-11-05-e6-coder-retrieval-2k-static-pcie6g/capture_layer16_route_input.py \
  bench/results/2026-11-05-e6-coder-retrieval-2k-static-pcie6g/first-route-boundary
```
