# Q6_K warp-dequant × MTP randomized screen — Orin — 2026-10-12/13

This three-block randomized complete-block screen compared the current Q6_K route with `STRATA_Q6K_WARP_DEQUANT=1`, each with MTP disabled and with verifier window 4. It used the same Qwen3.8 Flash-Next Coder IQ1_M model, binary SHA `1135dd9093a7bbf15c874516bc75886a029d4d149196898b15023ad95907d047`, 8K context, 3,903 admitted expert-cache slots, and a fixed 512-token prompt plus 64 generated tokens. Each fresh service had a distinct 512-token warmup and one-token warmup request. Order was randomized with seed `202610124`. All 12 requests and warmups passed, all three complete blocks had exact generated-output hash parity across all four conditions, MTP draft counts were 0/0 when off and 93 offered/32 accepted when on, and every cell preserved the six-GiB floor.

| MTP condition | Warp effect on total request | Paired bootstrap 95% interval | Prompt effect | Decode effect |
| --- | ---: | ---: | ---: | ---: |
| Off | −6.347% median | −7.460% to −5.488% | −7.941% | +2.005% |
| Window 4 | −5.531% median | −6.511% to −4.492% | −8.326% | +2.000% |

The paired MTP interaction contrast for total request time had median −0.046% and bootstrap interval −0.175% to +3.208%; this three-block screen does not support a material interaction claim. Decode was about 2% slower with the warp route in both MTP conditions, so the total-request improvement came from prompt processing. Minimum host availability was 13.06 GiB and minimum effective admission availability was 9.34 GiB across the 12 cells. GPU clocks varied dynamically; EMC rate access was unavailable and energy was not measured.

These are screening results for one model, prompt, context, binary and cache size. They do not pass the broader quality budget, held-out confirmation, or seven-repetition confirmation gates. No default changed. Raw runs, telemetry, configs, the randomized schedule and analysis are retained in `run/`; `analyze.py` reproduces the summary from those records.
