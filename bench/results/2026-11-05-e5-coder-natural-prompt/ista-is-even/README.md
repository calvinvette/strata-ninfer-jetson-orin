# ISTA IQ3_S `is_even` service parity — Orin — 2026-11-05

This is a two-pair service check on the actual ISTA-DASLab Qwen3.8-Flash-Next
IQ3_S GGUF shards, using the matching `iq3-s-pack` decoder pack and the
experiment's static 512-slot profile. Each fresh Strata/strict-NInfer pair ran
the same 44-token `is_even(n)` prompt with MTP-2, 512-token context, 64-token
output cap, prompt cache disabled, and state plus accepted-prefix tracing
enabled. The fixed service order was Strata then NInfer. Both backend requests
logged the seven supported mixed-codec route families at their observed model
layers; cache hit counters were 378/11,040 in each arm. These counters describe
the request's cache lookups and do not by themselves count NInfer kernel calls.

All four responses generated the same 21 token IDs and passed the independent
six-case executable function oracle. Within each pair, all 11 persistent-state
fields matched at each of 21 accepted-token boundaries and at the final state.
Across the two fresh pairs, both engines reproduced the same accepted tokens
and boundary hashes. This is a positive, repeatable parity point on a real
mixed-codec IQ3_S model; it does not settle the earlier Coder IQ1_M divergence,
qualify other prompts or profiles, or establish a general numerical tolerance.

The memory supervisor passed both pairs. Minimum available RAM was 19.13 GiB
and 19.76 GiB; sampled swap peaked at 1.37 GiB and 1.67 GiB, respectively, and
the existing cgroup OOM-kill count stayed at one. GPU clock readback at
supervisor start was 306 MHz; clocks were dynamic, EMC readback was denied, and
energy was not measured. State tracing and the fixed-order requests make all
observed timings unsuitable for performance inference.

The exact binary, pack metadata, profile and model-shard hashes, full token
results, supervisor summaries, and per-boundary hashes are recorded in
[`results.json`](results.json). Raw logs and telemetry remain in adjacent local
run directories. The profile file was an experiment-generated `/tmp` artifact;
its hash is recorded, but the file is not included in Git.
