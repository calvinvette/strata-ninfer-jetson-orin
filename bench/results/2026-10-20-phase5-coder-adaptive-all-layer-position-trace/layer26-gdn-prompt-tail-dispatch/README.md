# Prompt-tail router and activation trace — Orin — 2026-10-20

This same-service diagnostic used the current candidate and pinned Coder
IQ1_M GGUF from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. The shards are
`Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf` and
`Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf`, kept under
`~/models/strata-orin-validation/Coder-GGUF/IQ1_M/`.

The 512→2,048→512 sequence generated the same 16 token IDs for the initial and
recovery short requests. The opt-in router capture selected absolute verifier
positions 505 and 506 across all 48 layers. It retained 192 rows (two requests,
two positions, 48 layers) in
`run/all-layer-selected-positions.jsonl`. The capture stores 2,560 FP32
activation values per row as nine-significant-digit decimals. The analyzer
compared token IDs, expert IDs, expert owners and activation vectors for each
initial/recovery pair.

At both positions, expert IDs match through layer 26. Owner placement already
differs at layer 1, but all captured activations are identical through layer
25. Layer 26 is the first activation difference: 2,560/2,560 values differ,
with maximum absolute delta 0.00978 and relative L2 0.00482 at position 505;
at position 506 the maximum is 0.00260 and relative L2 0.00105. Expert IDs
first differ at layer 27 for position 505 and layer 31 for position 506.
The analyzer output is `dispatch-analysis.json`, based on capture SHA-256
`f2ed1861fd751751d870e3140c3b81001f87d7e60f22bd594cb45079093d9b0b`.

This bounds the first captured numerical change to the layer-26 verifier
activation for these two prompt-tail positions. Earlier owner differences did
not change captured activations through layer 25. It does not identify which
upstream state transition or kernel introduced the layer-26 input change, and
it is not a quality or performance result.

The supervised run passed in 184.4 seconds under `MemoryMax=28G`. Minimum host
and admission availability were both 15,376,863,232 bytes (14.33 GiB); cgroup
memory event counters remained zero. GPU/CPU clocks were sampled dynamically;
EMC clock readback was denied. Energy was not request-attributed.

Local build and checks after adding the plural position filter:

- Orin `strata` build passed.
- `file_expert_source_test` and `native_expert_parity_q8_1_selector_contract`
  passed (2/2); integration Python tests passed (163/163); Python bytecode
  compilation passed.
- maestro1 HIP rebuilt and linked; `strata --help` exited 0. SYCL build had no
  source changes and no work; its CLI check exited 0. Both are x86 compile/CLI
  evidence only. Cgroup memory events were all zero.

Reproduce the capture and analysis from the repository root on Orin:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/supervisor \
  --timeout 1200 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_one.py \
  --adapt-every 4 --adapt-swaps 8 --capture-moe-positions 505,506 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/run

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_prompt_tail_dispatch.py \
  --capture bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/run/all-layer-selected-positions.jsonl \
  --positions 505 506 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/dispatch-analysis.json
```

Phase 5 remains open.
