# Early adaptive owner changes across model layers 0–2

Date: captures from 2026-10-30; cross-layer comparison completed 2026-10-31. Hardware: Jetson AGX Orin. This is a state-drift localization check, not a performance or independent quality result.

## Setup

Three matched fixed/adaptive capture pairs used the same 65,536-token Q2_0 prompt, 32 generated tokens, 131,072 context, original expert profile, 3,000 slots, 6 GiB resident budget, eight workers, prefill 128, MTP-2, PCIe staging off and prompt cache off. One pair captured each of model layers 0, 1 and 2. Each layer capture recorded the first seven generated dispatches, positions 65,536–65,542. These are separate repeated runs rather than a single simultaneous multi-layer capture. All six runs passed, returned the same 32-token hash, and retained at least 8.44 GiB available physical RAM; sampled cgroup OOM kills were zero. Peak sampled system swap was 1.87 GiB.

The committed summary records each position’s token, route equality, activation equality, relative L2, owner changes and hashes of the local raw capture files. Raw dispatch data and memory telemetry remain under `/tmp/e6-65k-{fixed,adaptive}-layer{0,1,2}-route*` and are not committed.

## Findings

| Model layer | Positions with matching routes | Owner changes | Input activation finding |
|---:|---:|---|---|
| 0 | 7/7 | None | Bitwise equal at all seven positions |
| 1 | 7/7 | At position 65,540, expert 3 is GPU-owned in fixed (`0`) and CPU-owned in adaptive (`-1`) | Bitwise equal at all seven positions, including the owner transition |
| 2 | 7/7 | None | First difference at 65,540 (`5.12e-8` relative L2); otherwise bitwise equal |

The owner change follows adaptive swap `1:320>3`, applied before position 65,540. A separate same-input service-row capture and native CPU/GPU oracle at that position found the service output rows bitwise matched their respective owner replays; the per-expert delta was `1.059e-7` relative L2 and combined MoE delta `4.345e-8`. This aligns the first layer-2 input change with a small layer-1 owner effect. It does not establish that the expert transition causes the prefix-8 persistent-state difference: the owner/oracle row capture is a separate run, no forced-owner counterfactual was propagated through the remaining model, and matching generated text is not a state or quality oracle.

This closes the search for additional owner-kind changes in model layers 0–2 over these seven positions. It leaves open whether the observed layer-1 transition materially contributes to the later recurrent-state delta, and whether other model layers or later positions add effects. See the [machine-readable comparison](layer0-2-owner-window-65536-65542.json), [layer-1 service/oracle comparison](active-owner-oracle-position65540.json), and [accepted-prefix diagnostic](adaptive-long-prefix-state-diagnostic.md).
