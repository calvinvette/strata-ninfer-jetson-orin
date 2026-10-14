# Accepted-only adaptive window: 256-token state check

This extends the accepted-window boundary test on the current candidate binary.
It checks long accepted-prefix chains and persistent main-model state for the
opt-in accepted-only adaptation route. It is correctness evidence, not a serving
performance or broad quality claim.

## Orin run

The supervised Qwen3.8-Flash-Next GSQ RCO Q2_0 run used FP16 KV, the same exact
2,048-token prompt as the 32-token boundary check, a 256-token output allowance,
3,000 expert-cache slots, prefill 512, and accepted-only adaptation every four
accepted tokens. MTP off/2/3/4 ran in fresh services under a 28-GiB cgroup cap
and six-GiB admission floor. The prompt SHA256 is
`93cefb75fa4bb48eec0bcbf5771e06a6cce6bbad03c463df644fb45634b3dc15`; candidate
binary SHA256 is
`5a72dbad8a79782a7cd778ab222fdcfe82f3665b25923767215f0f465bbcd213`.
The model shards and pack remained under `~/models`; no model was downloaded.
The config contains no activation-capture hooks.

All four arms emitted 256 identical token IDs and matched all nine recorded
persistent-state fields at final state. Every shared accepted-prefix boundary
matched exactly: 168 for MTP2, 150 for MTP3, and 134 for MTP4. Drafts offered
and accepted were 136/88, 201/106, and 264/122 for MTP2/3/4. The supervisor
exited successfully after 908.8 seconds. Minimum physical host availability
was 16.88 GiB; minimum effective admission availability was 8.43 GiB. All
sampled cgroup low/high/max/OOM counters were zero. Tegrastats `tj` ranged from
44.8 to 55.2 °C. Clocks were dynamic and energy was not attributed to requests.
The single-run timings in `results.json` are not used for performance claims.

This confirms prefix parity for this prompt, cache and FP16-KV configuration.
It does not resolve the separate same-service recovery drift after adaptive
residency changes, nor qualify other prompts, cache sizes, KV formats, or
adaptive policies.

## Reproduction

From the repository root on Orin:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-accepted-window-256/supervisor \
  --timeout 14400 --interval 1 -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-14-phase5-accepted-window-256/config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-14-phase5-accepted-window-256/run \
  --prompt-tokens 2048 --tokens 256 --windows 0 2 3 4 \
  --use-config-adaptive-swaps --run
```

Raw per-arm logs, comparison records, memory samples and tegrastats are retained
in `run/` and `supervisor/`; `SHA256SUMS.txt` covers the files.
