# Layer-1 mirror tail-state capture — retained failed cell — Orin — 2026-10-20

This follow-up requested positions 516–523 from the same pinned Coder IQ1_M model and current candidate binary, with the opt-in CPU Q8_1 arithmetic mirror limited to `iq2_s/q2_0@layer=1`. The randomized order selected adaptive first. Its supervised service run passed the runtime and memory checks, but the capture runner marked the cell failed because 12 generated tokens emitted accepted endpoints through 522; endpoint 523 was never produced. The delayed-control arm did not run, so this is not a valid paired result. The request and raw partial captures are retained to document the failed/unsupported cell.

At adaptive positions 516–522, layer-2 GDN intermediate fields and verifier pre/post state remained bit-identical between initial and recovery requests. Accepted layer-2 GDN recurrent and convolution state also matched at all seven observed endpoints. The adaptive per-GDN service-hash comparison still finds differences beginning at endpoint 511 in GDN ordinal 3 (model layer 4); that result comes from this service's prompt-to-recovery trace and does not establish the cause. Minimum host/admission availability was 14.14 GiB; maximum scope use was 10.85 GiB, with zero sampled `high`, `max`, `oom`, or `oom_kill` events.

The failure is a selection error, not a runtime or numerical failure. Reproduction of this exact failed selection:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261046 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1' \
  --capture-moe-positions 516,517,518,519,520,521,522,523 \
  --capture-verify-gdn-layer 2 --verify-gdn-positions 516,517,518,519,520,521,522,523 \
  --capture-verify-gdn-state-layer 2 --gdn-state-positions 516,517,518,519,520,521,522,523 \
  --capture-gdn-commit-state-layer 2 --gdn-commit-state-positions 516,517,518,519,520,521,522,523 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position516-523-layer1-mirror-prefix-trace
```

The layer-4 prefill-state experiment targets the earlier boundary and does not depend on endpoint 523.
