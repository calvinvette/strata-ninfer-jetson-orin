# Q2_0 256-token accepted-prefix MTP parity — Orin — 2026-10-14

This supervised correctness run extends the current-build Q2_0 accepted-prefix
comparison from 128 to 256 generated tokens. Four sequential fresh engines
used one exact 2,048-token formatted prompt, 8K configured context, FP16 KV,
3,000 requested expert-cache slots and the accepted-only adaptive-swap policy
at cadence 4. The artifact was `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0`, with the
native pack `q2-ple-pack` and the local MTP runtime weights. Model assets remain
under `~/models/` and are not copied into the repository.

All four arms completed 256 tokens. They emitted identical token IDs and
matched all nine persistent-state fields at the final boundary and every
shared accepted-prefix boundary. MTP-off had 256 commit boundaries; MTP2,
MTP3 and MTP4 had 168, 150 and 134, respectively. Every candidate boundary
shared with the MTP-off trace matched directly.

| MTP window | Drafts offered | Drafts accepted | Shared matching boundaries | Output/final state |
| ---: | ---: | ---: | ---: | --- |
| Off | 0 | 0 | Reference: 256 | 256 IDs recorded |
| 2 | 136 | 88 | 168 | Exact IDs and state |
| 3 | 201 | 106 | 150 | Exact IDs and state |
| 4 | 264 | 122 | 134 | Exact IDs and state |

All arms used the same current CUDA executable, SHA256
`abef7698554590b3e28036844da207c0c58c291167204bee9dff248d80304b32`. The
prepared prompt SHA256 was
`93cefb75fa4bb48eec0bcbf5771e06a6cce6bbad03c463df644fb45634b3dc15`. The
run took 900.77 seconds under one sequential `MemoryMax=28G` scope. Minimum
physical host availability was 16.935 GiB; minimum effective admission
availability was 8.107 GiB. The six-GiB floor passed, and sampled cgroup
pressure, limit and OOM counters stayed zero. Read-only CPU/GPU/EMC clock
observations and tegrastats are retained. Energy was not measured. State tracing
synchronizes the decode path, so no timing conclusion is drawn.

This provides longer-chain state evidence for one Q2_0 prompt, fixed cache,
FP16 KV and accepted-only adaptation policy. It does not resolve the separate
same-service residency-change recovery drift, establish task quality, or
qualify other prompts, cache sizes, KV formats, eager decode or MTP performance.
Phase 5 remains open.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output supervisor --timeout 7200 --interval 1 --sample-clocks -- \
    python3 tools/integration/accepted_prefix_parity.py \
      --config bench/results/2026-10-14-phase5-q2-mtp-quality/config-mtp4.json \
      --engine build/integration/candidate/strata \
      --output run --tokens 256 --prompt-tokens 2048 \
      --windows 0 2 3 4 --use-config-adaptive-swaps --run
```
