# Layer-21 owner and expert-output comparison at position 534 — Orin — 2026-10-22

This supervised adaptive-only replay repeated the pinned Coder IQ1_M 128-token
short→long→short sequence with the same binary, model, prompts, adaptive
cadence 4/cap 8, and CPU Q8_1 selector `all`. At position 534, the initial and
recovery requests both consumed token 3155. Layer-21 verifier inputs, expert
IDs and weights matched. The owner kinds also matched for every rank: CUDA
owners for experts 149, 103, 85 and 184; CPU owners for experts 215, 127, 132,
13 and 177. All ten captured expert output rows were bit-identical across the
requests, as were the captured shared and combined MoE outputs.

This excludes a layer-21 MoE owner flip or MoE output delta for this token as
the explanation of the changed layer-22 input. Since the layer-22 input is the
first changed activation, the remaining target is the layer-21 post-MoE path,
including its recurrent/GDN and residual operations. The next capture will
inspect those intermediate boundaries. The comparison is not an independent
operator oracle because no expert row changed owners or values.

The supervised run completed all three 128-token requests in 597.4 seconds.
Minimum host/admission availability was 14.20 GiB, above the six-GiB floor;
cgroup memory-event counters remained zero. Clocks were observed dynamically,
EMC readback was unsupported, and energy was not measured. Raw capture and
supervisor logs remain local; `layer21-owner-analysis.json` is the compact
comparison.
