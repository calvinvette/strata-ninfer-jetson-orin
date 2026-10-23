# Layer-17 prefill state with the layer-16 targeted CPU selector

This follow-up uses the same randomized short/short/short adaptive-versus-
delayed-control workload and IQ1_M model as the adjacent layer-16 targeted
state capture. The opt-in selector was
`iq3_xxs/iq4_nl@layer=16`. Both service arms completed under their supervisors;
minimum host and admission availability were 14.05 GiB for delayed control and
14.17 GiB for adaptive, with no cgroup pressure or OOM events. See each arm's
`supervisor/result.json` and retained memory/clock samples for raw telemetry.

The first request's 505-token prefill was traced at all eight chunk boundaries
for layer 17 (GDN ordinal 13). Control and adaptive hashes matched at every
boundary, including 505, and the end-of-prompt raw state was bit-identical:
all 786,432 recurrent and 30,720 convolution values matched. This establishes
prefill parity across these two fresh service arms for this selector and input.
It does not explain the same-service adaptive state divergence found after
repeated requests in the adjacent
[`adaptive-layer16-q8-targeted-prefix-states/state-prefix-analysis.json`](../adaptive-layer16-q8-targeted-prefix-states/state-prefix-analysis.json),
where raw layer-17 verifier state was already different at captured position
512. The prefill capture here records only the first actual prefill per service;
identical later prompts reused cached work and did not produce repeat traces.

A follow-up request to capture verifier state at positions 505–511 is retained
in the sibling
[`adaptive-layer16-q8-targeted-generated-positions505-511`](../adaptive-layer16-q8-targeted-generated-positions505-511/).
The service
completed its first adaptive arm, but the diagnostic validator observed only
position 511 (three request occurrences), while positions 505–510 were not
available through this verifier-state hook. It marked the capture unsupported
and stopped before running the second arm. The supervisor still passed its
memory floor (14.13 GiB minimum availability); this is an instrumentation
limitation, not a model/runtime pass or comparison. The verified prompt-end
prefill trace above remains the supported evidence.

Reproduce the cross-arm trace analysis with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_prefill_gdn_state_arms.py \
  --control-log bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer16-q8-targeted-prefill-state/delayed-control/result/service.log \
  --control-state bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer16-q8-targeted-prefill-state/delayed-control/result/prefill-gdn-state.bin \
  --adaptive-log bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer16-q8-targeted-prefill-state/adaptive-cap8/result/service.log \
  --adaptive-state bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer16-q8-targeted-prefill-state/adaptive-cap8/result/prefill-gdn-state.bin \
  --layer 17 \
  --output /tmp/layer17-prefill-state-analysis.json
```

The cross-arm result narrows the open Phase 5 investigation but does not
identify a causal operation or qualify accepted-prefix state transactions.
